#!/usr/bin/env python3
"""Research-only masked-three-day PV production reconstruction benchmark.

Pinned MORE-EU original source, 79 admissible months; first 55 historical months
for fitting global single-channel coefficients, last 24 previously-studied months
for retrospective testing (680 overlapping 3-day placements). Neither external
channel is asserted physically independent or available during real outage.
No direct source arrays are redistributed. No results replace R55-EP5 no-imputation
Solar paper. No tuned hyperparameters or leakage of hidden outcome in predictions.
"""
from __future__ import annotations
import argparse, calendar, csv, json, hashlib, math, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import r55_pmedc_paired_bounds_original_source as source
import r55_surviving_channel_envelopes as channel

METHODS = ('retained_month_mean', 'adjacent_day_interpolation',
           'weather_development_ratio', 'weather_same_month_ratio',
           'plant_development_ratio', 'plant_same_month_ratio')
J = 14
C = .95
EPS = 1e-10


def day_dates(month):
    year, mm = (int(a) for a in month['month'].split('-'))
    return [f'{year:04d}-{mm:02d}-{d:02d}' for d in range(1, calendar.monthrange(year, mm)[1]+1)]


def dev_fit(months, ch):
    """Fit zero-intercept per-array daily linear coefficient, development only."""
    xy = np.zeros(J, dtype=float); xx = 0.; used = 0
    for m in months:
        y = np.asarray(m['days'], dtype=float)
        for row, date in zip(y, day_dates(m)):
            v = ch.get(date)
            if v is not None and np.isfinite(v) and v > 0:
                xy += v * row; xx += v*v; used += 1
    assert used > 100 and xx>0, (used, xx)
    return np.maximum(xy/xx,0.), used


def channel_sum_and_month_ratio(y, dates, gap_start, ch):
    """Use available channel values in omitted 3 days, plus matched retained days."""
    gap_ids = range(gap_start, gap_start+3)
    hidden_channel=[ch.get(dates[i]) for i in gap_ids]
    if not all(v is not None and math.isfinite(v) and v >= 0 for v in hidden_channel):
        return None
    lost_z=sum(hidden_channel)
    known=[i for i,d in enumerate(dates) if i not in gap_ids and (ch.get(d) is not None) and math.isfinite(ch[d]) and ch[d]>=0]
    denom=sum(ch[dates[i]] for i in known)
    if denom<=0 or len(known)<10 or lost_z<=0: return None
    valid_energy=y[known].sum(axis=0)
    return lost_z, np.maximum(valid_energy/denom,0.),len(known)


def prediction_models(y, dates, s, weather, plant, betaw, betap):
    n=len(y)
    known=np.ones(n,bool);known[s:s+3]=False
    ret=y[known,:].sum(axis=0)
    model={'retained_month_mean':np.maximum(3*ret/(n-3),0.)}
    before=y[s-1,:] if s>0 else None
    after=y[s+3,:] if s+3<n else None
    if before is not None and after is not None:
        bridge=1.5*(before+after)
    elif before is not None:
        bridge=3.*before
    elif after is not None:
        bridge=3.*after
    else:
        raise AssertionError('A full month with 3 days always has a boundary')
    model['adjacent_day_interpolation']=np.maximum(bridge,0.)
    w=channel_sum_and_month_ratio(y,dates,s,weather)
    if w is not None:
        z,rat,nvalid=w
        model['weather_development_ratio']=np.maximum(z*betaw,0.)
        model['weather_same_month_ratio']=np.maximum(z*rat,0.)
    p=channel_sum_and_month_ratio(y,dates,s,plant)
    if p is not None:
        z,rat,nvalid=p
        model['plant_development_ratio']=np.maximum(z*betap,0.)
        model['plant_same_month_ratio']=np.maximum(z*rat,0.)
    return ret,model


def classify(full):
    return np.asarray(full)>= C*float(np.max(full))-EPS


def acc_new():
    return Counter()


def accumulate(a,hidden,pred,pred_members,ref,observed_members):
    assert len(hidden)==len(pred)==J
    errors=np.asarray(pred)-np.asarray(hidden)
    a['windows']+=1
    a['candidate_predictions']+=J
    a['sum_abs_error']+=float(np.sum(np.abs(errors)))
    a['sum_squared_error']+=float(np.dot(errors,errors))
    a['sum_true_hidden']+=float(np.sum(np.abs(hidden)))
    a['sum_pred_hidden']+=float(np.sum(pred))
    a['sum_truth_hidden_signed']+=float(np.sum(hidden))
    same=bool(np.array_equal(pred_members,ref))
    obs_correct=bool(np.array_equal(observed_members,ref))
    a['exact_shortlists']+=int(same)
    a['repaired_changed_windows']+=int(same and not obs_correct)
    a['damaged_previously_correct_windows']+=int((not same) and obs_correct)
    a['false_memberships']+=int(np.sum(pred_members!=ref))
    a['TP']+=int(np.sum(pred_members&ref))
    a['FP']+=int(np.sum(pred_members&~ref))
    a['FN']+=int(np.sum(~pred_members&ref))
    a['TN']+=int(np.sum(~pred_members&~ref))


