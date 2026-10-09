"""One committed retailer/week batch, with cancellable staged replacements."""
import io
import json
import multiprocessing
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from flask import request, jsonify
from werkzeug.datastructures import FileStorage
from database import get_db_connection
from retailer_setup import apply_pipeline, validate_pipeline, validate_retailer, assign_store_codes
from batch_metrics import input_metrics, received_metrics, public_metrics, previous_period

FINDING_CODES={'numeric':'RULE_NUMERIC_INVALID','date':'RULE_DATE_INVALID','required':'VALIDATION_REQUIRED',
               'range':'VALIDATION_RANGE','pattern':'VALIDATION_PATTERN','unique':'VALIDATION_DUPLICATE'}

def now(): return datetime.now(timezone.utc).isoformat()
def decode(value, default): return json.loads(value) if value else default

def execute_step(records, rule, queue):
    try:
        output, steps, issues, trace = apply_pipeline(records, [rule])
        queue.put({'output':output, 'issueCount':len(issues), 'changedCells':len(trace)})
    except (ValueError, TypeError, KeyError) as exc:
        message=str(exc)
        code='RULE_FIELD_MISSING' if 'does not exist' in message else 'RULE_TARGET_EXISTS' if 'already exists' in message else 'RULE_CONFIG_INVALID'
        queue.put({'errorCode':code,'message':message})
    except Exception:
        queue.put({'errorCode':'RULE_EXECUTION_ERROR','message':'Rule execution failed unexpectedly.'})

def execute_parse(source, filename, parser, queue):
    try:
        file=FileStorage(stream=io.BytesIO(source),filename=filename)
        try:records,_,_=parser(file)
        finally:file.close()
        queue.put({'output':records})
    except Exception:
        queue.put({'errorCode':'INPUT_PARSE_ERROR','message':'The input file could not be parsed.'})

def public_job(row):
    return {k:row[k] for k in ['id','retailer_id','retailer_name','period','start_time','end_time','status','filename']} | {
        'errorCodes':decode(row['error_codes'],[]), 'hasAudit':row['status']!='Cancelled Job' and bool(row['audit']),
        'metrics':public_metrics(decode(row['metrics'],{})), 'lastAttempt':decode(row['last_attempt'],None)}

