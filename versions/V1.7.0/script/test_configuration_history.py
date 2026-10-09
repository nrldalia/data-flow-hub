import unittest
import test_batch_jobs as fixtures
from database import get_db_connection

class ConfigurationHistoryTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    def history(self):return self.client.get('/api/v1/retailers/'+self.retailer+'/configuration-history').get_json()['versions']

    def test_changes_version_unchanged_save_does_not_and_failed_save_is_atomic(self):
        self.assertEqual([v['version'] for v in self.history()],[1])
        self.client.put('/api/v1/retailers/'+self.retailer,json=self.config)
        self.assertEqual(len(self.history()),1)
        changed={**self.config,'pipeline':[{**self.rule,'description':'Trim imported SKU padding'}]}
        response=self.client.put('/api/v1/retailers/'+self.retailer,json=changed)
        self.assertEqual(response.get_json()['configurationVersion']['version'],2)
        self.assertNotIn('description',self.history()[1]['configuration']['pipeline'][0])
        self.assertEqual(self.client.put('/api/v1/retailers/'+self.retailer,json={**changed,'senderEmail':'bad'}).status_code,400)
        self.assertEqual(len(self.history()),2)

    def test_run_pins_original_version_despite_later_changes_and_delete(self):
        original=self.start()
        changed={**self.config,'pipeline':[{**self.rule,'operation':'uppercase','description':'Uppercase SKU'}]}
        self.client.put('/api/v1/retailers/'+self.retailer,json=changed)
        self.finish(original)
        data=self.client.get('/api/v1/batches/'+original+'/configuration').get_json()
        self.assertEqual(data['version']['version'],1);self.assertEqual(data['configuration']['pipeline'][0]['operation'],'trim')
        new=self.client.post('/api/v1/batches/'+original+'/reprocess').get_json()['attemptId'];self.finish(new)
        self.assertEqual(self.client.get('/api/v1/batches/'+new+'/configuration').get_json()['version']['version'],2)
        self.assertEqual(self.client.post('/api/v1/retailers/delete',json={'ids':[self.retailer]}).status_code,200)
        self.assertEqual(self.client.get('/api/v1/batches/'+original+'/configuration').status_code,200)

    def test_store_approval_versions_setup_without_changing_run_snapshot(self):
        aid=self.start(source=b'sku,Store ID\na,NEW\n');self.finish(aid)
        self.assertEqual(self.client.post('/api/v1/batches/'+aid+'/approve').status_code,200)
        self.assertEqual(len(self.history()),2);self.assertEqual(self.history()[0]['reason'],'New stores approved')
        snap=self.client.get('/api/v1/batches/'+aid+'/configuration').get_json()
        self.assertEqual(snap['configuration']['stores'],[])

    def test_legacy_run_does_not_claim_configuration_provenance(self):
        aid=self.start();self.finish(aid)
        with get_db_connection() as db:db.execute('UPDATE batch_jobs SET metrics=? WHERE id=?',('{}',aid))
        self.assertEqual(self.client.get('/api/v1/batches/'+aid+'/configuration').status_code,404)
