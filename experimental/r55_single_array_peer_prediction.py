#!/usr/bin/env python3
"""RESEARCH ONLY peer reconstruction for hypothetical ONE ARRAY logger outage.

The other 13 array channels are *assumed to remain measured* on three hidden
PV-array days, unlike the R55 manuscript's common-day all-array gap. This
changes the missingness mechanism, and findings must never be pooled.
No source records redistributed and no operational guarantee is asserted.
"""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import r55_pmedc_paired_bounds_original_source as source
import r55_missing_day_prediction_benchmark as base
J=14;C=.95
METHODS=('no_reconstruction','monthly_self_mean','peer_development_ratio','peer_same_month_ratio','peer_boundary_ratio')


def evaluate_models(month_y,s,j,dev_ratios):
    n=len(month_y)
    known=np.ones(n,bool);known[s:s+3]=False
    y=month_y[:,j]
    peers=np.mean(np.delete(month_y,j,axis=1),axis=1)
    obs=y[known].sum();gap_peers=peers[s:s+3].sum();retpeers=peers[known].sum()
    d={'no_reconstruction':0.,'monthly_self_mean':3.*obs/(n-3)}
    if retpeers>0:
        d['peer_same_month_ratio']=gap_peers*(obs/retpeers)
    d['peer_development_ratio']=gap_peers*dev_ratios[j]
    lb=s-1 if s>0 else None;rb=s+3 if s+3<n else None
    xL=(y[lb]/peers[lb]) if lb is not None and peers[lb]>0 else None
    xR=(y[rb]/peers[rb]) if rb is not None and peers[rb]>0 else None
    if xL is not None or xR is not None:
        v=0.
        for i in range(3):
            if xL is None:ratio=xR
            elif xR is None:ratio=xL
            else:ratio=xL*(1-(i+1)/4)+xR*((i+1)/4)
            v+=peers[s+i]*ratio
        d['peer_boundary_ratio']=v
    return {k:max(0.,v) for k,v in d.items() if v is not None and math.isfinite(v)}


def training_ratios(dev):
    sums=np.zeros(J); peer_sums=np.zeros(J)
    for month in dev:
        a=np.asarray(month['days'],float)
        sums+=np.sum(a,axis=0)
        peer_sums+=np.sum((np.sum(a,axis=1,keepdims=True)-a)/(J-1),axis=0)
    assert np.all(peer_sums>0)
    return sums/peer_sums


def accumulate(stats,month_y,s,j,estimate):
    full=np.sum(month_y,axis=0)
    reference=base.classify(full)
    truth=float(np.sum(month_y[s:s+3,j]))
    predicted=full.copy();predicted[j]=full[j]-truth+estimate
    inferred=base.classify(predicted)
    stats['cases']+=1
    stats['sum_abs_missing_energy_error']+=abs(estimate-truth)
    stats['sum_true_missing_energy']+=abs(truth)
    stats['exact_full_shortlists']+=int(np.array_equal(reference,inferred))
    stats['correct_masked_candidate_membership']+=int(reference[j]==inferred[j])
    stats['false_inclusions']+=int(inferred[j] and not reference[j])
    stats['false_exclusions']+=int(not inferred[j] and reference[j])
    stats['unrelated_candidate_membership_changes']+=int(np.sum(reference!=inferred)-int(reference[j]!=inferred[j]))
    stats['sum_squared_error']+=(estimate-truth)**2


def summarise(x):
    if not x or not x.get('cases'):return None
    return {'cases':int(x['cases']),
        'masked_energy_WAPE_pct':100*x['sum_abs_missing_energy_error']/x['sum_true_missing_energy'],
        'masked_energy_RMSE_normalised_sample_sum':math.sqrt(x['sum_squared_error']/x['cases']),
        'exact_full_shortlists':int(x['exact_full_shortlists']),
        'exact_full_shortlist_rate_pct':100*x['exact_full_shortlists']/x['cases'],
        'correct_masked_array_member':int(x['correct_masked_candidate_membership']),
        'false_inclusions':int(x['false_inclusions']),'false_exclusions':int(x['false_exclusions']),
        'other_array_membership_changes_due_to_masked_prediction':int(x['unrelated_candidate_membership_changes'])}