def register_batch_routes(app, parse_upload, error):
    with get_db_connection() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS batch_jobs(
            id TEXT PRIMARY KEY,retailer_id TEXT NOT NULL,retailer_name TEXT NOT NULL,period TEXT NOT NULL,
            start_time TEXT NOT NULL,end_time TEXT,status TEXT NOT NULL,filename TEXT NOT NULL,
            source BLOB NOT NULL,pipeline TEXT NOT NULL,output TEXT,audit TEXT,error_codes TEXT,last_attempt TEXT,
            UNIQUE(retailer_id,period))''')
        db.execute('''CREATE TABLE IF NOT EXISTS batch_attempts(
            id TEXT PRIMARY KEY,retailer_id TEXT NOT NULL,retailer_name TEXT NOT NULL,period TEXT NOT NULL,
            start_time TEXT NOT NULL,filename TEXT NOT NULL,source BLOB NOT NULL,pipeline TEXT NOT NULL,
            deadline REAL NOT NULL,progress TEXT NOT NULL,UNIQUE(retailer_id,period))''')

    with get_db_connection() as db:
        for table in ['batch_jobs','batch_attempts']:
            if 'metrics' not in [r['name'] for r in db.execute(f'PRAGMA table_info({table})')]:
                db.execute(f'ALTER TABLE {table} ADD COLUMN metrics TEXT')

    def finalize(aid, status, output=None, audit=None, codes=None):
        with get_db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            attempt=db.execute('SELECT * FROM batch_attempts WHERE id=?',(aid,)).fetchone()
            if not attempt: return False
            cancelled=status=='Cancelled Job'
            ended=None if cancelled else now()
            previous=db.execute('SELECT * FROM batch_jobs WHERE retailer_id=? AND period=?',(attempt['retailer_id'],attempt['period'])).fetchone()
            if cancelled and previous:
                outcome={'id':aid,'status':status,'start_time':attempt['start_time'],'end_time':None,'errorCodes':codes or [],'hasAudit':False}
                db.execute('UPDATE batch_jobs SET last_attempt=? WHERE id=?',(json.dumps(outcome),previous['id']))
            else:
                # Replacing the unique slot deletes the former ID, audit, output and source together.
                if previous: db.execute('DELETE FROM batch_jobs WHERE id=?',(previous['id'],))
                db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (aid,attempt['retailer_id'],attempt['retailer_name'],attempt['period'],attempt['start_time'],ended,status,
                     attempt['filename'],attempt['source'],attempt['pipeline'],None if cancelled else json.dumps(output),
                     None if cancelled else json.dumps(audit or []),json.dumps(codes or []),None,attempt['metrics']))
            db.execute('DELETE FROM batch_attempts WHERE id=?',(aid,))
            return True

    def active(aid):
        with get_db_connection() as db: return db.execute('SELECT * FROM batch_attempts WHERE id=?',(aid,)).fetchone()

    def process_result(aid, target, args, deadline):
        context=multiprocessing.get_context('spawn');queue=context.Queue(maxsize=1)
        process=context.Process(target=target,args=(*args,queue))
        try:process.start()
        except Exception:
            queue.close()
            return {'errorCode':'RULE_WORKER_START_ERROR','message':'The execution worker could not start.'}
        try:
            while True:
                if not active(aid):return None
                if time.time()>=deadline:
                    finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return None
                try:return queue.get(timeout=0.1)
                except Exception:
                    if not process.is_alive():return {'errorCode':'RULE_PROCESS_EXIT','message':'The worker stopped before returning a result.'}
        finally:
            if process.is_alive():process.terminate()
            process.join(timeout=2);queue.close()

    def run(aid):
        attempt=active(aid)
        if not attempt:return
        audit=[];interrupted=False;codes=[]
        try:
            started=now();parse_clock=time.monotonic()
            if app.testing and app.config.get('BATCH_TEST_EXECUTOR'):
                file=FileStorage(stream=io.BytesIO(attempt['source']),filename=attempt['filename'])
                try:records,_,_=parse_upload(file)
                finally:file.close()
            else:
                result=process_result(aid,execute_parse,(attempt['source'],attempt['filename'],parse_upload),attempt['deadline'])
                if result is None:return
                if result.get('errorCode'):
                    finalize(aid,'Cancelled Job',codes=[result['errorCode']]);return
                records=result['output']
            audit.append({'sequence':0,'ruleName':'File parsing','category':'Ingestion','attempt':1,'startTime':started,'endTime':now(),'durationMs':round((time.monotonic()-parse_clock)*1000),'result':'Successful','errorCode':None,'message':f'{len(records)} rows parsed.'})
        except Exception:
            finalize(aid,'Cancelled Job',codes=['INPUT_PARSE_ERROR']);return
        metrics=decode(attempt['metrics'],{})
        received_metrics(metrics,records)
        pipeline=decode(attempt['pipeline'],[])
        # Cleaning count is the output at the last Cleaning step, before later transformations.
        metrics['rowsAfterCleaning']=len(records) if not any(r['category']=='Cleaning' for r in pipeline) else None
        with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
        for sequence, rule in enumerate(pipeline,1):
            for retry in range(1,4):
                attempt=active(aid)
                if not attempt:return
                if time.time()>=attempt['deadline']:
                    finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return
                started=now();clock=time.monotonic()
                progress={'sequence':sequence,'ruleName':rule.get('name',rule['operation']),'attempt':retry,'totalRules':len(pipeline)}
                with get_db_connection() as db: db.execute('UPDATE batch_attempts SET progress=? WHERE id=?',(json.dumps(progress),aid))
                result=None
                executor=app.config.get('BATCH_TEST_EXECUTOR')
                if app.testing and executor:
                    try:result=executor(records,rule)
                    except Exception:result={'errorCode':'RULE_EXECUTION_ERROR','message':'Rule execution failed unexpectedly.'}
                else:
                    result=process_result(aid,execute_step,(records,rule),attempt['deadline'])
                    if result is None:return
                if not active(aid):return
                if time.time()>=attempt['deadline']:
                    finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return
                findings=result.get('issueCount',0)
                failed=bool(result.get('errorCode')) or findings>0
                code=result.get('errorCode') or (FINDING_CODES.get(rule['operation'],'RULE_VALIDATION_FAILED') if findings else None)
                audit.append({'sequence':sequence,'ruleId':rule['id'],'ruleName':rule.get('name',rule['operation']),'category':rule['category'],'attempt':retry,
                              'startTime':started,'endTime':now(),'durationMs':round((time.monotonic()-clock)*1000),'result':'Fail Execution' if failed or findings else 'Successful',
                              'executionCode':'908' if failed else '909',
                              'errorCode':code,'message':result.get('message') or (f'{findings} data validation findings.' if findings else 'Rule executed successfully.'),
                              'issueCount':findings,'changedCells':result.get('changedCells',0)})
                if failed:
                    interrupted=True
                    if code not in codes:codes.append(code)
                    if retry==3:finalize(aid,'Cancelled Job',codes=codes+['RULE_RETRY_LIMIT']);return
                    continue
                interrupted=interrupted or bool(findings)
                if code and code not in codes:codes.append(code)
                records=result['output']
                if rule['category']=='Cleaning':
                    metrics['rowsAfterCleaning']=len(records)
                    with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                break
        if not active(aid):return
        if time.time()>=attempt['deadline']:finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return
        finalize(aid,'Completed with Interruption' if interrupted else 'Completed',records,audit,codes)

    def launch(retailer_id,period,filename,source,store_field=''):
        try:
            year,week=period.split('-W');datetime.fromisocalendar(int(year),int(week),1)
            if period!=f'{int(year):04d}-W{int(week):02d}':raise ValueError()
        except (ValueError,AttributeError):return error('Choose a valid ISO week, for example 2026-W41.')
        with get_db_connection() as db:
            retailer=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(retailer_id,)).fetchone()
            if not retailer:return error('Retailer not found.',404)
            config=json.loads(retailer['payload']);pipeline=config.get('pipeline',[])
            try:validate_pipeline(pipeline)
            except ValueError as exc:return error(str(exc))
            if not isinstance(store_field,str) or len(store_field)>200:return error('Store ID column must be at most 200 characters.')
            previous=db.execute("SELECT source FROM batch_jobs WHERE retailer_id=? AND period=? AND status!='Cancelled Job'",(retailer_id,previous_period(period))).fetchone()
            metrics=input_metrics(source,period,config.get('stores',[]),previous,store_field.strip())
            aid='BATCH-'+uuid.uuid4().hex[:12]
            deadline=time.time()+float(app.config.get('BATCH_TIMEOUT_SECONDS',300))
            try:
                db.execute('INSERT INTO batch_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)',(aid,retailer_id,config['name'],period,now(),filename,source,json.dumps(pipeline),deadline,'{}',json.dumps(metrics)))
            except sqlite3.IntegrityError:return error('A job is already processing for this retailer and week.',409)
        if app.config.get('BATCH_DEFER_WORKER') and app.testing:
            pass
        else:
            def guarded():
                try:run(aid)
                except Exception:
                    app.logger.exception('Batch worker failed')
                    finalize(aid,'Cancelled Job',codes=['JOB_INTERNAL_ERROR'])
            threading.Thread(target=guarded,daemon=True).start()
        return jsonify(success=True,attemptId=aid),202

    @app.route('/api/v1/batches',methods=['GET','POST'])
    def batches():
        if request.method=='GET':
            with get_db_connection() as db:
                jobs=[public_job(r) for r in db.execute('SELECT * FROM batch_jobs ORDER BY start_time DESC')]
                pending=[{k:r[k] for k in ['id','retailer_id','retailer_name','period','start_time','filename']} | {'progress':decode(r['progress'],{})} for r in db.execute('SELECT * FROM batch_attempts ORDER BY start_time DESC')]
            return jsonify(success=True,jobs=jobs,active=pending)
        file=request.files.get('file')
        if not file or not file.filename:return error('Select a batch data file.')
        return launch(request.form.get('retailerId',''),request.form.get('period',''),file.filename,file.read(),request.form.get('storeIdField',''))

    @app.route('/api/v1/batches/<aid>/status')
    def status(aid):
        attempt=active(aid)
        if attempt:return jsonify(success=True,processing=True,progress=decode(attempt['progress'],{}))
        with get_db_connection() as db:
            job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(aid,)).fetchone()
            if job:return jsonify(success=True,processing=False,job=public_job(job))
            row=db.execute("SELECT last_attempt FROM batch_jobs WHERE json_extract(last_attempt,'$.id')=?",(aid,)).fetchone()
        if row:return jsonify(success=True,processing=False,job=decode(row['last_attempt'],{}))
        return error('Job no longer exists; it may have been replaced.',404)

    @app.route('/api/v1/batches/<jid>/audit')
    def audit(jid):
        with get_db_connection() as db:job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
        if not job:return error('Job not found.',404)
        if job['status']=='Cancelled Job':return error('Cancelled jobs have no audit log.',404)
        return jsonify(success=True,job=public_job(job),entries=decode(job['audit'],[]))

    @app.route('/api/v1/batches/<jid>/reprocess',methods=['POST'])
    def reprocess(jid):
        with get_db_connection() as db:job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
        if not job:return error('Job not found.',404)
        body=request.get_json(silent=True)
        if body is None:body={}
        if not isinstance(body,dict):return error('Invalid reprocessing request.')
        return launch(job['retailer_id'],body.get('period',job['period']),job['filename'],job['source'],decode(job['metrics'],{}).get('storeIdField',''))

    @app.route('/api/v1/batches/<jid>/approve',methods=['POST'])
    def approve(jid):
        with get_db_connection() as db:
            db.execute('BEGIN IMMEDIATE');job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            if db.execute('SELECT id FROM batch_attempts WHERE retailer_id=? AND period=?',(job['retailer_id'],job['period'])).fetchone():return error('Wait for or cancel the reprocessing attempt before approving.',409)
            if job['status'] not in ['Completed','Completed with Interruption']:return error('Only completed jobs can be approved.',409)
            metrics=decode(job['metrics'],{})
            retailer=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(job['retailer_id'],)).fetchone()
            if not retailer:return error('Retailer not found.',404)
            config=json.loads(retailer['payload']);existing=config.get('stores',[])
            known={store['key'].casefold() for store in existing}
            additions=[{**store,'status':'Active','exception':False,'address':''} for store in metrics.get('newStores') or [] if store['key'].casefold() not in known]
            if additions:
                try:
                    updated=validate_retailer({**config,'stores':existing+additions})
                    updated['stores']=assign_store_codes(updated['stores'],existing,db)
                except ValueError as exc:return error('New stores require review before approval: '+str(exc))
                db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(updated),job['retailer_id']))
            metrics['newStoresAddedOnApproval']=len(additions)
            db.execute('UPDATE batch_jobs SET metrics=? WHERE id=?',(json.dumps(metrics),jid))
            entries=decode(job['audit'],[])
            stamp=now();entries.append({'sequence':None,'ruleName':'Job approval','category':'Action','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Successful','errorCode':None,'message':'Approved by operator action.'})
            db.execute('UPDATE batch_jobs SET status=?,audit=? WHERE id=?',('Approved Job',json.dumps(entries),jid))
        return jsonify(success=True)

    @app.route('/api/v1/batches/<jid>/cancel',methods=['POST'])
    def cancel(jid):
        if active(jid) and finalize(jid,'Cancelled Job',codes=['JOB_CANCELLED_BY_USER']):return jsonify(success=True)
        with get_db_connection() as db:
            db.execute('BEGIN IMMEDIATE');job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            if db.execute('SELECT id FROM batch_attempts WHERE retailer_id=? AND period=?',(job['retailer_id'],job['period'])).fetchone():return error('Cancel the active reprocessing attempt using its Cancel Job button.',409)
            db.execute('UPDATE batch_jobs SET status=?,end_time=NULL,audit=NULL,output=NULL,error_codes=? WHERE id=?',('Cancelled Job',json.dumps(['JOB_CANCELLED_BY_USER']),jid))
        return jsonify(success=True)

    # Spawned rule processes import the main module on Windows; recovery runs only in the server.
    if multiprocessing.current_process().name=='MainProcess':
        with get_db_connection() as db:stale=[r['id'] for r in db.execute('SELECT id FROM batch_attempts')]
        for aid in stale:finalize(aid,'Cancelled Job',codes=['JOB_SERVER_RESTARTED'])
    app.extensions['batch_run']=run
    app.extensions['batch_finalize']=finalize
