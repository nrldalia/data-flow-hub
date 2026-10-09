import unittest,json
import test_batch_jobs as fixtures
from database import get_db_connection

class ClientDeleteTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs

    def test_bulk_delete_removes_configs_samples_preserves_history_and_store_registry(self):
        second=self.client.post('/api/v1/retailers',json={**self.config,'key':self.config['key']+'_2','stores':[{'key':'S1','name':'Store'}]}).get_json()['retailer']
        aid=self.start();self.finish(aid)
        with get_db_connection() as db:
            db.execute('INSERT INTO retailer_samples VALUES(?,?,?,?)',(self.retailer,'sample.csv','[]',10))
            registry=db.execute('SELECT COUNT(*) FROM store_code_registry').fetchone()[0]
        response=self.client.post('/api/v1/retailers/delete',json={'ids':[self.retailer,second['id']]})
        self.assertEqual(response.status_code,200,response.data)
        with get_db_connection() as db:
            self.assertIsNone(db.execute('SELECT id FROM retailer_configs WHERE id=?',(self.retailer,)).fetchone())
            self.assertIsNone(db.execute('SELECT retailer_id FROM retailer_samples WHERE retailer_id=?',(self.retailer,)).fetchone())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM store_code_registry').fetchone()[0],registry)
        self.assertEqual(self.client.get('/api/v1/batches/'+aid+'/audit').status_code,200)

    def test_active_job_blocks_entire_bulk_delete(self):
        second=self.client.post('/api/v1/retailers',json={**self.config,'key':self.config['key']+'_2'}).get_json()['retailer']
        self.start()
        self.assertEqual(self.client.post('/api/v1/retailers/delete',json={'ids':[self.retailer,second['id']]}).status_code,409)
        ids={r['id'] for r in self.client.get('/api/v1/retailers').get_json()['retailers']}
        self.assertTrue({self.retailer,second['id']}.issubset(ids))

    def test_invalid_or_unknown_selection_is_atomic(self):
        for body in [None,{'ids':[]},{'ids':'bad'},{'ids':[None]},{'ids':[self.retailer,'missing']}]:
            response=self.client.post('/api/v1/retailers/delete',json=body)
            self.assertIn(response.status_code,[400,404])
            self.assertIn(self.retailer,{r['id'] for r in self.client.get('/api/v1/retailers').get_json()['retailers']})
