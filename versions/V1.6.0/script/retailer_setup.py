"""Retailer configuration and deterministic, ordered sample rule previews."""
import copy
import io
import json
import math
import re
import sqlite3
import uuid
from pathlib import Path
from fnmatch import fnmatchcase
from datetime import datetime
from flask import request, jsonify, send_file
from database import get_db_connection

CATEGORIES = ['Cleaning', 'Transformation', 'Validation']
OPERATIONS = {
    'Cleaning': {'trim': 'Trim whitespace', 'uppercase': 'Uppercase text', 'lowercase': 'Lowercase text', 'replace': 'Replace text'},
    'Transformation': {'numeric': 'Convert to number', 'date': 'Standardise date', 'rename': 'Rename column'},
    'Validation': {'required': 'Required value', 'range': 'Numeric range', 'pattern': 'Text pattern', 'unique': 'Unique values'},
}
BUILTINS = [{'id': op, 'name': label, 'category': category, 'operation': op, 'defaults': {}}
            for category, ops in OPERATIONS.items() for op, label in ops.items()]
EXAMPLES={'trim':'Example: Remove spaces around store names.','uppercase':'Example: Convert store names to uppercase.','lowercase':'Example: Convert store names to lowercase.',
          'replace':'Example: Replace St. with Street.','numeric':'Example: Convert sales text into numbers.','date':'Example: Convert 08/10/2026 to 2026-10-08.',
          'rename':'Example: Rename sales to revenue.','required':'Example: Require a store ID.','range':'Example: Accept sales between zero and 1000.',
          'pattern':'Example: Require store IDs matching SKU-*.','unique':'Example: Reject repeated store IDs.'}
for definition in BUILTINS:definition['example']=EXAMPLES[definition['operation']]
REFERENCE_RULES=json.loads(Path(__file__).with_name('rule_references.json').read_text(encoding='utf-8'))
EMAIL = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
SAMPLE_LIMIT = 1_000_000

CONDITION_OPERATORS = {'eq','ne','gt','ge','lt','le','between','contains','starts','ends','blank','notblank'}

def validate_condition(condition):
    if condition is None: return
    if not isinstance(condition, dict) or condition.get('operator') not in CONDITION_OPERATORS:
        raise ValueError('Choose a supported condition type.')
    if not isinstance(condition.get('field'),str) or not condition['field'].strip() or len(condition['field'])>500:
        raise ValueError('Choose a condition field.')
    op=condition['operator']
    for key in ['value','value2']:
        if key in condition and (not isinstance(condition[key],str) or len(condition[key])>500):
            raise ValueError('Condition values must be text of at most 500 characters.')
    if op not in {'blank','notblank'} and not condition.get('value','').strip():
        raise ValueError('Enter a condition value.')
    if op in {'gt','ge','lt','le','between'}:
        try:
            value=float(condition['value'])
            if not math.isfinite(value): raise ValueError()
            if op=='between':
                upper=float(condition.get('value2',''))
                if not math.isfinite(upper) or upper<value: raise ValueError()
        except (ValueError,TypeError): raise ValueError('Enter valid numeric condition bounds in ascending order.')

def condition_matches(row, condition):
    if condition is None: return True
    old=row.get(condition['field']); op=condition['operator']; value=condition.get('value','')
    blank=old is None or str(old).strip()==''
    if op=='blank': return blank
    if op=='notblank': return not blank
    text='' if old is None else str(old)
    if op=='contains': return value.casefold() in text.casefold()
    if op=='starts': return text.casefold().startswith(value.casefold())
    if op=='ends': return text.casefold().endswith(value.casefold())
    if op in {'eq','ne'}:
        try: equal=float(text)==float(value)
        except (ValueError,TypeError): equal=text.casefold()==value.casefold()
        return equal if op=='eq' else not equal
    try: number=float(old); bound=float(value)
    except (ValueError,TypeError): return False
    if not math.isfinite(number): return False
    if op=='gt': return number>bound
    if op=='ge': return number>=bound
    if op=='lt': return number<bound
    if op=='le': return number<=bound
    return bound<=number<=float(condition['value2'])

