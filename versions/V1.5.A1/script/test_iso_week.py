import unittest
import test_batch_jobs as fixtures

class IsoWeekTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs

    def completed(self,week):
        aid=self.start(period=week);self.finish(aid);return aid

    def test_reprocess_different_week_keeps_original_and_updates_baseline(self):
        original=self.completed('2026-W41')
        response=self.client.post('/api/v1/batches/'+original+'/reprocess',json={'period':'2026-W42'})
        self.assertEqual(response.status_code,202,response.data)
        aid=response.get_json()['attemptId'];self.finish(aid)
        jobs=self.jobs();self.assertEqual({j['period'] for j in jobs},{'2026-W41','2026-W42'})
        newest=next(j for j in jobs if j['id']==aid)
        self.assertEqual(newest['metrics']['previousPeriod'],'2026-W41')
        self.assertEqual(newest['metrics']['fileSizeDeviationBytes'],0)

    def test_default_reprocess_preserves_same_week_replacement(self):
        original=self.completed('2026-W41')
        response=self.client.post('/api/v1/batches/'+original+'/reprocess')
        aid=response.get_json()['attemptId'];self.finish(aid)
        self.assertEqual(len(self.jobs()),1);self.assertEqual(self.jobs()[0]['period'],'2026-W41')
        self.assertNotEqual(self.jobs()[0]['id'],original)

    def test_invalid_week_and_shape_rejected_without_starting(self):
        original=self.completed('2026-W41')
        for body in [{'period':'2026-W54'},{'period':'2025-W53'},{'period':'2026-W1'},{'period':None},[]]:
            response=self.client.post('/api/v1/batches/'+original+'/reprocess',json=body)
            self.assertEqual(response.status_code,400,(body,response.data))
        self.assertEqual(len(self.jobs()),1)
        self.assertEqual(self.client.get('/api/v1/batches').get_json()['active'],[])

    def test_target_week_conflict_and_cancel_preserves_both_records(self):
        original=self.completed('2026-W41');target=self.completed('2026-W42')
        response=self.client.post('/api/v1/batches/'+original+'/reprocess',json={'period':'2026-W42'})
        aid=response.get_json()['attemptId']
        self.assertEqual(self.client.post('/api/v1/batches/'+original+'/reprocess',json={'period':'2026-W42'}).status_code,409)
        self.client.post('/api/v1/batches/'+aid+'/cancel')
        self.assertEqual({j['id'] for j in self.jobs()},{original,target})
