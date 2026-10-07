import io
import json
import os
import tempfile
import unittest
from pathlib import Path

# Use an isolated database; no actual retailer/sample data is needed by tests.
test_dir = tempfile.TemporaryDirectory()
os.environ['DATAFLOW_DB'] = str(Path(test_dir.name) / 'retailer_test.db')
import app
from retailer_setup import apply_pipeline

def rule(op, category, field='sku', **settings):
    return {'id':op + str(settings),'name':op,'category':category,'operation':op,'field':field,**settings}

class RetailerSetupTests(unittest.TestCase):
    def setUp(self):
        self.client=app.app.test_client()
        self.body={'name':'Test Retailer','key':'TEST_'+os.urandom(5).hex(),'serviceType':'SM','senderEmail':'internal@example.com','retailerEmail':'','stores':[{'key':'S1','name':'Main Store'}],'pipeline':[],'sectionOrder':['Cleaning','Transformation','Validation']}
        response=self.client.post('/api/v1/retailers',json=self.body)
        self.assertEqual(response.status_code,200,response.data)
        self.rid=response.get_json()['retailer']['id']

    def upload(self,content=b'sku,sales\n item ,invalid\n',filename='sample.csv'):
        return self.client.post(f'/api/v1/retailers/{self.rid}/sample',data={'file':(io.BytesIO(content),filename)})

    def test_required_sender_and_optional_retailer_email(self):
        for email in ['', 'invalid']:
            self.assertEqual(self.client.post('/api/v1/retailers',json={**self.body,'key':'OTHER','senderEmail':email}).status_code,400)
        self.assertEqual(self.client.post('/api/v1/retailers',json={**self.body,'key':'OTHER','retailerEmail':'invalid'}).status_code,400)

    def test_unique_retailer_and_store_keys(self):
        self.assertEqual(self.client.post('/api/v1/retailers',json={**self.body,'key':self.body['key'].lower()}).status_code,409)
        changed={**self.body,'stores':[{'key':'S1','name':'One'},{'key':'s1','name':'Two'}]}
        self.assertEqual(self.client.put(f'/api/v1/retailers/{self.rid}',json=changed).status_code,400)

    def test_configuration_sample_and_custom_rule_persist(self):
        pipeline=[rule('trim','Cleaning'),rule('required','Validation')]
        data={**self.body,'pipeline':pipeline}
        self.assertEqual(self.client.put(f'/api/v1/retailers/{self.rid}',json=data).status_code,200)
        retailers=self.client.get('/api/v1/retailers').get_json()['retailers']
        restored=next(r for r in retailers if r['id']==self.rid)
        self.assertEqual(restored['pipeline'],pipeline)
        self.assertEqual(restored['stores'],self.body['stores'])
        self.assertEqual(self.upload().status_code,200)
        self.assertEqual(self.client.get(f'/api/v1/retailers/{self.rid}/sample').get_json()['sample']['totalRows'],1)
        created=self.client.post('/api/v1/rule-definitions',json={'name':'Retailer SKU trim','category':'Cleaning','operation':'trim','defaults':{'field':'sku'}})
        self.assertEqual(created.status_code,200)
        self.assertIn(created.get_json()['rule'],self.client.get('/api/v1/rule-definitions').get_json()['rules'])

    def test_sample_limit_is_strict_and_failed_upload_preserves_sample(self):
        self.assertEqual(self.upload().status_code,200)
        self.assertEqual(self.upload(b'x'*1_000_000).status_code,413)
        self.assertEqual(self.client.get(f'/api/v1/retailers/{self.rid}/sample').get_json()['sample']['filename'],'sample.csv')
        self.assertEqual(self.upload(b'not a spreadsheet','wrong.xlsx').status_code,400)

    def test_sequence_changes_results_and_step_preview(self):
        records=[{'sku':' a '}]
        trim=rule('trim','Cleaning');replace=rule('replace','Cleaning',find=' a ',replacement='b')
        first,steps,_,_=apply_pipeline(records,[replace,trim])
        second,_,_,_=apply_pipeline(records,[trim,replace])
        self.assertEqual(first[0]['sku'],'b');self.assertEqual(second[0]['sku'],'a')
        self.assertEqual(steps[0]['before'][0]['sku'],' a ')
        self.assertEqual(steps[0]['after'][0]['sku'],'b')
        self.assertEqual(records[0]['sku'],' a ')

    def test_section_order_changes_detections(self):
        records=[{'sku':'  SKU-A  '}]
        cleaning=rule('trim','Cleaning');validation=rule('pattern','Validation',pattern='SKU-*')
        _,_,issues,_=apply_pipeline(records,[validation,cleaning]);self.assertEqual(len(issues),1)
        _,_,issues,_=apply_pipeline(records,[cleaning,validation]);self.assertEqual(issues,[])

    def test_rename_numeric_and_invalid_values(self):
        records=[{'sales':'12'},{'sales':'bad'}]
        out,_,issues,_=apply_pipeline(records,[rule('rename','Transformation','sales',target='revenue'),rule('numeric','Transformation','revenue')])
        self.assertEqual(out,[{'revenue':12},{'revenue':'bad'}]);self.assertEqual(issues[0]['row'],2)
        with self.assertRaises(ValueError):apply_pipeline([{'sales':1,'revenue':2}],[rule('rename','Transformation','sales',target='revenue')])

    def test_full_sample_applied_with_25_row_previews_and_full_export(self):
        content=('sku,sales\n'+'\n'.join(f' item{i} ,bad' for i in range(31))).encode()
        self.assertEqual(self.upload(content).status_code,200)
        pipeline=[rule('trim','Cleaning'),rule('numeric','Transformation','sales')]
        response=self.client.post(f'/api/v1/retailers/{self.rid}/preview',json={'pipeline':pipeline})
        self.assertEqual(response.status_code,200,response.data)
        data=response.get_json();self.assertEqual(data['totalRows'],31);self.assertEqual(len(data['final']),25);self.assertEqual(len(data['issues']),31)
        self.assertEqual(len(data['steps'][0]['before']),25);self.assertEqual(len(data['sections']),2)
        export=self.client.post(f'/api/v1/retailers/{self.rid}/example.csv',json={'pipeline':pipeline})
        self.assertEqual(export.status_code,200);self.assertIn(b'item30',export.data)
        self.assertNotIn(b' item30 ',export.data)

    def test_unknown_field_and_invalid_rules_are_errors(self):
        self.upload()
        for pipeline in [[rule('trim','Cleaning','unknown')],[rule('range','Validation','sales',min='10',max='1')],[rule('date','Transformation','sku')]]:
            self.assertEqual(self.client.post(f'/api/v1/retailers/{self.rid}/preview',json={'pipeline':pipeline}).status_code,400)
        self.assertEqual(self.client.post('/api/v1/ai-assist',json={'consent':True}).status_code,403)

if __name__=='__main__':unittest.main()