def self_test():
    # Identical normalized peer traces must recover hidden production exactly.
    v=np.arange(1,32,dtype=float)
    y=np.stack([1.3*v,1.1*v,1.6*v],axis=1)
    d=evaluate_models(y,8,0,[1.3/1.35,1.1/1.45,1.6/1.2])
    assert abs(d['peer_same_month_ratio']-sum(y[8:11,0]))<1e-8
    assert abs(d['peer_boundary_ratio']-sum(y[8:11,0]))<1e-8


def run(source_path,out):
    self_test()
    months=source.read_months(source_path)
    assert len(months)==79
    ratios=training_ratios(months[:55])
    counts={m:Counter() for m in METHODS}
    monthly=defaultdict(lambda:{m:Counter() for m in METHODS})
    unavailable=Counter()
    for month in months[55:]:
        yy=np.asarray(month['days'],float)
        for s in range(len(yy)-2):
            for j in range(J):
                estimates=evaluate_models(yy,s,j,ratios)
                for meth in METHODS:
                    if meth in estimates:
                        accumulate(counts[meth],yy,s,j,estimates[meth])
                        accumulate(monthly[month['month']][meth],yy,s,j,estimates[meth])
                    else:unavailable[meth]+=1
    assert counts['no_reconstruction']['cases']==680*J
    assert counts['peer_same_month_ratio']['cases']==680*J
    result={'status':'RESEARCH_ONLY_SINGLE_ARRAY_GAP_PREDICTION_NOT_COMMON_GAP',
         'source_git_blob':source.BLOB,
         'test_scope':{'months':24,'gap_placements_per_full_month':680,'single_array_missing_cases':9520,'dev_months':55,'q':.05},
         'definition':'One candidate has 3 missing days; other 13 channels retain their original measurements including masked dates; not the original all-candidate outage',
         'methods':{'no_reconstruction':'Masked candidate lost energy treated as zero',
             'monthly_self_mean':'Self retained month mean times 3 days',
             'peer_development_ratio':'Historical dev ratio candidate production/mean of other arrays times observed peers during omitted dates',
             'peer_same_month_ratio':'Matched retained same-month candidate/mean-peer ratio times observed peer energy during omitted dates',
             'peer_boundary_ratio':'Linear interpolation of candidate/peer ratio on boundary days, multiplied by peer output during missing days'},
         'missing_methods':dict(unavailable),
         'counts':{m:summarise(x) for m,x in counts.items()},
         'limitations':['Separate hypothetical missingness pattern from main R55 common gap',
             'Availability of the other 13 array channels during a real single-array outage is not confirmed',
             'Original dataset normalized per-unit not raw electrical kWh and arrays share a site',
             'Retrospective heldout split reused from earlier analysis, no independent prospective validation',
             'Dependent overlapping windows, same site, and no population-confidence interpretation',
             'No source rows publicly redistributed'],'redistributes_raw':False}
    d=Path(out);d.mkdir(parents=True,exist_ok=True)
    (d/'SINGLE_ARRAY_PEER_RECONSTRUCTION_RESEARCH_ONLY.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    with (d/'SINGLE_ARRAY_MONTHLY_AGGREGATES.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.writer(f);w.writerow(['month','model','cases','full_shortlist_correct','masked_member_correct','sum_abs_error','sum_true_hidden_energy'])
        for m,stats in sorted(monthly.items()):
            for meth,c in stats.items():
                if c['cases']:
                    w.writerow([m,meth,int(c['cases']),int(c['exact_full_shortlists']),int(c['correct_masked_candidate_membership']),round(c['sum_abs_missing_energy_error'],6),round(c['sum_true_missing_energy'],6)])
    print('R55_SINGLE_ARRAY_PEER_PREDICTION_SOURCE_PASS',json.dumps(result['counts'],sort_keys=True),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--array',required=True);a.add_argument('--out',default='R55_SINGLE_ARRAY_RESULTS');x=a.parse_args();run(x.array,x.out)
