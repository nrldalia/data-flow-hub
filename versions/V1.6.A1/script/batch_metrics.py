"""Immutable batch input metrics and store reconciliation summaries."""
import re
from datetime import datetime, timedelta

def previous_period(period):
    year, week = period.split('-W')
    day = datetime.fromisocalendar(int(year), int(week), 1) - timedelta(days=7)
    iso = day.isocalendar()
    return f'{iso.year:04d}-W{iso.week:02d}'

def input_metrics(source, period, stores, previous, store_field=''):
    size = len(source)
    baseline = len(previous['source']) if previous else None
    delta = size - baseline if baseline is not None else None
    return dict(fileSizeBytes=size, previousPeriod=previous_period(period), previousFileSizeBytes=baseline,
                fileSizeDeviationBytes=delta, fileSizeDeviationPercent=round(delta / baseline * 100, 2) if baseline else None,
                fileSizeDirection='Unavailable' if delta is None else 'Increase' if delta > 0 else 'Decrease' if delta < 0 else 'Unchanged',
                expectedStores=[{'key':s['key'], 'name':s['name']} for s in stores if s.get('status', 'Active') == 'Active'],
                registeredStoreIds=[s['key'] for s in stores], storeIdField=store_field,
                rowsReceived=None, rowsAfterCleaning=None, storesReceived=None, newStores=None, missingStores=None)

def received_metrics(metrics, records):
    metrics['rowsReceived'] = len(records)
    columns = list(dict.fromkeys(k for row in records for k in row))
    field = metrics['storeIdField']
    if not field:
        aliases = {'storeid', 'retailerstoreid', 'storecode', 'retailerstorecode', 'storekey'}
        candidates = [c for c in columns if re.sub(r'[^a-z0-9]', '', c.lower()) in aliases]
        if len(candidates) == 1: field = candidates[0]
    if not field or (records and field not in columns):
        metrics['storeComparisonNote'] = 'Store ID column unavailable or ambiguous. Specify it when uploading.'
        return
    metrics['storeIdField'] = field
    names = [c for c in columns if re.sub(r'[^a-z0-9]', '', c.lower()) in {'storename', 'retailerstorename'}]
    received = {}
    blank = 0
    for row in records:
        value = row.get(field)
        key = '' if value is None else str(value).strip()
        if not key:
            blank += 1
            continue
        normalized = key.casefold()
        if normalized not in received:
            name = str(row.get(names[0]) or key).strip() if names else key
            received[normalized] = {'key':key, 'name':name}
    registered = {key.casefold() for key in metrics['registeredStoreIds']}
    metrics['storesReceived'] = len(received)
    metrics['newStores'] = [s for key, s in received.items() if key not in registered]
    metrics['missingStores'] = [s for s in metrics['expectedStores'] if s['key'].casefold() not in received]
    metrics['rowsWithoutStoreId'] = blank
    metrics['storeTotalIncludingNew'] = len(registered) + len(metrics['newStores'])
    metrics['storeComparisonNote'] = 'Unique received IDs; missing stores are active stores absent from the input.'

def public_metrics(metrics):
    return {k:v for k,v in metrics.items() if k not in {'expectedStores', 'registeredStoreIds'}}