def validate_pipeline(pipeline, allow_references=False):
    if not isinstance(pipeline, list) or len(pipeline) > 100:
        raise ValueError('Use a list of at most 100 rules.')
    ids = set()
    for sequence,rule in enumerate(pipeline,1):
        if not isinstance(rule, dict):
            raise ValueError('Invalid rule configuration.')
        category, op = rule.get('category'), rule.get('operation')
        if category not in OPERATIONS or (op not in OPERATIONS[category] and op!='reference'):
            raise ValueError('Choose a supported rule operation and category.')
        if op=='reference':
            if not isinstance(rule.get('name'),str) or not rule['name'].strip():raise ValueError('Choose a named rule reference.')
            if not allow_references:raise ValueError(f'Rule {sequence}: "{rule["name"]}" is reference-only; its execution engine is not available.')
        if not isinstance(rule.get('id'), str) or not rule['id'] or rule['id'] in ids:
            raise ValueError('Each rule must have a unique ID.')
        ids.add(rule['id'])
        if op!='reference' and (not isinstance(rule.get('field'), str) or not rule['field'].strip()):
            raise ValueError('Select a field for every rule.')
        validate_condition(rule.get('condition'))
        for key in ['name', 'field', 'target', 'find', 'replacement', 'dateFormat', 'pattern', 'description']:
            if key in rule and (not isinstance(rule[key], str) or len(rule[key]) > 500):
                raise ValueError('Rule text must be at most 500 characters.')
        if op == 'rename' and not rule.get('target', '').strip():
            raise ValueError('A renamed column needs a target name.')
        if op == 'replace' and not rule.get('find'):
            raise ValueError('Enter text to find for a replacement rule.')
        if op == 'date' and not rule.get('dateFormat'):
            raise ValueError('Enter the source date format.')
        if op == 'range':
            try:
                low, high = float(rule.get('min', '')), float(rule.get('max', ''))
                if not math.isfinite(low) or not math.isfinite(high) or low > high:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError('Enter valid minimum and maximum values.')
        if op == 'pattern':
            # A small, safe glob-style pattern prevents regex denial of service.
            pattern = rule.get('pattern', '')
            if not pattern or len(pattern) > 100:
                raise ValueError('Enter a text pattern of at most 100 characters. Use * and ? as wildcards.')

