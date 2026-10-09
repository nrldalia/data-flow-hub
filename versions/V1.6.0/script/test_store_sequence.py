import os,tempfile,unittest,threading,json,sqlite3
from pathlib import Path
test_dir=tempfile.TemporaryDirectory()
os.environ['DATAFLOW_DB']=str(Path(test_dir.name)/'sequence.db')
import app
from database import get_db_connection
from retailer_setup import initialize_store_sequence

class StoreSequenceTests(unittest.TestCase):
    def setUp(self):self.client=app.app.test_client()
    def create(self,name,stores):
        body=dict(name=name,key='SEQ_'+os.urandom(6).hex(),senderEmail='qa@example.com',serviceType='SM',pipeline=[],stores=stores)
        result=self.client.post('/api/v1/retailers',json=body)
        self.assertEqual(result.status_code,200,result.data)
        return result.get_json()['retailer']
    def last(self):
        with get_db_connection() as db:return db.execute('SELECT last_value FROM store_code_sequence WHERE id=1').fetchone()[0]

    def test_global_sequence_interleaves_retailers(self):
        start=self.last()
        b=self.create('Retailer B',[dict(key='B1',name='B first')])
        a=self.create('Retailer A',[dict(key='A1',name='A first')])
        response=self.client.put('/api/v1/retailers/'+b['id'],json={**b,'stores':b['stores']+[dict(key='B2',name='B second')]})
        self.assertEqual(response.status_code,200,response.data)
        codes=[b['stores'][0]['suiteCode'],a['stores'][0]['suiteCode'],response.get_json()['retailer']['stores'][1]['suiteCode']]
        self.assertEqual(codes,[f'MY6{n:07d}' for n in range(start+1,start+4)])

    def test_edits_do_not_consume_numbers_and_removal_never_reuses(self):
        saved=self.create('Edit QA',[dict(key='ONE',name='One')]);code=saved['stores'][0]['suiteCode'];number=self.last()
        changed={**saved,'stores':[{**saved['stores'][0],'key':'RENAMED','status':'Inactive'}]}
        result=self.client.put('/api/v1/retailers/'+saved['id'],json=changed)
        self.assertEqual(result.get_json()['retailer']['stores'][0]['suiteCode'],code)
        self.assertEqual(self.last(),number)
        self.assertEqual(self.client.put('/api/v1/retailers/'+saved['id'],json={**saved,'stores':[]}).status_code,200)
        newer=self.create('After removal',[dict(key='NEW',name='New')])
        self.assertEqual(newer['stores'][0]['suiteCode'],f'MY6{number+1:07d}')

    def test_failed_save_rolls_back_number(self):
        saved=self.create('Conflict',[]);start=self.last()
        duplicate={**saved,'stores':[dict(key='X',name='X')]}
        self.assertEqual(self.client.post('/api/v1/retailers',json=duplicate).status_code,409)
        self.assertEqual(self.last(),start)

    def test_concurrent_allocations_are_unique_and_consecutive(self):
        start=self.last();results=[];lock=threading.Lock();barrier=threading.Barrier(5)
        def worker(i):
            client=app.app.test_client();barrier.wait()
            result=client.post('/api/v1/retailers',json=dict(name=f'Concurrent {i}',key='CON_'+os.urandom(6).hex(),senderEmail='qa@example.com',serviceType='SM',pipeline=[],stores=[dict(key='S1',name='One')]))
            with lock:results.append((result.status_code,result.get_json()))
        threads=[threading.Thread(target=worker,args=(i,)) for i in range(5)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(15)
        self.assertFalse(any(t.is_alive() for t in threads));self.assertEqual(len(results),5)
        self.assertTrue(all(code==200 for code,_ in results),results)
        numbers=sorted(int(data['retailer']['stores'][0]['suiteCode'][3:]) for _,data in results)
        self.assertEqual(numbers,list(range(start+1,start+6)))

    def migration_db(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE retailer_configs(id TEXT PRIMARY KEY,payload TEXT)')
        return db

    def test_migration_retains_old_codes_and_preserves_existing_my6(self):
        db=self.migration_db()
        payload=dict(stores=[dict(key='OLD',name='Old',suiteCode='SUITE-OLD'),dict(id='EXISTING',key='VALID',name='Valid',suiteCode='MY60000020')])
        db.execute('INSERT INTO retailer_configs VALUES(?,?)',('R1',json.dumps(payload)));db.commit()
        initialize_store_sequence(db);db.commit()
        saved=json.loads(db.execute('SELECT payload FROM retailer_configs').fetchone()[0]);codes=[s['suiteCode'] for s in saved['stores']]
        self.assertEqual(codes,['MY60000021','MY60000020'])
        self.assertEqual(db.execute('SELECT legacy_code FROM store_code_registry WHERE code=?',('MY60000021',)).fetchone()[0],'SUITE-OLD')
        initialize_store_sequence(db);db.commit()
        self.assertEqual(json.loads(db.execute('SELECT payload FROM retailer_configs').fetchone()[0]),saved)
        db.close()

    def test_sequence_limit_cannot_wrap(self):
        from retailer_setup import next_store_code
        db=self.migration_db();initialize_store_sequence(db);db.commit()
        db.execute('UPDATE store_code_sequence SET last_value=9999999 WHERE id=1')
        with self.assertRaisesRegex(ValueError,'exhausted'):next_store_code(db,'NEW')
        self.assertEqual(db.execute('SELECT COUNT(*) FROM store_code_registry').fetchone()[0],0)
        db.close()

    def test_sequence_persists_when_initialized_again(self):
        self.create('Before restart',[dict(key='ONE',name='One')]);number=self.last()
        with get_db_connection() as db:initialize_store_sequence(db)
        newer=self.create('After restart',[dict(key='TWO',name='Two')])
        self.assertEqual(newer['stores'][0]['suiteCode'],f'MY6{number+1:07d}')

    def test_migration_rejects_duplicate_existing_codes(self):
        db=self.migration_db()
        stores=[dict(id='S1',key='ONE',suiteCode='MY60000001'),dict(id='S2',key='TWO',suiteCode='MY60000001')]
        db.execute('INSERT INTO retailer_configs VALUES(?,?)',('R1',json.dumps(dict(stores=stores))));db.commit()
        with self.assertRaises(sqlite3.IntegrityError):initialize_store_sequence(db)
        db.rollback();db.close()

if __name__=='__main__':unittest.main()
