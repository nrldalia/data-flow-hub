"""Remove old retailer/week uniqueness without losing job history."""
import json

def migrate_run_history(db):
    db.execute('BEGIN IMMEDIATE')
    for table in ['batch_jobs','batch_attempts']:
        indexes=db.execute(f'PRAGMA index_list({table})').fetchall()
        unique=any(r['unique'] and [c['name'] for c in db.execute(f"PRAGMA index_info('{r['name']}')")] == ['retailer_id','period'] for r in indexes)
        if not unique:continue
        sql=db.execute('SELECT sql FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone()[0]
        import re
        sql=re.sub(r',\s*UNIQUE\s*\(retailer_id\s*,\s*period\)', '', sql, flags=re.I)
        sql=sql.replace(table,table+'_history_migration',1)
        db.execute(sql)
        db.execute(f'INSERT INTO {table}_history_migration SELECT * FROM {table}')
        db.execute(f'DROP TABLE {table}')
        db.execute(f'ALTER TABLE {table}_history_migration RENAME TO {table}')
    db.execute('CREATE INDEX IF NOT EXISTS batch_job_period_history ON batch_jobs(retailer_id,period,end_time)')
    # Earlier releases retained only the most recent cancelled attempt as nested metadata.
    for job in db.execute('SELECT * FROM batch_jobs WHERE last_attempt IS NOT NULL').fetchall():
        last=json.loads(job['last_attempt'])
        if last.get('id') and not db.execute('SELECT id FROM batch_jobs WHERE id=?',(last['id'],)).fetchone():
            db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (last['id'],job['retailer_id'],job['retailer_name'],job['period'],last['start_time'],None,
                        'Cancelled Job',job['filename'],b'',job['pipeline'],None,None,json.dumps(last.get('errorCodes',[])),None,
                        json.dumps({'historyRecoveryNote':'Recovered cancellation metadata. Original input and receipt metrics were not retained.'})))
        db.execute('UPDATE batch_jobs SET last_attempt=NULL WHERE id=?',(job['id'],))
