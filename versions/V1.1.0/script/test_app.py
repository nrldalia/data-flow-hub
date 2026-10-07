import io,json,os,tempfile,unittest,zipfile
from pathlib import Path
_temp=tempfile.TemporaryDirectory();os.environ['DATAFLOW_DB']=str(Path(_temp.name)/'test.db')
import app as module
class APITests(unittest.TestCase):
 def setUp(self): self.client=module.app.test_client()
 def upload(self,records,rules=None,name='test.json'):
  return self.client.post('/api/v1/upload-and-clean',data={'file':(io.BytesIO(json.dumps(records).encode()),name),'rules':json.dumps(rules or {})},content_type='multipart/form-data')
 def test_all_rows_and_audit_history(self):
  records=[{'sku':f' sku{i} ','sales':str(i)} for i in range(9)]
  r=self.upload(records,{'trim':True,'numericFields':['sales']});self.assertEqual(r.status_code,200);d=r.json
  self.assertEqual(d['totalRows'],9);self.assertEqual(len(d['cleanedSample']),5);self.assertEqual(d['rawSample'][0]['sku'],' sku0 ')
  exported=self.client.post('/api/v1/export',json={'runId':d['runId'],'fileType':'json'});self.assertEqual(len(json.loads(exported.data)),9)
  loaded=self.client.get('/api/v1/runs/'+d['runId']).json;self.assertEqual(loaded['changedCells'],18);self.assertEqual(len(loaded['transformationTrace']),18)
  audit=self.client.get('/api/v1/runs/'+d['runId']+'/audit');self.assertEqual(audit.status_code,200)
  with zipfile.ZipFile(io.BytesIO(audit.data)) as z: self.assertEqual(json.loads(z.read('original.json')),records)
 def test_store_update_persists(self):
  r=self.client.put('/api/v1/stores/ST-101',json={'store_name':'Updated store','status':'Pending','region':'Malaysia'});self.assertEqual(r.status_code,200)
  self.assertEqual(next(s for s in self.client.get('/api/v1/stores').json['stores'] if s['store_id']=='ST-101')['store_name'],'Updated store')
 def test_bad_input_and_nonexistent(self):
  self.assertEqual(self.upload([]).status_code,400)
  self.assertEqual(self.upload([{'a':1}],{'numericFields':['unknown']}).status_code,400)
  self.assertEqual(self.client.post('/api/v1/export',json={'runId':'unknown'}).status_code,404)
 def test_issues_retained_without_invention(self):
  r=self.upload([{'sales':'oops','date':'03/04/2026','sku':''}]*2,{'numericFields':['sales'],'dateFields':['date'],'dateFormat':'%Y-%m-%d','requiredFields':['sku']}).json
  self.assertEqual(r['issueRows'],2);self.assertEqual(r['cleanedSample'][0]['sales'],'oops');self.assertEqual(r['outputRows'],2)
 def test_excel_and_csv(self):
  import pandas as pd
  for ext in ['csv','xlsx']:
   b=io.BytesIO()
   if ext=='csv':b.write(b'code,sales\n001,10\n002,20\n')
   else:
    with pd.ExcelWriter(b,engine='openpyxl') as w:pd.DataFrame({'code':['001','002'],'sales':['10','20']}).to_excel(w,index=False)
   b.seek(0);r=self.client.post('/api/v1/upload-and-clean',data={'file':(b,'test.'+ext)},content_type='multipart/form-data');self.assertEqual(r.status_code,200)
   exported=self.client.post('/api/v1/export',json={'runId':r.json['runId'],'fileType':ext});self.assertEqual(exported.status_code,200);self.assertEqual(r.json['rawSample'][0]['code'],'001')
 def test_ai_consent_and_missing_key(self):
  self.assertEqual(self.client.post('/api/v1/ai-assist',json={}).status_code,400)
  os.environ.pop('GEMINI_API_KEY',None)
  self.assertEqual(self.client.post('/api/v1/ai-assist',json={'consent':True}).status_code,503)
 def test_served_react_app(self):
  import re
  page=self.client.get('/');self.assertEqual(page.status_code,200)
  asset=re.search(rb'src="(/assets/[^"]+)"',page.data);self.assertIsNotNone(asset)
  self.assertEqual(self.client.get(asset.group(1).decode()).status_code,200)
 def test_run_metrics(self):
  r=self.upload([{'a':' x '}]).json
  saved=next(v for v in self.client.get('/api/v1/runs').json['runs'] if v['id']==r['runId']);self.assertEqual(saved['changedCells'],1)
if __name__=='__main__':unittest.main()
