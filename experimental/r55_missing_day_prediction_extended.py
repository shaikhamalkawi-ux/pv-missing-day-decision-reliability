#!/usr/bin/env python3
"""RESEARCH ONLY second, predeclared benchmark of PV missing-day reconstruction.

Fixes alternative per-array functional responses to available surviving channels.
Model coefficients are estimated exclusively from observed non-masked days of
that same historical month; hidden array outputs are never used for prediction.
No tuning, no physical independence claim for external channels, no manuscript edit.
"""
from __future__ import annotations
import argparse, csv, json, math
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import r55_missing_day_prediction_benchmark as base
import r55_pmedc_paired_bounds_original_source as original
import r55_surviving_channel_envelopes as channel

EPS=1e-10
EXTENDED=('plant_boundary_ratio_interpolation','weather_boundary_ratio_interpolation',
          'plant_same_month_quadratic','weather_same_month_quadratic',
          'plant_weather_joint_same_month_regression')


def available_daily_vector(dates, vals):
    return np.array([vals.get(date, float('nan')) for date in dates],float)


def boundary_ratio_model(y, daily_channel, s):
    n=len(y)
    if not np.all(np.isfinite(daily_channel[s:s+3])) or np.any(daily_channel[s:s+3]<0):return None
    left=s-1 if s>=1 else None
    right=s+3 if s+3<n else None
    rleft=(np.maximum(y[left,:],0.)/daily_channel[left]) if (left is not None and np.isfinite(daily_channel[left]) and daily_channel[left]>0) else None
    rright=(np.maximum(y[right,:],0.)/daily_channel[right]) if (right is not None and np.isfinite(daily_channel[right]) and daily_channel[right]>0) else None
    if rleft is None and rright is None:return None
    predicted=np.zeros(y.shape[1],float)
    for idx,di in enumerate(range(s,s+3)):
        if rleft is not None and rright is not None:
            ratio=(1-(idx+1)/4)*rleft+((idx+1)/4)*rright
        elif rleft is not None:ratio=rleft
        else:ratio=rright
        predicted+=float(daily_channel[di])*ratio
    return np.maximum(predicted,0.)


def local_regression(y, s, features):
    """Complete-case fixed-feature OLS with no intercept; no masked y enters fit."""
    n,k=features.shape
    known=np.ones(n,dtype=bool);known[s:s+3]=False
    train=known&np.all(np.isfinite(features),axis=1)&np.all(features>=0,axis=1)
    if np.sum(train)<max(12,3*k) or not np.all(np.isfinite(features[s:s+3])):return None
    if np.any(features[s:s+3]<0):return None
    x=features[train,:]
    scaler=np.median(x,axis=0)
    if np.any(scaler<=0):return None
    scaled=x/scaler[None,:]
    if np.linalg.matrix_rank(scaled)!=k or np.linalg.cond(scaled)>1e8:return None
    coef=np.linalg.lstsq(scaled, y[train,:],rcond=None)[0]
    pred=features[s:s+3,:]/scaler[None,:]@coef
    return np.maximum(np.sum(pred,axis=0),0.)


def models(y,dates,s,weather,plant):
    w=available_daily_vector(dates,weather);p=available_daily_vector(dates,plant)
    out={}
    for label,ch in [('plant_boundary_ratio_interpolation',p),('weather_boundary_ratio_interpolation',w)]:
        ans=boundary_ratio_model(y,ch,s)
        if ans is not None:out[label]=ans
    if np.all(np.isfinite(p)):
        x=np.stack([p,p*p/np.nanmedian(p) if np.nanmedian(p)>0 else p*p],axis=1)
        ans=local_regression(y,s,x)
        if ans is not None:out['plant_same_month_quadratic']=ans
    if np.all(np.isfinite(w)):
        x=np.stack([w,w*w/np.nanmedian(w) if np.nanmedian(w)>0 else w*w],axis=1)
        ans=local_regression(y,s,x)
        if ans is not None:out['weather_same_month_quadratic']=ans
    if np.all(np.isfinite(p)) and np.all(np.isfinite(w)):
        medp=float(np.nanmedian(p)); medw=float(np.nanmedian(w))
        if medp>0 and medw>0:
            x=np.stack([p,w,p*w/medw],axis=1)
            ans=local_regression(y,s,x)
            if ans is not None:out['plant_weather_joint_same_month_regression']=ans
    return out


def self_tests():
    days=24
    dates=[f'2020-01-{i+1:02d}' for i in range(days)]
    plant={d:float(i+10) for i,d in enumerate(dates)}
    w={d:float(2*i+23) for i,d in enumerate(dates)}
    p=np.array(list(plant.values()));weather=np.array(list(w.values()))
    Y=np.stack([2*p+.01*p*p,3*p+.02*p*p],axis=1)
    pred=models(Y,dates,8,w,plant)
    assert pred['plant_same_month_quadratic'].shape==(2,)
    truth=Y[8:11].sum(axis=0)
    assert np.allclose(pred['plant_same_month_quadratic'],truth,atol=1e-7), ('quadratic recovery',pred,truth)
    assert np.allclose(pred['plant_boundary_ratio_interpolation'],truth,atol=1.)
    for meth,z in pred.items(): assert np.all(np.isfinite(z)) and np.all(z>=0),meth