def summarize(a):
    if not a or not a.get('windows'): return None
    n=int(a['candidate_predictions'])
    P=int(a['TP']); R=int(a['TP']+a['FN'])
    return {
        'windows':int(a['windows']),
        'candidate_predictions':n,
        'wape_hidden_3day_pct':100*a['sum_abs_error']/a['sum_true_hidden'] if a['sum_true_hidden'] else None,
        'rmse_hidden_3day_normalized_sample_sum':math.sqrt(a['sum_squared_error']/n),
        'hidden_total_bias_pct':100*(a['sum_pred_hidden']-a['sum_truth_hidden_signed'])/a['sum_true_hidden'] if a['sum_true_hidden'] else None,
        'exact_shortlists':int(a['exact_shortlists']),
        'exact_shortlist_rate_pct':100*a['exact_shortlists']/a['windows'],
        'candidate_membership_errors':int(a['false_memberships']),
        'repaired_changed_windows':int(a['repaired_changed_windows']),
        'damaged_previously_correct_windows':int(a['damaged_previously_correct_windows']),
        'TP':int(a['TP']),'FP':int(a['FP']),'FN':int(a['FN']),'TN':int(a['TN']),
        'shortlist_membership_recall_pct':100*P/R if R else None
    }


def self_test():
    y=np.array([[1.,2.],[2.,4.],[3.,6.],[4.,8.],[5.,10.],[6.,12.],[7.,14.]])
    dates=['2020-01-%02d'%i for i in range(1,8)]
    w={d:float(i) for i,d in enumerate(dates,1)}
    z=channel_sum_and_month_ratio(y,dates,2,w)
    # 7 days insufficient for >=10 valid calibration; expected fail closed.
    assert z is None
    assert np.array_equal(classify(np.array([95.,100.])),[True,True])
    assert not np.array_equal(classify(np.array([94.,100.])),[True,True])
    assert set(METHODS)==set(('retained_month_mean','adjacent_day_interpolation','weather_development_ratio','weather_same_month_ratio','plant_development_ratio','plant_same_month_ratio'))


