import os
import tempfile
import unittest
from pathlib import Path

test_dir=tempfile.TemporaryDirectory()
os.environ['DATAFLOW_DB']=str(Path(test_dir.name)/'rules.db')
import app
from retailer_setup import apply_pipeline, validate_pipeline

def rule(op='trim',category='Cleaning',field='sku',**extra):
    return dict(id=op,name=op,operation=op,category=category,field=field,**extra)

class RulesConfigureTests(unittest.TestCase):
    def test_condition_only_changes_matching_rows(self):
        records=[{'sku':' a ','sales':'15'},{'sku':' b ','sales':'5'},{'sku':' c ','sales':'bad'}]
        output,steps,issues,_=apply_pipeline(records,[rule(condition={'field':'sales','operator':'gt','value':'10'})])
        self.assertEqual([r['sku'] for r in output],['a',' b ',' c '])
        self.assertEqual(steps[0]['changedCells'],1);self.assertEqual(issues,[])

    def test_condition_validation_and_duplicates(self):
        records=[{'sku':'X','active':'yes'},{'sku':'X','active':'no'},{'sku':'','active':'no'}]
        output,_,issues,_=apply_pipeline(records,[rule('unique','Validation',condition={'field':'active','operator':'eq','value':'YES'})])
        self.assertEqual(issues,[]);self.assertEqual(output,records)

    def test_blank_and_text_conditions(self):
        records=[{'sku':' item ','kind':'Hello'},{'sku':' other ','kind':None}]
        for op,value in [('contains','ell'),('starts','he'),('ends','LO'),('notblank','')]:
            output,_,_,_=apply_pipeline(records,[rule(condition={'field':'kind','operator':op,'value':value})])
            self.assertEqual(output[0]['sku'],'item');self.assertEqual(output[1]['sku'],' other ')
        output,_,_,_=apply_pipeline(records,[rule(condition={'field':'kind','operator':'blank'})])
        self.assertEqual(output[1]['sku'],'other');self.assertEqual(output[0]['sku'],' item ')

    def test_between_is_inclusive_and_comparisons(self):
        records=[{'sku':' a ','sales':10},{'sku':' b ','sales':20},{'sku':' c ','sales':21}]
        output,_,_,_=apply_pipeline(records,[rule(condition={'field':'sales','operator':'between','value':'10','value2':'20'})])
        self.assertEqual([r['sku'] for r in output],['a','b',' c '])
        for op,expected in [('ge',2),('lt',1),('le',2),('ne',2)]:
            _,steps,_,_=apply_pipeline(records,[rule(condition={'field':'sales','operator':op,'value':'20'})])
            self.assertEqual(steps[0]['changedCells'],expected)

    def test_invalid_conditions_rejected(self):
        for condition in [{'field':'sales','operator':'between','value':'20','value2':'10'}, {'field':'sales','operator':'gt','value':'nan'},{'field':'','operator':'blank'},{'field':'sku','operator':'script','value':'x'}]:
            with self.assertRaises(ValueError):validate_pipeline([rule(condition=condition)])
        with self.assertRaises(ValueError):apply_pipeline([{'sku':'x'}],[rule(condition={'field':'missing','operator':'blank'})])

    def test_global_cross_component_sequence(self):
        rows=[{'sku':' a '}]
        rename=rule('rename','Transformation',target='code')
        trim=rule(field='code')
        output,steps,_,_=apply_pipeline(rows,[rename,trim])
        self.assertEqual(output,[{'code':'a'}]);self.assertEqual([s['category'] for s in steps],['Transformation','Cleaning'])
        with self.assertRaises(ValueError):apply_pipeline(rows,[trim,rename])

    def test_api_persists_description_condition_and_sequence(self):
        client=app.app.test_client()
        pipeline=[rule('rename','Transformation',target='code',description='Use the standard item identifier.'),rule(field='code',condition={'field':'sales','operator':'gt','value':'10'})]
        payload=dict(name='Condition QA',key='COND_QA',senderEmail='qa@example.com',serviceType='SM',pipeline=pipeline)
        result=client.post('/api/v1/retailers',json=payload)
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(result.get_json()['retailer']['pipeline'],pipeline)
        saved=client.get('/api/v1/retailers').get_json()['retailers']
        self.assertEqual(next(r for r in saved if r['key']=='COND_QA')['pipeline'],pipeline)
        bad={**payload,'key':'BAD','pipeline':[rule(description='x'*501)]}
        self.assertEqual(client.post('/api/v1/retailers',json=bad).status_code,400)

if __name__=='__main__':unittest.main()
