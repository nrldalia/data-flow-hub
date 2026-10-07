"""Original Flask architecture, enhanced deterministic processing and audit persistence."""
import io, os, json, uuid, hashlib
from datetime import datetime, timezone
import pandas as pd
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from database import get_db_connection, init_db, seed_db

app=Flask(__name__,static_folder="../frontend-github/dist/assets",static_url_path="/assets")
app.config['MAX_CONTENT_LENGTH']=50*1024*1024
CORS(app,origins=['http://localhost:5173','http://127.0.0.1:5173'])
init_db();seed_db()
with get_db_connection() as c:
 c.execute('CREATE TABLE IF NOT EXISTS run_evidence(run_id TEXT PRIMARY KEY,payload_id INTEGER,source BLOB,trace TEXT)')
 c.execute('CREATE TABLE IF NOT EXISTS processing_runs(id TEXT PRIMARY KEY,created_at TEXT,filename TEXT,file_type TEXT,input_rows INTEGER,result TEXT,source_hash TEXT,rules TEXT,output TEXT,raw_preview TEXT,issues TEXT)')

def error(message,status=400): return jsonify(success=False,error=message),status
@app.errorhandler(413)
def too_large(e): return error('File exceeds the 50 MB upload limit.',413)
@app.route('/')
def homepage(): return send_from_directory(os.path.join(os.path.dirname(__file__),'..','frontend-github','dist'),'index.html')
@app.route('/api/v1/health')
def health(): return jsonify(success=True,aiConfigured=bool(os.getenv('GEMINI_API_KEY')),version='1.1.0')
@app.route('/api/v1/stores')
def get_stores():
 with get_db_connection() as c:
  rows=[dict(r) for r in c.execute("SELECT id as store_id,store_name,region,status FROM stores WHERE id != 'FILE_UPLOAD'")]
  for row in rows:
   latest=c.execute('SELECT missing_fields_count FROM raw_data_payloads WHERE store_id=? ORDER BY id DESC LIMIT 1',(row['store_id'],)).fetchone()
   row['missing_fields']=latest[0] if latest else 0
 return jsonify(success=True,stores=rows)
@app.route('/api/v1/stores/<store_id>',methods=['PUT'])
def update_store(store_id):
 data=request.get_json(silent=True) or {}
 if not isinstance(data,dict): return error('Invalid store body.')
 if not str(data.get('store_name','')).strip(): return error('Store name is required.')
 if data.get('status') not in ['Clean','Error','Pending']: return error('Invalid store status.')
 with get_db_connection() as c:
  if not c.execute('SELECT id FROM stores WHERE id=?',(store_id,)).fetchone(): return error('Store not found.',404)
  c.execute('UPDATE stores SET store_name=?,region=?,status=? WHERE id=?',(data['store_name'].strip(),data.get('region',''),data['status'],store_id))
 return jsonify(success=True)

def parse_upload(file):
 name=file.filename.lower(); content=file.read()
 if name.endswith('.csv'):
  df=pd.read_csv(io.BytesIO(content),dtype=str,keep_default_na=False); records=df.to_dict('records'); kind='csv'
 elif name.endswith('.xlsx'):
  df=pd.read_excel(io.BytesIO(content),dtype=str,keep_default_na=False);records=df.to_dict('records');kind='xlsx'
 elif name.endswith('.json'):
  records=json.loads(content.decode('utf-8-sig'));records=[records] if isinstance(records,dict) else records;kind='json'
 else: raise ValueError('Upload CSV, Excel or JSON.')
 if not isinstance(records,list) or not records or not all(isinstance(r,dict) for r in records): raise ValueError('Upload a nonempty list of records or a single JSON object.')
 if any(not isinstance(k,str) for r in records for k in r): raise ValueError('Field names must be text.')
 return records,kind,content

def clean(records,rules):
 out=[];trace=[];issues=[]
 numeric=rules.get('numericFields',[]);date_fields=rules.get('dateFields',[]);required=rules.get('requiredFields',[])
 if any(not isinstance(v,list) or not all(isinstance(k,str) for k in v) for v in [numeric,date_fields,required]): raise ValueError('Rule field lists must contain field names.')
 columns=set(k for r in records for k in r)
 if (set(numeric)|set(date_fields)|set(required))-columns: raise ValueError('Configured field not found in uploaded data.')
 if set(numeric)&set(date_fields): raise ValueError('A field cannot be both numeric and date.')
 fmt=rules.get('dateFormat','')
 if date_fields and not fmt: raise ValueError('Provide an explicit input date format.')
 for row_no,record in enumerate(records,1):
  result=dict(record)
  for field,value in record.items():
   new=value;actions=[]
   if rules.get('trim',True) and isinstance(new,str):
    new=new.strip()
    if new!=value: actions.append('Trim whitespace')
   if field in numeric and new is not None and new!='':
    try:
     number=pd.to_numeric(new,errors='raise')
     if not pd.notna(number) or not float('-inf')<float(number)<float('inf'): raise ValueError()
     new=float(number) if float(number)%1 else int(number);actions.append('Convert numeric')
    except (ValueError,TypeError,OverflowError): issues.append({'row':row_no,'field':field,'issue':'Invalid numeric; original retained'})
   if field in date_fields and new is not None and new!='':
    try: new=datetime.strptime(str(new),fmt).strftime('%Y-%m-%d');actions.append('Standardise date')
    except (ValueError,TypeError): issues.append({'row':row_no,'field':field,'issue':'Invalid date; original retained'})
   result[field]=new
   if new!=value or type(new) is not type(value): trace.append({'step':len(trace)+1,'row':row_no,'field':field,'before':value,'after':new,'action':'; '.join(actions)})
  for field in required:
   if result.get(field) is None or str(result.get(field,'')).strip()=='': issues.append({'row':row_no,'field':field,'issue':'Missing required value'})
  out.append(result)
 if rules.get('flagDuplicates',True):
  seen={}
  for i,r in enumerate(out,1): seen.setdefault(json.dumps(r,sort_keys=True,default=str),[]).append(i)
  for rows in seen.values():
   if len(rows)>1: issues.extend({'row':i,'field':'record','issue':'Duplicate record; retained'} for i in rows)
 return out,trace,issues
