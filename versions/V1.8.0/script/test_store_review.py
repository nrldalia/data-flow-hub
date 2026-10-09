import unittest
import test_batch_jobs as fixtures

class StoreReviewTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs

    def batch(self):
        aid=self.start(source=b'sku,Store ID,Store Name\na,N1,Store One\nb,N2,Store Two\n');self.finish(aid);return aid
    def stores(self):return next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer)['stores']
    def approve(self,aid,stores):return self.client.post('/api/v1/batches/'+aid+'/stores/review',json={'stores':stores})

    def test_partial_review_job_approval_independence_and_metadata(self):
        aid=self.batch()
        response=self.approve(aid,[{'key':'N1','name':'Reviewed name','address':'12 Test Street','status':'Inactive','exception':True}])
        self.assertEqual(response.status_code,200,response.data)
        s=self.stores()[0];self.assertEqual(s['name'],'Reviewed name');self.assertEqual(s['address'],'12 Test Street');self.assertEqual(s['status'],'Inactive');self.assertTrue(s['exception'])
        self.assertRegex(s['suiteCode'],r'^MY6[0-9]{7}$');self.assertEqual(self.jobs()[0]['status'],'Completed')
        reviewed=self.client.get('/api/v1/batches/'+aid+'/stores/review').get_json()['stores']
        self.assertEqual([r['decision'] for r in reviewed],['Approved','Pending review'])
        self.assertEqual(self.approve(aid,[{'key':'N1','name':'Overwrite'}]).status_code,409)
        self.client.post('/api/v1/batches/'+aid+'/approve')
        self.assertEqual(len(self.stores()),1)
        self.assertEqual(self.approve(aid,[{'key':'N2','name':'Second name','status':'Active','address':''}]).status_code,200)
        self.assertEqual(self.jobs()[0]['status'],'Approved Job');self.assertEqual(len(self.stores()),2)
        snapshot=self.client.get('/api/v1/batches/'+aid+'/configuration').get_json()
        self.assertEqual(snapshot['configuration']['stores'],[])
        entries=self.client.get('/api/v1/batches/'+aid+'/audit').get_json()['entries']
        self.assertEqual(sum(e['ruleName']=='New Store approval' for e in entries),2)

    def test_invalid_selection_and_details_are_atomic(self):
        aid=self.batch()
        for stores in [[{'key':'UNKNOWN','name':'Unknown'}],[{'key':'N1','name':'Good'},{'key':'N2','name':''}],[{'key':'N1','name':'A'},{'key':'N1','name':'B'}]]:
            self.assertEqual(self.approve(aid,stores).status_code,400)
            self.assertEqual(self.stores(),[])
        history=self.client.get('/api/v1/retailers/'+self.retailer+'/configuration-history').get_json()['versions']
        self.assertEqual(len(history),1)

    def test_other_run_cannot_duplicate_or_overwrite_registered_store(self):
        first=self.batch();second=self.batch()
        self.approve(first,[{'key':'N1','name':'Official name','address':'Official address'}])
        rows=self.client.get('/api/v1/batches/'+second+'/stores/review').get_json()['stores']
        self.assertEqual(rows[0]['decision'],'Already registered')
        response=self.approve(second,[{'key':'N1','name':'Unwanted overwrite'}])
        self.assertEqual(response.get_json()['addedCount'],0)
        self.assertEqual(self.stores()[0]['name'],'Official name');self.assertEqual(len(self.stores()),1)

    def test_cancelled_job_cannot_add_stores(self):
        aid=self.batch();self.client.post('/api/v1/batches/'+aid+'/cancel')
        self.assertEqual(self.approve(aid,[{'key':'N1','name':'One'}]).status_code,409)
        self.assertEqual(self.stores(),[])
