"""Independent, transactional review and approval of received new stores."""
import json
from datetime import datetime,timezone
from flask import jsonify,request
from database import get_db_connection
from retailer_setup import validate_retailer,assign_store_codes
from configuration_history import record_version,version_summary

def register_store_review_routes(app,error):
    @app.route('/api/v1/batches/<jid>/stores/review',methods=['GET','POST'])
    def review_stores(jid):
        with get_db_connection() as db:
            if request.method=='POST':db.execute('BEGIN IMMEDIATE')
            job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            if job['status'] not in ['Completed','Completed with Interruption','Approved Job']:return error('Only completed jobs support New Store review.',409)
            retailer=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(job['retailer_id'],)).fetchone()
            if not retailer:return error('Retailer setup no longer exists.',404)
            config=json.loads(retailer['payload']);existing=config.get('stores',[])
            known={s['key'].casefold():s for s in existing}
            metrics=json.loads(job['metrics'] or '{}');reviews=metrics.get('storeReviews',{})
            candidates={s['key'].casefold():s for s in metrics.get('newStores') or []}
            if request.method=='GET':
                rows=[]
                for key,source in candidates.items():
                    approved=reviews.get(key)
                    current=known.get(key)
                    decision=(approved or {}).get('decision') or ('Already registered' if current else 'Pending review')
                    rows.append({'key':source['key'],'name':source['name'],'address':'','status':'Active','exception':False,**(approved or current or {}),'decision':decision})
                return jsonify(success=True,jobId=jid,retailerName=job['retailer_name'],period=job['period'],stores=rows)
            body=request.get_json(silent=True);selected=body.get('stores') if isinstance(body,dict) else None
            if not isinstance(selected,list) or not selected or len(selected)>1000:return error('Select one or more new stores to approve.')
            additions=[];decisions=[];seen=set()
            for store in selected:
                if not isinstance(store,dict) or not isinstance(store.get('key'),str):return error('Invalid store selection.')
                key=store['key'].casefold()
                if key in seen or key not in candidates:return error('Select distinct stores flagged by this job.')
                seen.add(key)
                if key in reviews:return error('A selected store has already been reviewed. Refresh the review page.',409)
                if key in known:
                    decisions.append((key,{**known[key],'decision':'Already registered'}));continue
                normalized={'key':candidates[key]['key'],'name':store.get('name'),'address':store.get('address',''),'status':store.get('status','Active'),'exception':store.get('exception',False)}
                additions.append(normalized);decisions.append((key,{**normalized,'decision':'Approved'}))
            if additions:
                try:
                    updated=validate_retailer({**config,'stores':existing+additions})
                    updated['stores']=assign_store_codes(updated['stores'],existing,db)
                except (ValueError,TypeError) as exc:return error('Review store details: '+str(exc))
                db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(updated),job['retailer_id']))
                version=version_summary(record_version(db,job['retailer_id'],updated,'New stores approved'))
                known={s['key'].casefold():s for s in updated['stores']}
            else:version=None
            stamp=datetime.now(timezone.utc).isoformat()
            for key,decision in decisions:
                reviews[key]={**decision,**known[key],'decision':decision['decision'],'approvedAt':stamp,'configurationVersion':version}
            metrics['storeReviews']=reviews
            metrics['newStoresApprovedCount']=sum(r['decision']=='Approved' for r in reviews.values())
            entries=json.loads(job['audit'] or '[]');entries.append({'sequence':None,'ruleName':'New Store approval','category':'Action','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Successful','errorCode':None,'message':f'{len(additions)} new stores added; {len(decisions)-len(additions)} already registered.'})
            db.execute('UPDATE batch_jobs SET metrics=?,audit=? WHERE id=?',(json.dumps(metrics),json.dumps(entries),jid))
        return jsonify(success=True,addedCount=len(additions),reviewedCount=len(decisions),configurationVersion=version)
