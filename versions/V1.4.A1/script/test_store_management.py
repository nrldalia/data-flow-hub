import os,tempfile,unittest
from pathlib import Path
test_dir=tempfile.TemporaryDirectory()
os.environ['DATAFLOW_DB']=str(Path(test_dir.name)/'stores.db')
import app
from database import get_db_connection

class StoreManagementTests(unittest.TestCase):
    def setUp(self):
        self.client=app.app.test_client()
        body=dict(name='Store QA',key='STOREQA_'+os.urandom(4).hex(),senderEmail='qa@example.com',serviceType='SM',pipeline=[],stores=[dict(key='S1',name='Main',address='1 Example Road',status='Active',exception=False)])
        self.saved=self.client.post('/api/v1/retailers',json=body).get_json()['retailer']
        self.rid=self.saved['id']
    def put(self,body):return self.client.put('/api/v1/retailers/'+self.rid,json=body)

    def test_generated_code_and_metadata_persist(self):
        store=self.saved['stores'][0]
        self.assertRegex(store['suiteCode'],r'^SUITE-[A-F0-9]{32}$')
        self.assertEqual(store['status'],'Active');self.assertFalse(store['exception'])
        reread=next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.rid)
        self.assertEqual(reread['stores'],self.saved['stores'])

    def test_code_stable_when_store_and_retailer_key_change(self):
        old=self.saved['stores'][0]
        changed={**self.saved,'key':self.saved['key']+'_NEW','stores':[{**old,'key':'S2','name':'Renamed','status':'Inactive','exception':True,'address':'2 Example Road','suiteCode':'FORGED'}]}
        result=self.put(changed);self.assertEqual(result.status_code,200,result.data)
        store=result.get_json()['retailer']['stores'][0]
        self.assertEqual(store['suiteCode'],old['suiteCode']);self.assertEqual(store['id'],old['id'])
        self.assertEqual(store['key'],'S2');self.assertEqual(store['address'],'2 Example Road')
        self.assertEqual(store['status'],'Inactive');self.assertTrue(store['exception'])
        self.assertEqual(result.get_json()['retailer']['key'],changed['key'])

    def test_multiple_stores_get_distinct_codes(self):
        result=self.put({**self.saved,'stores':self.saved['stores']+[dict(key='S2',name='Branch',suiteCode=self.saved['stores'][0]['suiteCode'])]})
        stores=result.get_json()['retailer']['stores']
        self.assertNotEqual(stores[0]['suiteCode'],stores[1]['suiteCode'])
        self.assertEqual(stores[1]['status'],'Active');self.assertFalse(stores[1]['exception'])

    def test_bad_status_exception_address_and_identity_rejected(self):
        for patch in [dict(status='unknown'),dict(exception='Yes'),dict(address='x'*2001),dict(id='UNKNOWN')]:
            self.assertEqual(self.put({**self.saved,'stores':[{**self.saved['stores'][0],**patch}]}).status_code,400)
        self.assertEqual(self.put({**self.saved,'stores':[self.saved['stores'][0],{**self.saved['stores'][0],'key':'S2'}]}).status_code,400)

    def test_shared_key_conflict_is_atomic(self):
        other={**self.saved,'key':'OTHER_'+os.urandom(4).hex(),'stores':[]}
        self.assertEqual(self.client.post('/api/v1/retailers',json=other).status_code,200)
        result=self.put({**self.saved,'key':other['key'],'stores':[{**self.saved['stores'][0],'status':'Inactive'}]})
        self.assertEqual(result.status_code,409)
        reread=next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.rid)
        self.assertEqual(reread,self.saved)

    def test_legacy_stores_receive_codes_once(self):
        import json
        legacy={**self.saved,'stores':[dict(key='OLD',name='Legacy Store')]}
        with get_db_connection() as db:db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(legacy),self.rid))
        result=self.put(legacy);self.assertEqual(result.status_code,200)
        first=result.get_json()['retailer'];second=self.put(first).get_json()['retailer']
        self.assertEqual(first['stores'],second['stores'])

if __name__=='__main__':unittest.main()