@app.route('/api/v1/upload-and-clean',methods=['POST'])
def upload_and_clean():
 file=request.files.get('file')
 if not file or not file.filename: return error('No file uploaded.')
 try:
  records,kind,content=parse_upload(file); rules=json.loads(request.form.get('rules','{}'))
  if not isinstance(rules,dict): raise ValueError('Invalid rules.')
  output,trace,issues=clean(records,rules);rid='RUN-'+uuid.uuid4().hex[:10];created=datetime.now(timezone.utc).isoformat()
  with get_db_connection() as c:
   c.execute("INSERT OR IGNORE INTO stores(id,store_name,status) VALUES('FILE_UPLOAD','Uploaded Files Directory','Pending')")
   cursor=c.execute('INSERT INTO raw_data_payloads(store_id,raw_json_payload,missing_fields_count) VALUES(?,?,?)',('FILE_UPLOAD',json.dumps(records),sum(i['issue']=='Missing required value' for i in issues)))
   payload_id=cursor.lastrowid
   for t in trace: c.execute('INSERT INTO transformation_traces(payload_id,step_number,field_name,action_taken,cleaned_json_payload) VALUES(?,?,?,?,?)',(payload_id,t['step'],t['field'],json.dumps(t),None))
   c.execute('INSERT INTO run_evidence VALUES(?,?,?,?)',(rid,payload_id,content,json.dumps(trace)))
   c.execute('INSERT INTO processing_runs VALUES(?,?,?,?,?,?,?,?,?,?,?)',(rid,created,file.filename,kind,len(records),'Completed',hashlib.sha256(content).hexdigest(),json.dumps(rules),json.dumps(output),json.dumps(records[:25]),json.dumps(issues)))
  return jsonify(success=True,runId=rid,filename=file.filename,fileType=kind,totalRows=len(records),outputRows=len(output),rawSample=records[:25],cleanedSample=output[:25],transformationTrace=trace,issues=issues,changedCells=len(trace),issueRows=len({i['row'] for i in issues}))
 except (ValueError,UnicodeDecodeError,TypeError) as e: return error(str(e))
 except Exception: app.logger.exception('Upload processing failed'); return error('Processing failed. Check the backend terminal for details.',500)
@app.route('/api/v1/runs')
def runs():
 with get_db_connection() as c:
  rows=[]
  for r in c.execute('SELECT * FROM processing_runs ORDER BY created_at DESC'):
   issues=json.loads(r['issues']); evidence=c.execute('SELECT trace FROM run_evidence WHERE run_id=?',(r['id'],)).fetchone()
   rows.append({k:r[k] for k in ['id','created_at','filename','file_type','input_rows','result']} | {'issueRows':len({i['row'] for i in issues}),'changedCells':len(json.loads(evidence['trace'])) if evidence else 0,'outputRows':len(json.loads(r['output']))})
 return jsonify(success=True,runs=rows)
@app.route('/api/v1/runs/<rid>')
def run_detail(rid):
 with get_db_connection() as c:
  r=c.execute('SELECT * FROM processing_runs WHERE id=?',(rid,)).fetchone()
  if not r: return error('Run not found.',404)
  evidence=c.execute('SELECT trace FROM run_evidence WHERE run_id=?',(rid,)).fetchone()
  traces=json.loads(evidence['trace']) if evidence else []
 return jsonify(success=True,runId=r['id'],filename=r['filename'],fileType=r['file_type'],totalRows=r['input_rows'],outputRows=len(json.loads(r['output'])),rawSample=json.loads(r['raw_preview']),cleanedSample=json.loads(r['output'])[:25],issues=json.loads(r['issues']),transformationTrace=traces,changedCells=len(traces),issueRows=len({i['row'] for i in json.loads(r['issues'])}),rules=json.loads(r['rules']))