def apply_pipeline(records, pipeline):
    validate_pipeline(pipeline)
    output = copy.deepcopy(records)
    steps, all_issues, trace = [], [], []
    for seq, rule in enumerate(pipeline, 1):
        field, op = rule['field'], rule['operation']
        columns = {key for row in output for key in row}
        if field not in columns:
            raise ValueError(f'Rule {seq}: field "{field}" does not exist at this step.')
        condition=rule.get('condition')
        if condition and condition['field'] not in columns:
            raise ValueError(f'Rule {seq}: condition field does not exist at this step.')
        if op == 'rename' and rule['target'] != field and rule['target'] in columns:
            raise ValueError(f'Rule {seq}: target column already exists.')
        before = copy.deepcopy(output[:25])
        issues, changes, seen = [], 0, {}
        for row_no, row in enumerate(output, 1):
            if not condition_matches(row, condition): continue
            old = row.get(field)
            value = old
            issue = None
            if op == 'trim' and isinstance(old, str): value = old.strip()
            elif op == 'uppercase' and isinstance(old, str): value = old.upper()
            elif op == 'lowercase' and isinstance(old, str): value = old.lower()
            elif op == 'replace' and isinstance(old, str): value = old.replace(rule['find'], rule.get('replacement', ''))
            elif op == 'numeric' and old not in (None, ''):
                try:
                    number = float(old)
                    if not math.isfinite(number): raise ValueError()
                    value = int(number) if number.is_integer() else number
                except (ValueError, TypeError, OverflowError): issue = 'Invalid number; original retained'
            elif op == 'date' and old not in (None, ''):
                try: value = datetime.strptime(str(old), rule['dateFormat']).strftime('%Y-%m-%d')
                except (ValueError, TypeError): issue = 'Invalid date; original retained'
            elif op == 'required' and (old is None or str(old).strip() == ''): issue = 'Missing required value'
            elif op == 'range':
                try:
                    number = float(old)
                    if not math.isfinite(number) or not float(rule['min']) <= number <= float(rule['max']): issue = 'Outside allowed numeric range'
                except (TypeError, ValueError): issue = 'Value is not numeric'
            elif op == 'pattern':
                pattern = rule['pattern'].replace('[', '[[]')
                if old is None or not fnmatchcase(str(old), pattern): issue = 'Does not match text pattern'
            elif op == 'unique':
                key = json.dumps(old, sort_keys=True)
                seen.setdefault(key, []).append(row_no)
            if op == 'rename':
                row[rule['target']] = row.pop(field, None)
                if rule['target'] != field:
                    changes += 1
                    trace.append({'step':seq, 'row':row_no, 'field':field, 'before':field, 'after':rule['target'], 'action':rule.get('name', 'Rename column')})
            elif value != old or type(value) is not type(old):
                changes += 1
                trace.append({'step':seq, 'row':row_no, 'field':field, 'before':old, 'after':value, 'action':rule.get('name', op)})
                row[field] = value
            if issue: issues.append({'step':seq, 'row':row_no, 'field':field, 'issue':issue})
        if op == 'unique':
            for row_numbers in seen.values():
                if len(row_numbers) > 1:
                    issues.extend({'step':seq,'row':n,'field':field,'issue':'Duplicate value; retained'} for n in row_numbers)
        all_issues.extend(issues)
        steps.append({'id':rule['id'],'sequence':seq,'category':rule['category'],'name':rule.get('name',op),'before':before,'after':copy.deepcopy(output[:25]),'issues':issues,'changedCells':changes,'totalRows':len(output)})
    return output, steps, all_issues, trace

def validate_retailer(body):
    if not isinstance(body, dict): raise ValueError('Invalid retailer configuration.')
    for key, label in [('name','Retailer name'), ('key','Retailer key'), ('senderEmail','Sender email')]:
        if not isinstance(body.get(key), str) or not body[key].strip(): raise ValueError(label + ' is required.')
        body[key] = body[key].strip()
    if len(body['name']) > 120 or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', body['key']):
        raise ValueError('Retailer key must contain 1–64 letters, numbers, underscores or hyphens.')
    if not EMAIL.fullmatch(body['senderEmail']): raise ValueError('Enter a valid sender email.')
    body['retailerEmail'] = str(body.get('retailerEmail','')).strip()
    if body['retailerEmail'] and not EMAIL.fullmatch(body['retailerEmail']): raise ValueError('Enter a valid retailer email or leave it blank.')
    if body.get('serviceType') not in ['SM','HM','MM']: raise ValueError('Choose SM, HM or MM.')
    stores = body.get('stores',[])
    if not isinstance(stores,list) or len(stores) > 1000: raise ValueError('Use a store table of at most 1,000 rows.')
    keys=set()
    for store in stores:
        if not isinstance(store,dict) or not isinstance(store.get('key'),str) or not isinstance(store.get('name'),str): raise ValueError('Every store needs a key and name.')
        store['key']=store['key'].strip();store['name']=store['name'].strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',store['key']) or not store['name'] or len(store['name']) > 120: raise ValueError('Every store needs a valid key and name.')
        if store['key'].lower() in keys: raise ValueError('Store keys must be unique within a retailer.')
        keys.add(store['key'].lower())
        if store.get('status','Active') not in ['Active','Inactive']: raise ValueError('Choose Active or Inactive for every store.')
        if not isinstance(store.get('exception',False),bool): raise ValueError('Store exception status must be Yes or No.')
        if not isinstance(store.get('address',''),str) or len(store.get('address',''))>2000: raise ValueError('Store address must be text of at most 2,000 characters.')
        if 'id' in store and (not isinstance(store['id'],str) or not store['id']): raise ValueError('Invalid store identity.')
    validate_pipeline(body.get('pipeline',[]),allow_references=True)
    order=body.get('sectionOrder',CATEGORIES)
    if not isinstance(order,list) or sorted(order)!=sorted(CATEGORIES): raise ValueError('Include each rule section exactly once.')
    return {k:body.get(k, [] if k in ['stores','pipeline'] else '') for k in ['name','key','serviceType','senderEmail','retailerEmail','stores','pipeline']} | {'sectionOrder':order}

