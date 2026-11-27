#!/usr/bin/env python3
"""RESEARCH ONLY: use surviving whole-site and weather channels for missing array-output certificates.

All source files are pinned. Array-day records are counterfactually omitted;
plant/weather recordings stay available only as a **conditional hypothetical**.
Training envelopes are descriptive, not future-valid hard physical limits.
No original data rows leave the GitHub runner.
"""
import argparse, calendar, csv, hashlib, io, json, math
from pathlib import Path
from collections import Counter
import numpy as np
import r55_pmedc_paired_bounds_original_source as original
BLOB_PLANT='ed388bb714a02b44d8921738a30ef661fb41af31'
BLOB_WEATHER='30b542c7caecca6eeac71ed25d1ec8ae4c7e20b1'
J=14; C=.95; EPS=1e-10

def channel_days(path,expected_sha,index,weather=False):
    raw=Path(path).read_bytes();got=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    assert got==expected_sha,(got,expected_sha)
    try:txt=raw.decode('utf-8-sig')
    except UnicodeDecodeError:txt=raw.decode('cp1252')
    reader=csv.reader(io.StringIO(txt))
    head=next(reader)
    all_days={};total=0;bad_total=0
    for row in reader:
        total+=1
        assert len(row)==len(head)
        dt,tm=row[0].split();d,m,y=map(int,dt.split('/'));date=f'20{y:02d}-{m:02d}-{d:02d}'
        rec=all_days.setdefault(date,{'s':0.,'n':0,'bad':0,'dupe':False,'clocks':set(),'neg':0})
        rec['n']+=1
        if tm in rec['clocks']:rec['dupe']=True
        rec['clocks'].add(tm)
        try:v=float(row[index])
        except ValueError:v=float('nan')
        if not math.isfinite(v):rec['bad']+=1;bad_total+=1;continue
        if weather and v<0:rec['neg']+=1
        rec['s']+=max(0,v) if weather else v
    assert total==280512,total
    agg={d:r['s'] for d,r in all_days.items() if r['n']==96 and len(r['clocks'])==96 and not r['dupe'] and r['bad']==0}
    return agg,{'source_blob':got,'file_name':Path(path).name,'channel_header':head[index],'rows':total,'valid_96_sample_days':len(agg),'nonnumeric_values':bad_total,
                'days_with_negative_irradiance':sum(int(r['neg']>0) for r in all_days.values()) if weather else None}

def features(month,channel_days):
    year,mo=map(int,month['month'].split('-'))
    calendar_days=calendar.monthrange(year,mo)[1]
    vals=[channel_days.get(f'{year:04d}-{mo:02d}-{i:02d}') for i in range(1,calendar_days+1)]
    arr=[]
    for start in range(calendar_days-2):
        v=vals[start:start+3]
        arr.append(sum(v) if all(t is not None for t in v) and sum(v)>0 else None)
    return arr

def make_scaled_bounds(months,channel):
    feats=[];hidden=[];complete=0
    for month in months:
        S=features(month,channel)
        for (start,vec),z in zip(original.block_vectors(month),S):
            if z is None:continue
            feats.append(z);hidden.append([u/z for u in vec]);complete+=1
    assert complete>=30,complete
    lo=[min(x[j] for x in hidden) for j in range(J)]
    hi=[max(x[j] for x in hidden) for j in range(J)]
    pl=[[min(x[j]-C*x[k] for x in hidden) for k in range(J)] for j in range(J)]
    ph=[[max(x[j]-C*x[k] for x in hidden) for k in range(J)] for j in range(J)]
    return lo,hi,pl,ph,complete

