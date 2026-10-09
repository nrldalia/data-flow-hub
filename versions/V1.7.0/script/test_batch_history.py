import unittest,sqlite3,json
from batch_history import migrate_run_history
import test_batch_jobs as fixtures
from database import get_db_connection

class BaselineHistoryTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs

    def test_previous_week_uses_latest_successful_run_excluding_failure(self):
        first=self.start('2026-W40',b'sku\na\n');self.finish(first)
        source=b'sku\n longer-value \n'
        second=self.start('2026-W40',source);self.finish(second)
        with get_db_connection() as db:
            db.execute('UPDATE batch_jobs SET end_time=? WHERE id=?',('2026-10-01T00:00:00+00:00',first))
            db.execute('UPDATE batch_jobs SET end_time=? WHERE id=?',('2026-10-02T00:00:00+00:00',second))
        cancelled=self.start('2026-W40',b'sku\n rejected \n');self.client.post('/api/v1/batches/'+cancelled+'/cancel')
        current=self.start('2026-W41',b'sku\na\n');self.finish(current)
        m=next(j for j in self.jobs() if j['id']==current)['metrics']
        self.assertEqual(m['previousFileSizeBytes'],len(source));self.assertEqual(len(self.jobs()),4)

class HistoryMigrationTests(unittest.TestCase):
    def test_migration_preserves_jobs_and_recovers_nested_cancellation_once(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE batch_jobs(id TEXT PRIMARY KEY,retailer_id TEXT,retailer_name TEXT,period TEXT,start_time TEXT,end_time TEXT,status TEXT,filename TEXT,source BLOB,pipeline TEXT,output TEXT,audit TEXT,error_codes TEXT,last_attempt TEXT,metrics TEXT,UNIQUE(retailer_id,period))')
        db.execute('CREATE TABLE batch_attempts(id TEXT PRIMARY KEY,retailer_id TEXT,period TEXT,UNIQUE(retailer_id,period))')
        outcome={'id':'FAILED','start_time':'2026-10-09','errorCodes':['RULE_RETRY_LIMIT']}
        db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('OLD','R','Retailer','2026-W41','2026-10-08','2026-10-08','Completed','old.csv',b'sku\na','[]','[]','[]','[]',json.dumps(outcome),'{}'));db.commit()
        migrate_run_history(db);db.commit()
        rows=db.execute('SELECT * FROM batch_jobs ORDER BY id').fetchall()
        self.assertEqual(len(rows),2);self.assertEqual(rows[1]['source'],b'sku\na')
        self.assertEqual(rows[0]['status'],'Cancelled Job');self.assertIsNone(rows[0]['end_time']);self.assertIsNone(rows[0]['audit'])
        db.execute('INSERT INTO batch_attempts VALUES(?,?,?)',('A','R','2026-W41'));db.execute('INSERT INTO batch_attempts VALUES(?,?,?)',('B','R','2026-W41'));db.commit()
        migrate_run_history(db);db.commit();self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_jobs').fetchone()[0],2)
        db.close()