@app.route('/api/v1/runs/<rid>/audit')
def audit_export(rid):
 import zipfile
 with get_db_connection() as c:
  r=c.execute('SELECT * FROM processing_runs WHERE id=?',(rid,)).fetchone()
  e=c.execute('SELECT source,trace FROM run_evidence WHERE run_id=?',(rid,)).fetchone()
 if not r or not e: return error('Run not found.',404)
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('original.'+r['file_type'],e['source'])
  z.writestr('cleaned.json',r['output']);z.writestr('changes.json',e['trace']);z.writestr('issues.json',r['issues']);z.writestr('rules.json',r['rules'])
  z.writestr('metadata.json',json.dumps({k:r[k] for k in ['id','created_at','filename','input_rows','source_hash']},indent=2))
 b.seek(0);return send_file(b,mimetype='application/zip',as_attachment=True,download_name=rid+'_audit.zip')
@app.route('/api/v1/export',methods=['POST'])
def export_dataset():
 data=request.get_json(silent=True) or {};rid=data.get('runId')
 if not rid: return error('A saved run ID is required to export the full dataset.')
 with get_db_connection() as c: row=c.execute('SELECT output,file_type FROM processing_runs WHERE id=?',(rid,)).fetchone()
 if not row: return error('Run not found.',404)
 output=json.loads(row['output']);kind=data.get('fileType',row['file_type']);b=io.BytesIO()
 if kind=='csv': b.write(pd.DataFrame(output).to_csv(index=False).encode('utf-8-sig'));mime='text/csv'
 elif kind=='xlsx':
  with pd.ExcelWriter(b,engine='openpyxl') as w: pd.DataFrame(output).to_excel(w,index=False,sheet_name='Cleaned')
  mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
 elif kind=='json': b.write(json.dumps(output,indent=2).encode());mime='application/json'
 else: return error('Unsupported export format.')
 b.seek(0);return send_file(b,mimetype=mime,as_attachment=True,download_name=f'{rid}_cleaned.{kind}')
@app.route('/api/v1/ai-assist',methods=['POST'])
def ai_assist():
 if os.getenv('DATAFLOW_AI_ENABLED','').lower() != 'true': return error('Analysis is dormant.',403)
 from ai_assistant import suggest
 body=request.get_json(silent=True) or {}
 if not body.get('consent'): return error('Explicit sample-sharing consent is required.')
 try:
  result=suggest(os.getenv('GEMINI_API_KEY',''),os.getenv('GEMINI_MODEL','gemini-2.5-flash'),'Return {"summary":"...", "suggested_rules":["..."]}. Explain the supplied issues and recommend rules. Never invent values or execute changes.',{'sample':body.get('sample',[])[:5],'issues':body.get('issues',[])[:20]})
  return jsonify(success=True,assistance=result)
 except Exception: return error('AI is unavailable. Check your key, model, network and quota. Automated processing remains available.',503)

def cleaning_log(rid):
 with get_db_connection() as c:
  run=c.execute('SELECT * FROM processing_runs WHERE id=?',(rid,)).fetchone()
  ev=c.execute('SELECT trace FROM run_evidence WHERE run_id=?',(rid,)).fetchone()
 if not run: return None,[]
 rows=[{'row':t['row'],'field':t['field'],'status':'Changed','before':t['before'],'after':t['after'],'action':t['action']} for t in json.loads(ev['trace'] if ev else '[]')]
 output=json.loads(run['output'])
 rows += [{'row':i['row'],'field':i['field'],'status':'Review','before':output[i['row']-1].get(i['field'],''),'after':output[i['row']-1].get(i['field'],''),'action':i['issue']} for i in json.loads(run['issues'])]
 return run,sorted(rows,key=lambda r:r['row'])
@app.route('/api/v1/runs/<rid>/log')
def log_export(rid):
 import csv
 run,rows=cleaning_log(rid)
 if run is None: return error('Run not found.',404)
 b=io.StringIO();writer=csv.DictWriter(b,fieldnames=['row','field','status','before','after','action']);writer.writeheader();writer.writerows(rows)
 return send_file(io.BytesIO(b.getvalue().encode('utf-8-sig')),mimetype='text/csv',as_attachment=True,download_name=rid+'_cleaning_log.csv')
@app.route('/api/v1/runs/<rid>/print')
def print_log(rid):
 from html import escape
 run,rows=cleaning_log(rid)
 if run is None: return error('Run not found.',404)
 body=''.join('<tr>'+''.join('<td>'+escape(str(r[k]))+'</td>' for k in ['row','field','status','before','after','action'])+'</tr>' for r in rows)
 return '<!doctype html><html><head><title>Cleaning log</title><style>body{font:12px Arial}table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;padding:6px;overflow-wrap:anywhere}thead{display:table-header-group}@media print{button{display:none}}</style></head><body><button onclick="window.print()">Print / Save as PDF</button><h1>DataFlow V1.1.0 cleaning log</h1><p>'+escape(run['filename'])+' | '+escape(rid)+' | '+str(len(rows))+' entries</p><table><thead><tr><th>Row</th><th>Field</th><th>Status</th><th>Before</th><th>After</th><th>Action / detection</th></tr></thead><tbody>'+body+'</tbody></table></body></html>'

if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