def next_store_code(db, identity, legacy_code=None):
    saved=db.execute('SELECT code FROM store_code_registry WHERE store_id=?',(identity,)).fetchone()
    if saved: return saved['code']
    number=db.execute('SELECT last_value FROM store_code_sequence WHERE id=1').fetchone()['last_value']+1
    if number>9_999_999: raise ValueError('The seven-digit SUITE storecode sequence is exhausted.')
    code=f'MY6{number:07d}'
    db.execute('UPDATE store_code_sequence SET last_value=? WHERE id=1',(number,))
    db.execute('INSERT INTO store_code_registry VALUES(?,?,?,?)',(identity,code,number,legacy_code))
    return code

def initialize_store_sequence(db):
    db.execute('CREATE TABLE IF NOT EXISTS store_code_sequence(id INTEGER PRIMARY KEY CHECK(id=1),last_value INTEGER NOT NULL CHECK(last_value BETWEEN 0 AND 9999999))')
    db.execute('CREATE TABLE IF NOT EXISTS store_code_registry(store_id TEXT PRIMARY KEY,code TEXT UNIQUE NOT NULL,sequence INTEGER UNIQUE NOT NULL,legacy_code TEXT)')
    db.execute('BEGIN IMMEDIATE')
    db.execute('INSERT OR IGNORE INTO store_code_sequence VALUES(1,0)')
    rows=db.execute('SELECT id,payload FROM retailer_configs ORDER BY rowid').fetchall()
    payloads=[(row['id'],json.loads(row['payload'])) for row in rows]
    # Register existing MY6 codes first, so imported higher numbers are never reused.
    for _,payload in payloads:
        for store in payload.get('stores',[]):
            if not store.get('id'):store['id']='STORE-'+uuid.uuid4().hex
            code=store.get('suiteCode') or ''
            if re.fullmatch(r'MY6[0-9]{7}',code) and int(code[3:])>0:
                registered=db.execute('SELECT code FROM store_code_registry WHERE store_id=?',(store['id'],)).fetchone()
                if registered and registered['code']!=code: raise ValueError('A store has conflicting registered storecodes.')
                if not registered:db.execute('INSERT INTO store_code_registry VALUES(?,?,?,NULL)',(store['id'],code,int(code[3:])))
    highest=db.execute('SELECT COALESCE(MAX(sequence),0) AS highest FROM store_code_registry').fetchone()['highest']
    db.execute('UPDATE store_code_sequence SET last_value=MAX(last_value,?) WHERE id=1',(highest,))
    for rid,payload in payloads:
        for store in payload.get('stores',[]):
            store['suiteCode']=next_store_code(db,store['id'],store.get('suiteCode') or None)
        db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(payload),rid))

def assign_store_codes(stores, previous, db):
    by_id={s['id']:s for s in previous if s.get('id')}
    by_key={s['key'].lower():s for s in previous}
    normalized=[];used=set()
    for store in stores:
        old=by_id.get(store.get('id')) if store.get('id') else by_key.get(store['key'].lower())
        if store.get('id') and old is None: raise ValueError('Store identity does not belong to this retailer.')
        identity=(old or {}).get('id') or 'STORE-'+uuid.uuid4().hex
        if identity in used: raise ValueError('Each store identity must appear only once.')
        used.add(identity)
        code=next_store_code(db,identity,(old or {}).get('suiteCode'))
        normalized.append({'id':identity,'key':store['key'],'name':store['name'],'suiteCode':code,
                           'status':store.get('status',(old or {}).get('status','Active')),
                           'exception':store.get('exception',(old or {}).get('exception',False)),
                           'address':store.get('address',(old or {}).get('address','')).strip()})
    return normalized

