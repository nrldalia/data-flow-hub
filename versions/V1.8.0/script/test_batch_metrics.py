import unittest
import test_batch_jobs as fixtures
from batch_metrics import input_metrics, received_metrics, previous_period
from database import get_db_connection
import app

class MetricsTests(unittest.TestCase):
    def test_previous_week_crosses_iso_year(self):
        self.assertEqual(previous_period('2026-W01'),'2025-W52')

    def test_reconcile_unique_ids_active_missing_and_inactive_known(self):
        m=input_metrics(b'abc','2026-W41',[{'key':'A','name':'A'},{'key':'B','name':'B'},{'key':'I','name':'I','status':'Inactive'}],{'source':b'ab'})
        received_metrics(m,[{'Store ID':'a'},{'Store ID':'a'},{'Store ID':'N','Store Name':'New'},{'Store ID':'I'},{'Store ID':''}])
        self.assertEqual(m['rowsReceived'],5);self.assertEqual(m['storesReceived'],3)
        self.assertEqual(m['newStores'],[{'key':'N','name':'New'}]);self.assertEqual(m['missingStores'],[{'key':'B','name':'B'}])
        self.assertEqual(m['storeTotalIncludingNew'],4);self.assertEqual(m['rowsWithoutStoreId'],1)
        self.assertEqual(m['fileSizeDeviationBytes'],1);self.assertEqual(m['fileSizeDeviationPercent'],50)

    def test_unavailable_mapping_and_baseline_are_not_zero(self):
        m=input_metrics(b'a','2026-W01',[],None)
        received_metrics(m,[{'sku':'X'}])
        self.assertIsNone(m['storesReceived']);self.assertIsNone(m['newStores']);self.assertIsNone(m['fileSizeDeviationBytes'])

    def test_empty_file_mapping_and_zero_baseline(self):
        m=input_metrics(b'','2026-W41',[{'key':'A','name':'A'}],{'source':b''},'Store ID')
        received_metrics(m,[])
        self.assertEqual(m['storesReceived'],0);self.assertEqual(len(m['missingStores']),1)
        self.assertEqual(m['fileSizeDeviationBytes'],0);self.assertIsNone(m['fileSizeDeviationPercent'])

    def test_decrease_is_signed(self):
        m=input_metrics(b'abc','2026-W41',[],{'source':b'abcdef'})
        self.assertEqual(m['fileSizeDirection'],'Decrease')
        self.assertEqual(m['fileSizeDeviationBytes'],-3);self.assertEqual(m['fileSizeDeviationPercent'],-50)

class BatchMetricApiTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs

    def test_metrics_snapshot_and_add_only_after_approval(self):
        self.config['stores']=[{'key':'OLD','name':'Old store'}]
        self.client.put('/api/v1/retailers/'+self.retailer,json=self.config)
        prior=self.start('2026-W40',b'sku,Store ID,Store Name\na,OLD,Old store\n');self.finish(prior)
        source=b'sku,Store ID,Store Name\n a ,NEW,New store\n b ,NEW,New store\n'
        aid=self.start(source=source);self.finish(aid)
        data=self.client.get('/api/v1/batches/'+aid+'/audit').get_json();m=data['job']['metrics']
        self.assertEqual(m['rowsReceived'],2);self.assertEqual(m['rowsAfterCleaning'],2)
        self.assertEqual(m['storesReceived'],1);self.assertEqual(m['newStores'][0]['key'],'NEW')
        self.assertEqual(m['missingStores'][0]['key'],'OLD');self.assertEqual(m['fileSizeBytes'],len(source))
        self.assertIsNotNone(m['fileSizeDeviationPercent'])
        def stores():return next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer)['stores']
        self.assertEqual(len(stores()),1)
        self.assertEqual(self.client.post('/api/v1/batches/'+aid+'/approve').status_code,200)
        self.assertEqual(len(stores()),1)
        self.assertEqual(self.client.post('/api/v1/batches/'+aid+'/stores/review',json={'stores':[{'key':'NEW','name':'New store','address':'Test Road','status':'Active','exception':False}]}).status_code,200)
        self.assertEqual(len(stores()),2);self.assertRegex(stores()[1]['suiteCode'],r'^MY6[0-9]{7}$')
        self.assertEqual(self.client.post('/api/v1/batches/'+aid+'/approve').status_code,409)
        self.assertEqual(len(stores()),2)

    def test_cancelled_replacement_preserves_prior_metrics_and_stores(self):
        first=self.start(source=b'sku,Store ID\na,NEW\n');self.finish(first)
        old=self.jobs()[0]['metrics']
        second=self.start(source=b'sku,Store ID\nb,OTHER\n')
        self.client.post('/api/v1/batches/'+second+'/cancel')
        self.assertEqual(next(j for j in self.jobs() if j['id']==first)['metrics'],old);self.assertEqual(len(self.jobs()),2)
        retailer=next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer)
        self.assertEqual(retailer['stores'],[])

    def test_cleaning_count_is_distinct_from_received_and_final_count(self):
        self.config['pipeline']=[self.rule,{**self.rule,'id':'transform','category':'Transformation','operation':'rename','target':'code'}]
        self.assertEqual(self.client.put('/api/v1/retailers/'+self.retailer,json=self.config).status_code,200)
        def executor(records,rule):
            output=records[:1] if rule['category']=='Cleaning' else records*3
            return {'output':output,'issueCount':0,'changedCells':0}
        app.app.config['BATCH_TEST_EXECUTOR']=executor
        aid=self.start(source=b'sku,Store ID\na,A\nb,B\n');self.finish(aid)
        m=self.jobs()[0]['metrics']
        self.assertEqual(m['rowsReceived'],2);self.assertEqual(m['rowsAfterCleaning'],1)
        with get_db_connection() as db:
            import json
            self.assertEqual(len(json.loads(db.execute('SELECT output FROM batch_jobs WHERE id=?',(aid,)).fetchone()[0])),3)