def run(array,plant,weather,out):
    self_tests()
    months=original.read_months(array)
    p,pmeta=channel.channel_days(plant,channel.BLOB_PLANT,1)
    w,wmeta=channel.channel_days(weather,channel.BLOB_WEATHER,2,weather=True)
    # DO NOT train global models on test months; these five local methods use only
    # retained days of each target month, with fixed formulas and no hyperparameters.
    counts={k:base.acc_new() for k in EXTENDED}
    fair={k:base.acc_new() for k in EXTENDED}
    oldcount=Counter();summary_by_month=defaultdict(lambda:{k:base.acc_new() for k in EXTENDED})
    missing=Counter()
    for month in months[55:]:
        dates=base.day_dates(month)
        y=np.asarray(month['days'],float)
        ref=base.classify(y.sum(axis=0))
        for s in range(len(y)-2):
            hidden=y[s:s+3].sum(axis=0)
            retained=np.sum(np.delete(y,np.s_[s:s+3],axis=0),axis=0)
            obs=base.classify(retained)
            modelpred=models(y,dates,s,w,p)
            oldcount['windows']+=1
            oldcount['observed_exact']+=int(np.array_equal(obs,ref))
            matched_all=len(modelpred)==len(EXTENDED)
            oldcount['all_methods_available']+=int(matched_all)
            for meth in EXTENDED:
                if meth not in modelpred:
                    missing[meth]+=1;continue
                pred=modelpred[meth]
                inferred=base.classify(retained+pred)
                base.accumulate(counts[meth],hidden,pred,inferred,ref,obs)
                base.accumulate(summary_by_month[month['month']][meth],hidden,pred,inferred,ref,obs)
                if matched_all:base.accumulate(fair[meth],hidden,pred,inferred,ref,obs)
    assert oldcount['windows']==680 and oldcount['observed_exact']==513
    assert all(v['windows']<=680 for v in counts.values())
    result={'state':'RESEARCH_ONLY_EXTENDED_METHODS_SOURCE_VERIFIED_NOT_MAIN_PAPER',
        'pinned_array_blob':original.BLOB,'pinned_plant_blob':channel.BLOB_PLANT,'pinned_weather_blob':channel.BLOB_WEATHER,
        'months':{'dev':55,'test_already_inspected':24,'test_3day_windows':680},
        'nonimputation_baseline':dict(oldcount),
        'model_formulas':{'plant_boundary_ratio_interpolation':'Interpolation of candidate-specific boundary-day normalized share y_j/plant; multiplied by surviving plant daily values',
             'weather_boundary_ratio_interpolation':'Interpolation of candidate-specific boundary-day normalized share y_j/irradiance; multiplied by surviving irradiance daily values',
             'plant_same_month_quadratic':'OLS with no intercept on plant_daily and plant_daily^2: trained from non-deleted days of same month',
             'weather_same_month_quadratic':'OLS with no intercept on irradiance_daily and irradiance_daily^2: trained from non-deleted days of same month',
             'plant_weather_joint_same_month_regression':'OLS no intercept on plant_daily, irradiance_daily and their interaction, trained on non-deleted days'},
        'eligibility':{k:int(v['windows']) for k,v in counts.items()},
        'missing':dict(missing),
        'each_eligible_scope':{k:base.summarize(v) for k,v in counts.items()},
        'fair_common_scope':{k:base.summarize(v) for k,v in fair.items()},
        'limitations':['All outputs are retrospective conditional reconstructions, not actual outage or certified physical bounds',
          'These scenarios assume plant/weather channels survive array telemetry loss; their instrument independence and persistence have not been verified',
          'No tuning or model selection on the 24 later months; methods declared before seeing the runs',
          'Benchmark compares dependent overlapping windows of the same plant, cannot infer confidence or population benefit',
          'Last 24 months were previously studied by R55; exploratory reused holdout, not independent future validation',
          'Source-specific per-unit sample sums are not absolute kWh; only normalized ratios are claimed',
          'Licensed raw source rows not redistributed'],'raw_rows_redistributed':False}
    d=Path(out);d.mkdir(exist_ok=True,parents=True)
    (d/'EXTENDED_PREDICTION_MODELS_RESEARCH_ONLY.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    with (d/'EXTENDED_MONTHLY_DERIVED_SUMMARY.csv').open('w',newline='',encoding='utf8') as f:
        wr=csv.writer(f);wr.writerow(['month','model','windows','exact_shortlists','repaired_changed','damaged_originally_correct','candidate_membership_errors','wape_percent'])
        for m,methods in sorted(summary_by_month.items()):
            for label,a in methods.items():
                s=base.summarize(a)
                if s:
                    wr.writerow([m,label,s['windows'],s['exact_shortlists'],s['repaired_changed_windows'],s['damaged_previously_correct_windows'],s['candidate_membership_errors'],s['wape_hidden_3day_pct']])
    print('R55_PV_EXTENDED_PREDICTION_SOURCE_VERIFIED_PASS',json.dumps({'baseline':dict(oldcount),'eligible':result['eligibility'],'results':result['each_eligible_scope'],'fair':result['fair_common_scope']},sort_keys=True),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--array',required=True);parser.add_argument('--plant',required=True);parser.add_argument('--weather',required=True)
    parser.add_argument('--out',default='R55_PV_EXTENDED_PREDICTION_DERIVED_ONLY')
    args=parser.parse_args();run(args.array,args.plant,args.weather,args.out)