def run(array,plant,weather,out):
    self_test()
    months=source.read_months(array)
    assert len(months)==79
    p,pm=channel.channel_days(plant,channel.BLOB_PLANT,1)
    w,wm=channel.channel_days(weather,channel.BLOB_WEATHER,2,weather=True)
    betaw,ndw=dev_fit(months[:55],w)
    betap,ndp=dev_fit(months[:55],p)
    cnt={k:acc_new() for k in METHODS}
    fair={k:acc_new() for k in METHODS}
    monthly=defaultdict(lambda:{k:acc_new() for k in METHODS})
    base_all=Counter(); base_fair=Counter(); missing=Counter()
    for month in months[55:]:
        dates=day_dates(month)
        y=np.asarray(month['days'],float)
        full=np.sum(y,axis=0)
        ref=classify(full)
        for s in range(len(y)-2):
            hidden=np.sum(y[s:s+3,:],axis=0)  # strictly validation truth, never a model feature
            retained,preds=prediction_models(y,dates,s,w,p,betaw,betap)
            assert np.max(np.abs((retained+hidden)-full))<1e-6
            observed_members=classify(retained)
            baseline_correct=bool(np.array_equal(observed_members,ref))
            base_all['windows']+=1; base_all['unchanged']+=int(baseline_correct)
            all_methods_present=len(preds)==len(METHODS)
            if all_methods_present:
                base_fair['windows']+=1; base_fair['unchanged']+=int(baseline_correct)
            for meth in METHODS:
                if meth not in preds:
                    missing[meth]+=1
                    continue
                pred=np.asarray(preds[meth],float)
                assert pred.shape==(J,) and np.all(np.isfinite(pred)) and np.min(pred)>=0
                inferred=classify(retained+pred)
                accumulate(cnt[meth],hidden,pred,inferred,ref,observed_members)
                accumulate(monthly[month['month']][meth],hidden,pred,inferred,ref,observed_members)
                if all_methods_present:
                    accumulate(fair[meth],hidden,pred,inferred,ref,observed_members)
    assert base_all['windows']==680 and base_all['unchanged']==513,base_all
    assert sum(cnt[x]['windows'] for x in METHODS[:2])==1360
    fair_n=base_fair['windows']
    assert fair_n>=300,(fair_n,dict(missing))
    assert all(fair[x]['windows']==fair_n for x in METHODS)
    report={
       'status':'RESEARCH_ONLY_MASKED_ORIGINAL_SOURCE_PREDICTION_BENCHMARK_NOT_MAIN_PAPER',
       'objective':'Predict 3-day missing normalized array output, and check downstream q=5% shortlist, not to certify natural outages',
       'array_blob':source.BLOB,'plant_blob':channel.BLOB_PLANT,'weather_blob':channel.BLOB_WEATHER,
       'split':{'admitted_complete_months':79,'historical_development_months':55,'later_months_previously_analysed':24,'test_mask_placements':680,'q':.05,'gap_length_days':3,'dependent_overlapping_windows':True},
       'development_day_counts':{'weather':ndw,'plant':ndp},
       'methods':{
         'retained_month_mean':'No external channel; monthly per-array retained-day average multiplied by three',
         'adjacent_day_interpolation':'No external channel; 3-day linear gap interpolation between observed before/after boundary days (single-sided at edges)',
         'weather_development_ratio':'Weather channel remains: fitted zero-intercept ratio from first 55 months times missing-day aggregate measured irradiance',
         'weather_same_month_ratio':'Weather channel remains: ratio of retained matched array sum to retained irradiance sum in same month times missing-day irradiance',
         'plant_development_ratio':'Plant channel remains: fitted zero-intercept array/plant ratio from first 55 months times missing-day plant-output sum',
         'plant_same_month_ratio':'Plant channel remains: ratio of retained matched array sum to retained plant sum in same month times missing-day plant output',
       },
       'original_non_imputation_baseline':{'all_680':dict(base_all),'strict_same_window_subset':dict(base_fair)},
       'eligible_counts_by_model':{k:int(cnt[k]['windows']) for k in METHODS},
       'missing_channels_by_model':dict(missing),
       'each_model_on_all_its_eligible_windows':{k:summarize(cnt[k]) for k in METHODS},
       'all_models_same_matched_windows':{k:summarize(fair[k]) for k in METHODS},
       'limits':[
           'A masked full historical month is not a genuine outage; eligibility is conditional on missing array power only',
           'Weather/plant data are assumed to remain observable in masked days and cannot be asserted to survive a field logging outage',
           'Plant power might be derived from array data or share wiring; its source independence is not established',
           'Train/test period is reused from previous 106Amen experiments, so it is not a fresh independent validation',
           'Overlapping three-day windows from each plant-month and candidate predictions are dependent; no probabilistic population generalization',
           'No imputed values introduced into locked R55-EP5 Solar manuscript, no commercial/physical-use claim',
           'The original MORE-EU third-party source rows are not redistributed',
           'Model families are fixed simple baselines, no hyperparameter optimization, and best post-hoc model is exploratory',
       ],'source_rows_redistributed':False,
    }
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'RESEARCH_ONLY_MISSING_DAY_PREDICTION_SUMMARY.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (out/'MONTHLY_DERIVED_COUNTS_NO_RAW.csv').open('w',newline='',encoding='utf8') as f:
        wr=csv.writer(f);wr.writerow(['month','model','windows','exact_shortlists','repaired_changed_windows','damaged_previously_correct_windows','candidate_membership_errors','sum_abs_error_normalized_sample_sum','sum_true_hidden_normalized_sample_sum'])
        for m,met in sorted(monthly.items()):
            for model,a in met.items():
                if not a.get('windows'):continue
                wr.writerow([m,model,int(a['windows']),int(a['exact_shortlists']),int(a['repaired_changed_windows']),int(a['damaged_previously_correct_windows']),int(a['false_memberships']),round(a['sum_abs_error'],6),round(a['sum_true_hidden'],6)])
    print('R55_PV_MISSING_DAY_PREDICTION_SOURCE_VERIFIED_PASS',json.dumps({'baseline':dict(base_all),'fair':dict(base_fair),'results':report['each_model_on_all_its_eligible_windows'],'fair_results':report['all_models_same_matched_windows']},sort_keys=True),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--array',required=True)
    ap.add_argument('--plant',required=True)
    ap.add_argument('--weather',required=True)
    ap.add_argument('--out',default='R55_MISSING_DAY_PREDICTION_RESULTS')
    x=ap.parse_args();run(x.array,x.plant,x.weather,x.out)
