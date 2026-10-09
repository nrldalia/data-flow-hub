"""Append-only, complete retailer configuration snapshots."""
import hashlib,json,uuid
from datetime import datetime,timezone

def version_summary(row):
    return {key:row[key] for key in ['id','version','saved_at','reason','sha256']}

def record_version(db,rid,config,reason):
    payload=json.dumps(config,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    digest=hashlib.sha256(payload.encode('utf-8')).hexdigest()
    previous=db.execute('SELECT * FROM retailer_configuration_versions WHERE retailer_id=? ORDER BY version DESC LIMIT 1',(rid,)).fetchone()
    if previous and previous['sha256']==digest:return previous
    identity='CFG-'+uuid.uuid4().hex
    db.execute('INSERT INTO retailer_configuration_versions VALUES(?,?,?,?,?,?,?)',(identity,rid,1 if not previous else previous['version']+1,datetime.now(timezone.utc).isoformat(),reason,digest,payload))
    return db.execute('SELECT * FROM retailer_configuration_versions WHERE id=?',(identity,)).fetchone()

def initialize_history(db):
    db.execute('CREATE TABLE IF NOT EXISTS retailer_configuration_versions(id TEXT PRIMARY KEY,retailer_id TEXT NOT NULL,version INTEGER NOT NULL,saved_at TEXT NOT NULL,reason TEXT NOT NULL,sha256 TEXT NOT NULL,payload TEXT NOT NULL,UNIQUE(retailer_id,version))')
    for row in db.execute('SELECT id,payload FROM retailer_configs').fetchall():
        record_version(db,row['id'],json.loads(row['payload']),'Existing setup baseline; earlier changes unavailable')