def run(array,plant,weather,out):
    amonths=original.read_months(array)
    plant_vals,plant_meta=channel_days(plant,BLOB_PLANT,index=1)
    irr_vals,irr_meta=channel_days(weather,BLOB_WEATHER,index=2,weather=True)
    mbox=original.make_bounds(amonths[:55]);cnt=Counter();monthly=[];badcases=[]
    boundmeta={};modelbounds={}
    for channel_name,v in [('plant',plant_vals),('irradiance',irr_vals)]:
        lo,hi,pl,ph,n=make_scaled_bounds(amonths[:55],v)
        boundmeta[channel_name]={'development_windows_with_channel':n,'dev_total_windows':1557,'test_windows_with_channel':0}
        modelbounds[channel_name]=(lo,hi,pl,ph)
    for month in amonths[55:]:
        full=[sum(x[j] for x in month['days']) for j in range(J)]
        ref=[x>=C*max(full)-EPS for x in full]
        ps=features(month,plant_vals);ws=features(month,irr_vals)
        ms=Counter()
        for idx,((start,hidden),p,w) in enumerate(zip(original.block_vectors(month),ps,ws)):
            retained=[full[j]-hidden[j] for j in range(J)]
            # Full original outcomes and all comparator models are unchanged.
            for channel_name,z in [('plant',p),('irradiance',w)]:
                if z is None:
                    cnt[channel_name+'_test_windows_channel_missing']+=1
                    continue
                boundmeta[channel_name]['test_windows_with_channel']+=1
                lo,hi,pl,ph=modelbounds[channel_name]
                box=original.classify(retained,[z*t for t in lo],[z*t for t in hi],pl,ph,'independent')
                paired=original.classify(retained,[z*t for t in lo],[z*t for t in hi],[[z*t for t in rr] for rr in pl],[[z*t for t in rr] for rr in ph],'paired')
                box_cov=all(z*lo[j]-EPS<=hidden[j]<=z*hi[j]+EPS for j in range(J))
                pair_cov=all(z*pl[j][k]-EPS<=hidden[j]-C*hidden[k]<=z*ph[j][k]+EPS for j in range(J) for k in range(J))
                cnt[channel_name+'_test_windows']+=1
                cnt[channel_name+'_independent_joint_coverage']+=int(box_cov)
                cnt[channel_name+'_paired_joint_coverage']+=int(pair_cov)
                for meth,status in [('independent',box),('paired',paired)]:
                    prefix=channel_name+'_'+meth+'_'
                    counts=sum(v!='?' for v in status)
                    errors=sum(v!='?' and (v=='I')!=bool(ref[j]) for j,v in enumerate(status))
                    cnt[prefix+'decided']+=counts
                    cnt[prefix+'wrong']+=errors
                    cnt[prefix+'full']+=int(counts==J)
                    cnt[prefix+'inc']+=status.count('I')
                    cnt[prefix+'exc']+=status.count('E')
                    if errors and len(badcases)<8:badcases.append({'channel':channel_name,'method':meth,'month':month['month'],'start_day':start,'wrong':errors,'box_covered':box_cov,'pair_covered':pair_cov})
        monthly.append({'month':month['month'],**dict(ms)})
    result={'state':'RESEARCH_ONLY_SURVIVING_SOURCE_CHANNELS_NOT_OPERATIONAL_CERTIFICATION',
        'array_blob':original.BLOB,'plant':plant_meta,'weather_irradiance':irr_meta,
        'source_roles':'Three co-timestamped CSVs; separate CSV != independently calibrated or separately persistent equipment',
        'models':'Training empirical envelopes of missing three-day array yields or pair contrasts divided by observed surviving-channel three-day sum; no energy imputation',
        'eligibility':boundmeta,
        'outcomes':dict(cnt),'illustrative_error_cases':badcases,
        'limits':['Conditional synthetic loss of array power ONLY while the Plant and Weather CSV channels remain visible','No evidence that plant is independent of array telemetries or survives genuine outage','No source-validated independent meter, no hard physical bounding law','Raw power and irradiance are separate files but matching clocks do not establish independent instruments','Descriptive 55-month fit, 24 later months already previously analysed, not new independent holdout','Some weather data fields have missing/nonfinite entries; channel availability is separately gated','Derived outputs only; licensed source rows are not redistributed']}
    o=Path(out);o.mkdir(parents=True,exist_ok=True)
    (o/'R55_SURVIVING_CHANNEL_BOUNDS_RESEARCH_ONLY.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('R55_CHANNEL_CONDITIONAL_BOUNDS_PASS',json.dumps({'eligible':boundmeta,'counts':dict(cnt),'first_errors':badcases[:3]},sort_keys=True),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--array',required=True);p.add_argument('--plant',required=True);p.add_argument('--weather',required=True);p.add_argument('--out',default='R55_SURVIVING_CHANNEL_RESULTS');x=p.parse_args();run(x.array,x.plant,x.weather,x.out)