def register_retailer_routes(app, parse_upload, error):
    with get_db_connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS retailer_configs(id TEXT PRIMARY KEY, retailer_key TEXT UNIQUE COLLATE NOCASE, payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS retailer_samples(retailer_id TEXT PRIMARY KEY, filename TEXT, records TEXT, byte_size INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS rule_definitions(id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        initialize_store_sequence(db)

    @app.route('/api/v1/retailers', methods=['GET','POST'])
    def retailers():
        if request.method == 'GET':
            with get_db_connection() as db:
                rows=[json.loads(row['payload']) | {'id':row['id']} for row in db.execute('SELECT * FROM retailer_configs ORDER BY retailer_key')]
            return jsonify(success=True,retailers=rows)
        return save_retailer(None)

    @app.route('/api/v1/retailers/<rid>', methods=['PUT'])
    def save_retailer(rid):
        try:
            body=validate_retailer(request.get_json(silent=True))
            with get_db_connection() as db:
                db.execute('BEGIN IMMEDIATE')
                if rid:
                    previous=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(rid,)).fetchone()
                    if not previous: return error('Retailer not found.',404)
                    body['stores']=assign_store_codes(body['stores'],json.loads(previous['payload']).get('stores',[]),db)
                    db.execute('UPDATE retailer_configs SET retailer_key=?,payload=? WHERE id=?',(body['key'],json.dumps(body),rid))
                else:
                    body['stores']=assign_store_codes(body['stores'],[],db)
                    rid='RET-'+uuid.uuid4().hex[:12]
                    db.execute('INSERT INTO retailer_configs VALUES(?,?,?)',(rid,body['key'],json.dumps(body)))
            return jsonify(success=True,retailer=body | {'id':rid})
        except (ValueError,TypeError) as exc: return error(str(exc))
        except sqlite3.IntegrityError: return error('Retailer key already exists.',409)

    @app.route('/api/v1/rule-definitions', methods=['GET','POST'])
    def rule_definitions():
        if request.method == 'GET':
            with get_db_connection() as db: custom=[json.loads(r['payload']) for r in db.execute('SELECT payload FROM rule_definitions')]
            names={(r['category'],r['name']) for r in BUILTINS}
            references=[r for r in REFERENCE_RULES if (r['category'],r['name']) not in names]
            return jsonify(success=True,rules=BUILTINS+references+custom)
        body=request.get_json(silent=True)
        if not isinstance(body,dict): return error('Invalid rule definition.')
        category,op,name=body.get('category'),body.get('operation'),body.get('name')
        if category not in OPERATIONS or op not in OPERATIONS[category] or not isinstance(name,str) or not name.strip() or len(name)>120:
            return error('Choose a rule category, operation and name.')
        defaults=body.get('defaults',{})
        if not isinstance(defaults,dict): return error('Invalid rule defaults.')
        try:
            validate_condition(defaults.get('condition'))
            for key in ['description','field','target','find','replacement','dateFormat','pattern']:
                if key in defaults and (not isinstance(defaults[key],str) or len(defaults[key])>500): raise ValueError('Rule text must be at most 500 characters.')
        except ValueError as exc: return error(str(exc))
        definition={'id':'RULE-'+uuid.uuid4().hex[:12],'category':category,'operation':op,'name':name.strip(),'defaults':{k:v for k,v in defaults.items() if k in ['field','target','find','replacement','min','max','dateFormat','pattern','description'] and isinstance(v,str)}}
        if defaults.get('condition'): definition['defaults']['condition']=defaults['condition']
        with get_db_connection() as db: db.execute('INSERT INTO rule_definitions VALUES(?,?)',(definition['id'],json.dumps(definition)))
        return jsonify(success=True,rule=definition)

    @app.route('/api/v1/retailers/<rid>/sample', methods=['GET','POST'])
    def retailer_sample(rid):
        with get_db_connection() as db:
            if not db.execute('SELECT id FROM retailer_configs WHERE id=?',(rid,)).fetchone(): return error('Save the retailer before uploading a sample.',404)
            if request.method=='GET':
                sample=db.execute('SELECT * FROM retailer_samples WHERE retailer_id=?',(rid,)).fetchone()
                if not sample: return jsonify(success=True,sample=None)
                records=json.loads(sample['records'])
                return jsonify(success=True,sample={'filename':sample['filename'],'totalRows':len(records),'rows':records[:25],'columns':list(dict.fromkeys(k for r in records for k in r)),'byteSize':sample['byte_size']})
        file=request.files.get('file')
        if not file or not file.filename: return error('Upload a CSV, Excel or JSON sample.')
        content=file.stream.read(SAMPLE_LIMIT)
        if len(content)>=SAMPLE_LIMIT: return error('Sample must be smaller than 1 MB (1,000,000 bytes).',413)
        file.stream.close()
        file.stream=io.BytesIO(content)
        try:
            records,kind,_=parse_upload(file)
            if len(records)>10000 or len({k for r in records for k in r})>100: return error('Sample supports at most 10,000 rows and 100 columns.')
            with get_db_connection() as db:
                db.execute('INSERT OR REPLACE INTO retailer_samples VALUES(?,?,?,?)',(rid,file.filename,json.dumps(records),len(content)))
            return jsonify(success=True,sample={'filename':file.filename,'totalRows':len(records),'rows':records[:25],'columns':list(dict.fromkeys(k for r in records for k in r)),'byteSize':len(content)})
        except (ValueError,TypeError,UnicodeDecodeError) as exc: return error(str(exc))
        except Exception: app.logger.exception('Sample parsing failed');return error('Could not parse the sample file.')

    def preview_data(rid, pipeline):
        with get_db_connection() as db: sample=db.execute('SELECT * FROM retailer_samples WHERE retailer_id=?',(rid,)).fetchone()
        if not sample: raise ValueError('Upload a sample first.')
        records=json.loads(sample['records'])
        output,steps,issues,trace=apply_pipeline(records,pipeline)
        sections=[]
        for step in steps:
            if not sections or sections[-1]['category']!=step['category']:
                sections.append({'category':step['category'],'before':step['before'],'after':step['after'],'issues':list(step['issues'])})
            else:
                sections[-1]['after']=step['after'];sections[-1]['issues'].extend(step['issues'])
        return output,{'success':True,'original':records[:25],'final':output[:25],'steps':steps,'sections':sections,'issues':issues,'totalRows':len(output),'changedCells':len(trace),'issueRows':len({i['row'] for i in issues})}

    @app.route('/api/v1/retailers/<rid>/preview',methods=['POST'])
    def preview(rid):
        try:
            body=request.get_json(silent=True)
            if not isinstance(body,dict): raise ValueError('Invalid preview request.')
            _,result=preview_data(rid,body.get('pipeline',[]))
            return jsonify(result)
        except (ValueError,TypeError) as exc: return error(str(exc))

    @app.route('/api/v1/retailers/<rid>/example.csv',methods=['POST'])
    def example_export(rid):
        import pandas as pd
        try:
            body=request.get_json(silent=True)
            if not isinstance(body,dict): raise ValueError('Invalid export request.')
            output,_=preview_data(rid,body.get('pipeline',[]))
            data=pd.DataFrame(output).to_csv(index=False).encode('utf-8-sig')
            return send_file(io.BytesIO(data),mimetype='text/csv',as_attachment=True,download_name='retailer_final_example.csv')
        except (ValueError,TypeError) as exc: return error(str(exc))
