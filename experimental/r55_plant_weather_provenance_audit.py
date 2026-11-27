#!/usr/bin/env python3
"""Inspect separate MORE-EU channels without redistributing any source rows.
No independent-meter or calibrated irradiance assertion; only source identity,
calendar alignment, empirical redundancy, and matched-channel availability.
"""
from pathlib import Path
import argparse,csv,hashlib,io,json,math,statistics
from collections import Counter,defaultdict
import numpy as np
import r55_pmedc_paired_bounds_original_source as original
BLOB_ARRAY=original.BLOB

def load(path):
    data=Path(path).read_bytes();blob=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
    rd=csv.reader(io.StringIO(data.decode('utf-8-sig')))
    header=next(rd)
    items={};dups=0;broken=0;missing=0;rawcount=0;count=Counter();first_fmt=None
    for row in rd:
        rawcount+=1
        if len(row)!=len(header):broken+=1;continue
        key=row[0].strip()
        first_fmt=first_fmt or (key[:36])
        if key in items:dups+=1
        nums=[]
        for z in row[1:]:
            if not z.strip():nums.append(None);missing+=1
            else:
                try:v=float(z);nums.append(v if math.isfinite(v) else None)
                except ValueError:nums.append(None);missing+=1
        items[key]=nums
        count['rows']+=1
    return {'name':Path(path).name,'size_bytes':len(data),'blob_sha1':blob,'header':header,'rows':rawcount,'unique_keys':len(items),'duplicate_keys':dups,'broken_rows':broken,'missing_non_numeric_entries':missing,'sample_timestamp_format':first_fmt},items

def run(array,plant,weather,out):
    A,a=load(array);P,p=load(plant);W,w=load(weather)
    assert A['blob_sha1']==BLOB_ARRAY and A['rows']==280512
    # Duplicate or different source clocks should be exposed, not forced into alignment.
    same_plant=set(a)&set(p);same_weather=set(a)&set(w)
    aid=set(a)
    act=[];py=[];trainx=[];trainy=[];testx=[];testy=[]
    # Qualified original 79 complete months; use exact source-clock timestamp keys.
    complete_months=[m['month'] for m in original.read_months(array)]
    train_months=set(complete_months[:55]);test_months=set(complete_months[55:])
    calendar=lambda x: f"20{x.split()[0].split('/')[-1]}-{int(x.split()[0].split('/')[1]):02d}" if len(x.split())==2 and '/' in x else 'NA'
    full_w=0;positive_w=0;positive_p=0
    for ts in same_plant:
        x=a[ts];y=p[ts]
        if len(x)!=14 or len(y)!=1 or y[0] is None or any(v is None for v in x):continue
        cm=calendar(ts)
        if cm in train_months:trainx.append(x);trainy.append(y[0])
        elif cm in test_months:testx.append(x);testy.append(y[0])
        if len(act)<200000:act.append(x);py.append(y[0])
    report={'state':'RESEARCH_ONLY_NOT_PUBLISHABLE_METROLOGICAL_INDEPENDENCE',
         'files':[A,P,W],
         'joins':{'array_plant_exact_timestamps':len(same_plant),'array_weather_exact_timestamps':len(same_weather),'array_plant_weather_triple_timestamps':len(a.keys()&p.keys()&w.keys()),'array_unique_not_in_plant':len(a.keys()-p.keys()),'array_unique_not_in_weather':len(a.keys()-w.keys())},
         'qualified_months':len(complete_months),'matched_rows_development':len(trainx),'matched_rows_test':len(testx)}
    if len(trainx)>=300 and len(testx)>=300:
        X=np.asarray(trainx,dtype=float);Y=np.asarray(trainy,dtype=float)
        Xt=np.asarray(testx,dtype=float);Yt=np.asarray(testy,dtype=float)
        # These are purely diagnostic numerical relations: do not infer independent wiring.
        weights=np.linalg.lstsq(X,Y,rcond=None)[0]
        def metrics(y,pred):
            err=pred-y
            return {'n':len(y),'mae':float(np.mean(np.abs(err))),'rmse':float(np.sqrt(np.mean(err**2))),
                 'max_absolute_error':float(np.max(np.abs(err))),'source_output_mean':float(np.mean(y)),
                 'source_output_max':float(np.max(y)),'corr':float(np.corrcoef(y,pred)[0,1]) if np.std(y)>0 and np.std(pred)>0 else None}
        report['empirical_plant_array_relationship']={
           'equal_mean_plant_dev':metrics(Y,X.mean(axis=1)),
           'equal_mean_plant_test':metrics(Yt,Xt.mean(axis=1)),
           'nonnegative_constraint_on_weights':False,
           'unconstrained_least_squares_coefficients_training_only':[float(z) for z in weights],
           'sum_of_fitted_coefficients':float(sum(weights)),
           'fit_plant_dev':metrics(Y,X@weights),'fit_plant_test':metrics(Yt,Xt@weights),
           'plant_independent_meter_status':'UNKNOWN: separate published channel does not show independent instrumentation, wiring, time base, or persistence during array logger outage'}
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    (out/'MORE_EU_PLANT_WEATHER_SOURCE_ROLE_GATE.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('SOURCE_CHANNEL_AUDIT_PASS',json.dumps({'file_headers':[A['header'],P['header'],W['header']],
          'joins':report['joins'],'months':len(complete_months),'matched_development':len(trainx),'matched_test':len(testx),
          'plant_relation':report.get('empirical_plant_array_relationship')},sort_keys=True),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--array',required=True);ap.add_argument('--plant',required=True);ap.add_argument('--weather',required=True);ap.add_argument('--out',default='R55_CHANNEL_PROVENANCE')
 x=ap.parse_args();run(x.array,x.plant,x.weather,x.out)
