import io,json,os,threading,time,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
test_dir=tempfile.TemporaryDirectory()
os.environ['DATAFLOW_DB']=str(Path(test_dir.name)/'batch_test.db')
from database import get_db_connection
import app
from retailer_setup import apply_pipeline

def execute(records,rule):
    output,steps,issues,trace=apply_pipeline(records,[rule])
    return {'output':output,'issueCount':len(issues),'changedCells':len(trace)}

class BatchJobTests(unittest.TestCase):
    def setUp(self):
        self.old_testing=app.app.testing;app.app.testing=True
        self.previous={k:app.app.config.get(k) for k in ['BATCH_DEFER_WORKER','BATCH_TEST_EXECUTOR','BATCH_TIMEOUT_SECONDS']}
        app.app.config.update(BATCH_DEFER_WORKER=True,BATCH_TEST_EXECUTOR=execute,BATCH_TIMEOUT_SECONDS=300)
        self.client=app.app.test_client()
        with get_db_connection() as db:
            db.execute('DELETE FROM batch_attempts');db.execute('DELETE FROM batch_jobs')
        self.rule={'id':'trim','name':'Trim SKU','category':'Cleaning','operation':'trim','field':'sku'}
        self.config={'name':'Batch Retailer','key':'BATCH_'+os.urandom(4).hex(),'serviceType':'SM','senderEmail':'sender@example.com','retailerEmail':'','stores':[],'pipeline':[self.rule],'sectionOrder':['Cleaning','Transformation','Validation']}
        self.retailer=self.client.post('/api/v1/retailers',json=self.config).get_json()['retailer']['id']

    def tearDown(self):
        app.app.testing=self.old_testing
        for key,value in self.previous.items():
            if value is None:app.app.config.pop(key,None)
            else:app.app.config[key]=value

    def start(self,period='2026-W41',source=b'sku\n item \n'):
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(source),'batch.csv'),'retailerId':self.retailer,'period':period})
        self.assertEqual(response.status_code,202,response.data)
        return response.get_json()['attemptId']

    def finish(self,aid):app.app.extensions['batch_run'](aid)
    def jobs(self):return self.client.get('/api/v1/batches').get_json()['jobs']
    def complete(self):
        aid=self.start();self.finish(aid);return self.jobs()[0]

    def test_completed_audit_has_timings_without_data_preview(self):
        job=self.complete();self.assertEqual(job['status'],'Completed');self.assertTrue(job['end_time'])
        audit=self.client.get('/api/v1/batches/'+job['id']+'/audit').get_json()
        self.assertEqual([e['result'] for e in audit['entries']],['Successful','Successful'])
        self.assertEqual(audit['entries'][1]['executionCode'],'909')
        self.assertTrue(all(e['startTime'] and e['endTime'] for e in audit['entries']))
        text=json.dumps(audit)
        for prohibited in ['rawSample','cleanedSample','before','after','output',' item ']:self.assertNotIn(prohibited,text)

    def test_recovered_retry_completes_with_interruption(self):
        calls=[]
        def flaky(records,rule):
            calls.append(1)
            if len(calls)==1:return {'errorCode':'RULE_EXECUTION_ERROR','message':'Rule execution failed.'}
            return execute(records,rule)
        app.app.config['BATCH_TEST_EXECUTOR']=flaky
        job=self.complete();self.assertEqual(job['status'],'Completed with Interruption');self.assertEqual(len(calls),2)
        entries=self.client.get('/api/v1/batches/'+job['id']+'/audit').get_json()['entries']
        self.assertEqual([e['result'] for e in entries[1:]],['Fail Execution','Successful'])
        self.assertEqual([e['executionCode'] for e in entries[1:]],['908','909'])

    def test_rule_failure_three_times_cancels_without_end_or_audit(self):
        calls=[]
        def failed(records,rule):calls.append(1);return {'errorCode':'RULE_FIELD_MISSING','message':'Missing field.'}
        app.app.config['BATCH_TEST_EXECUTOR']=failed
        job=self.complete();self.assertEqual(len(calls),3);self.assertEqual(job['status'],'Cancelled Job')
        self.assertIsNone(job['end_time']);self.assertFalse(job['hasAudit']);self.assertIn('RULE_FIELD_MISSING',job['errorCodes']);self.assertIn('RULE_RETRY_LIMIT',job['errorCodes'])
        self.assertEqual(self.client.get('/api/v1/batches/'+job['id']+'/audit').status_code,404)
        with get_db_connection() as db:
            row=db.execute('SELECT audit,output FROM batch_jobs WHERE id=?',(job['id'],)).fetchone()
            self.assertIsNone(row['audit']);self.assertIsNone(row['output'])

    def test_data_findings_cancel_after_three_attempts(self):
        numeric={**self.rule,'operation':'numeric','category':'Transformation'}
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[numeric]})
        job=self.complete();self.assertEqual(job['status'],'Cancelled Job');self.assertIn('RULE_NUMERIC_INVALID',job['errorCodes'])

    def test_timeout_cancellation(self):
        aid=self.start()
        with get_db_connection() as db:db.execute('UPDATE batch_attempts SET deadline=? WHERE id=?',(time.time()-1,aid))
        self.finish(aid);job=self.jobs()[0];self.assertEqual(job['status'],'Cancelled Job');self.assertIn('JOB_TIMEOUT',job['errorCodes']);self.assertIsNone(job['end_time'])

    def test_approval_and_cancellation_statuses(self):
        job=self.complete();jid=job['id']
        self.assertEqual(self.client.post('/api/v1/batches/'+jid+'/approve').status_code,200)
        self.assertEqual(self.jobs()[0]['status'],'Approved Job')
        self.assertEqual(self.client.post('/api/v1/batches/'+jid+'/cancel').status_code,200)
        job=self.jobs()[0];self.assertEqual(job['status'],'Cancelled Job');self.assertIsNone(job['end_time']);self.assertFalse(job['hasAudit'])
        self.assertEqual(self.client.post('/api/v1/batches/'+jid+'/approve').status_code,409)

    def test_successful_replacement_deletes_old_record_and_source(self):
        old=self.complete();new=self.start(source=b'sku\n replacement \n')
        self.assertEqual(self.jobs()[0]['id'],old['id'])
        self.finish(new);self.assertEqual(len(self.jobs()),1);self.assertEqual(self.jobs()[0]['id'],new)
        self.assertEqual(self.client.get('/api/v1/batches/'+old['id']+'/audit').status_code,404)
        with get_db_connection() as db:
            self.assertIsNone(db.execute('SELECT * FROM batch_jobs WHERE id=?',(old['id'],)).fetchone())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_attempts').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT source FROM batch_jobs').fetchone()[0],b'sku\n replacement \n')

    def test_cancelled_replacement_preserves_previous_job(self):
        old=self.complete();response=self.client.post('/api/v1/batches/'+old['id']+'/reprocess');aid=response.get_json()['attemptId']
        self.assertEqual(self.client.post('/api/v1/batches/'+aid+'/cancel').status_code,200)
        self.finish(aid);job=self.jobs()[0];self.assertEqual(job['id'],old['id']);self.assertEqual(job['status'],'Completed');self.assertTrue(job['hasAudit'])
        self.assertEqual(job['lastAttempt']['status'],'Cancelled Job');self.assertIsNone(job['lastAttempt']['end_time'])
        self.assertEqual(len(self.jobs()),1)
        self.assertEqual(self.client.get('/api/v1/batches/'+aid+'/status').get_json()['job']['status'],'Cancelled Job')

    def test_failed_replacement_preserves_previous_and_shows_error(self):
        old=self.complete();app.app.config['BATCH_TEST_EXECUTOR']=lambda records,rule:{'errorCode':'RULE_EXECUTION_ERROR','message':'Failed'}
        aid=self.start();self.finish(aid);job=self.jobs()[0]
        self.assertEqual(job['id'],old['id']);self.assertIn('RULE_EXECUTION_ERROR',job['lastAttempt']['errorCodes']);self.assertEqual(len(self.jobs()),1)

    def test_cancel_race_cannot_commit_after_cancel(self):
        old=self.complete();entered=threading.Event();release=threading.Event()
        def paused(records,rule):entered.set();release.wait(3);return execute(records,rule)
        app.app.config['BATCH_TEST_EXECUTOR']=paused;aid=self.start()
        thread=threading.Thread(target=self.finish,args=(aid,));thread.start();self.assertTrue(entered.wait(3))
        self.client.post('/api/v1/batches/'+aid+'/cancel');release.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertEqual(self.jobs()[0]['id'],old['id'])

    def test_duplicate_active_job_rejected_but_other_week_allowed(self):
        aid=self.start()
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku\nx'),'batch.csv'),'retailerId':self.retailer,'period':'2026-W41'})
        self.assertEqual(response.status_code,409)
        other=self.start('2026-W42');self.finish(aid);self.finish(other);self.assertEqual(len(self.jobs()),2)

    def test_invalid_week_and_parse_error(self):
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku\nx'),'batch.csv'),'retailerId':self.retailer,'period':'2026-W99'})
        self.assertEqual(response.status_code,400)
        aid=self.start(source=b'');self.finish(aid);self.assertIn('INPUT_PARSE_ERROR',self.jobs()[0]['errorCodes'])

    def test_reprocess_uses_latest_rules(self):
        old=self.complete();missing={**self.rule,'field':'missing'}
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[missing]})
        response=self.client.post('/api/v1/batches/'+old['id']+'/reprocess');aid=response.get_json()['attemptId']
        app.app.config['BATCH_TEST_EXECUTOR']=lambda records,rule:{'errorCode':'RULE_FIELD_MISSING','message':'Missing field.'}
        self.finish(aid);self.assertIn('RULE_FIELD_MISSING',self.jobs()[0]['lastAttempt']['errorCodes'])

if __name__=='__main__':unittest.main()
