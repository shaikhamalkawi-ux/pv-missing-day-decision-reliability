#!/usr/bin/env python3
"""106Amen research-only machine-learning prediction for three-day SINGLE-ARRAY gaps.

Frozen study: original MORE-EU 14-array source, SHA1 Git blob 5611277efdd581bb839ec380239846a43ebe0ba7.
First 55 full eligible months -> global training (per-array RF/XGB).
Last 24 complete months -> exploratory retained-month validation of 680 overlapping 3-day positions
x 14 masked arrays = 9,520 dependent, counterfactual examples. Holdout previously inspected.
Other 13 array readings DURING each simulated single-array outage stay observed; no physical claim.
Only reported complete reference, never masked target readings, enters scoring. Local calibration uses
only nonmasked target readings of the same test month. No weather/plant channels are assumed.
No tuned hyperparameters, no test-based feature selection, no source data redistributed.

Run: python run_ml_benchmark.py --source '/path/to/Array Power.csv' --out results
"""
from __future__ import annotations
import argparse, csv, json, math, os, platform, sys, hashlib, time
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import sklearn
import xgboost
import r55_pmedc_paired_bounds_original_source as original
import r55_single_array_peer_prediction as prior

J=14; C=.95; Q=.05; GAP=3; EPS=1e-10; SEED=27112026
MODELS=("monthly_self_mean", "peer_same_month_ratio", "peer_boundary_ratio",
        "rf_global", "rf_month_calibrated", "xgb_global", "xgb_month_calibrated")
RF_CFG=dict(n_estimators=240,max_depth=9,min_samples_leaf=3,max_features=.9,
            bootstrap=True,random_state=SEED,n_jobs=1)
XGB_CFG=dict(n_estimators=240,max_depth=4,learning_rate=.05,min_child_weight=5,
             subsample=.85,colsample_bytree=.9,reg_lambda=3.0,objective="reg:squarederror",
             tree_method="hist",random_state=SEED,n_jobs=1,verbosity=0)

def rows(month):
    from calendar import monthrange
    year, m = (int(v) for v in month['month'].split('-'))
    a=np.asarray(month['days'],dtype=np.float64)
    assert a.shape==(monthrange(year,m)[1],J),a.shape
    assert np.isfinite(a).all() and a.min()>=0, "Input must be nonnegative for PV screening"
    d=np.arange(1,len(a)+1)
    from datetime import date
    doy=np.array([date(year,m,int(day)).timetuple().tm_yday for day in d],dtype=np.float64)
    return a,doy

def features(a,dayofyear,j):
    """Uses only measured other-array power and known calendar (never target j or month target sum)."""
    p=np.delete(a,j,axis=1)
    return np.column_stack([p,p.mean(axis=1),p.std(axis=1),
                            np.sin(2*np.pi*dayofyear/365.25),
                            np.cos(2*np.pi*dayofyear/365.25)])

def member(v):
    x=np.asarray(v,dtype=float)
    assert x.shape==(J,) and np.isfinite(x).all() and x.min()>=-1e-9
    return x>=C*float(x.max())-EPS

def accum(a,ref,pred,truth,gap,j):
    a['cases']+=1
    a['abs_error']+=abs(pred-truth)
    a['squared_error']+=(pred-truth)**2
    a['true_gap']+=abs(truth)
    corrected=np.array(gap,copy=True);corrected[j]+=pred
    got=member(corrected)
    a['full_exact']+=int(np.array_equal(ref,got))
    a['masked_member_correct']+=int(ref[j]==got[j])
    a['false_inclusion']+=int(bool(got[j]) and not bool(ref[j]))
    a['false_exclusion']+=int(not bool(got[j]) and bool(ref[j]))
    a['nonmasked_membership_changes']+=int(np.count_nonzero(ref!=got))-int(ref[j]!=got[j])

def output_stats(a):
    n=a['cases']
    assert n==9520,n
    return {
        'cases':n,'energy_wape_percent':100*a['abs_error']/a['true_gap'],
        'energy_rmse_normalized_day_sums':math.sqrt(a['squared_error']/n),
        'full_shortlist_exact':a['full_exact'],
        'full_shortlist_accuracy_percent':100*a['full_exact']/n,
        'masked_membership_correct':a['masked_member_correct'],
        'false_inclusions':a['false_inclusion'],
        'false_exclusions':a['false_exclusion'],
        'nonmasked_membership_changes':a['nonmasked_membership_changes'],
        'sum_abs_error':a['abs_error'],'sum_true_gap':a['true_gap']}

def self_test():
    # No target leakage: feature values invariant under arbitrary change to masked target.
    rng=np.random.default_rng(34)
    m=rng.uniform(.01,10,size=(31,J))
    f=features(m,np.arange(1,32,dtype=float),7)
    m[:,7]+=500
    assert np.array_equal(features(m,np.arange(1,32,dtype=float),7),f)
    assert len(RF_CFG)>1 and len(XGB_CFG)>1
    a=np.array([95.0,100.0]+[0.]*(J-2));assert member(a)[:2].all()
    assert member(np.array([94.,100.]+[0.]*(J-2)))[0]==False

def run(source,outdir):
    t0=time.monotonic();self_test()
    months=original.read_months(source)
    assert len(months)==79 and len(months[:55])==55 and len(months[55:])==24
    dev=months[:55]; test=months[55:]
    dev_y=[];dev_doy=[]
    for m in dev:
        a,doy=rows(m);dev_y.append(a);dev_doy.append(doy)
    dev_y=np.vstack(dev_y); dev_doy=np.concatenate(dev_doy)
    print('FROZEN_RF_CONFIG',RF_CFG,flush=True)
    print('FROZEN_XGB_CONFIG',XGB_CFG,flush=True)
    print('TRAIN_DAYS',len(dev_y),'DEV_MONTHS',len(dev),'TEST_MONTHS',len(test),flush=True)
    train_meta=[]
    # independent per-array regression (no validation data used for fitting).
    rf_preds=[{} for _ in range(J)]; xgb_preds=[{} for _ in range(J)]
    for j in range(J):
        x=features(dev_y,dev_doy,j); y=dev_y[:,j]
        rf=RandomForestRegressor(**RF_CFG).fit(x,y)
        xgb=xgboost.XGBRegressor(**XGB_CFG).fit(x,y)
        for mt in test:
            arr,doy=rows(mt)
            xx=features(arr,doy,j)
            rf_preds[j][mt['month']]=np.maximum(rf.predict(xx),0.)
            xgb_preds[j][mt['month']]=np.maximum(xgb.predict(xx),0.)
        train_meta.append({'target_array':j+1,'n_train_days':len(x),
                           'num_features':x.shape[1],'feature_def':'13 other-array daily sums, their mean and SD, day-of-year sine/cosine'})
        print('TRAINED_ARRAY',j+1,'of',J,flush=True)
    assert all(len(q)==24 for q in rf_preds+xgb_preds)
    devrat=prior.training_ratios(dev)
    summaries={m:Counter() for m in MODELS}
    monthly={}
    for mt in test:
        key=mt['month']; yy,doy=rows(mt)
        n=len(yy);full=yy.sum(axis=0);ref=member(full)
        local={m:Counter() for m in MODELS}
        for s in range(n-2):
            mask=np.ones(n,dtype=bool);mask[s:s+3]=False
            for j in range(J):
                truth=float(yy[s:s+3,j].sum())
                rsum=full.copy(); rsum[j]-=truth
                pre=prior.evaluate_models(yy,s,j,devrat)
                peerbaseline={m:pre[m] for m in MODELS[:3]}
                pred={'rf_global':float(np.sum(rf_preds[j][key][s:s+3])),
                      'xgb_global':float(np.sum(xgb_preds[j][key][s:s+3]))}
                for method,base in [('rf_month_calibrated','rf'),('xgb_month_calibrated','xgb')]:
                    d=(rf_preds if base=='rf' else xgb_preds)[j][key]
                    den=float(np.sum(d[mask]))
                    assert den>0,(key,s,j,method)
                    # Admissible local update: target y from ONLY retained days.
                    scale=float(np.sum(yy[mask,j]))/den
                    pred[method]=float(np.sum(d[s:s+3])*scale)
                pred.update(peerbaseline)
                for m in MODELS:
                    assert m in pred and pred[m]>=0 and math.isfinite(pred[m]),(m,key,s,j)
                    accum(summaries[m],ref,pred[m],truth,rsum,j)
                    accum(local[m],ref,pred[m],truth,rsum,j)
        monthly[key]={k:dict(v) for k,v in local.items()}
        print('EVALUATED_MONTH',key,flush=True)
    final={m:output_stats(v) for m,v in summaries.items()}
    # Previous original-source peer benchmark must match byte-for-byte metrics up to machine roundoff.
    assert final['monthly_self_mean']['full_shortlist_exact']==6960,final['monthly_self_mean']
    assert final['peer_same_month_ratio']['full_shortlist_exact']==9061
    assert final['peer_boundary_ratio']['full_shortlist_exact']==9145
    assert abs(final['peer_boundary_ratio']['energy_wape_percent']-1.9120681546688565)<1e-8
    # Aggregated month-level paired descriptive comparisons, not independent sample inference.
    b='peer_boundary_ratio'; diffs={}
    for m in [x for x in MODELS if x!=b]:
        gap=[monthly[k][m]['full_exact']-monthly[k][b]['full_exact'] for k in sorted(monthly)]
        diffs[m]={'months_win':sum(z>0 for z in gap),'months_tie':sum(z==0 for z in gap),
                  'months_lose':sum(z<0 for z in gap),'gain_full_list_counts_over_peer':sum(gap),
                  'per_month_delta':dict(zip(sorted(monthly),gap))}
    result={'status':'RESEARCH_ONLY_NOT_SOLAR_MANUSCRIPT_RESULT',
            'study':'106Amen experimental RF/XGBoost vs fixed baseline for one-array 3-day missingness',
            'source_git_blob_sha1':original.BLOB,
            'scope':{'eligible_complete_months':79,'development_months':55,'test_months':24,
                     'n_train_days':len(dev_y),'gap_days':GAP,'arrays':J,
                     'test_3day_placements':680,'single_array_test_cases':9520,'q':Q,
                     'holdout_reused_from_prior_work':True},
            'methods':{
                'monthly_self_mean':'Retained mean of target days x3, no peers during gap',
                'peer_same_month_ratio':'Retained target/mean-peer monthly ratio x measured peers during gap',
                'peer_boundary_ratio':'Boundary-day target/peer ratio linearly interpolated across gap; measured other arrays during gap',
                'rf_global':'RandomForest trained on first 55 months per target; 13 other arrays + mean/std and calendar; no target within 3-day gap',
                'xgb_global':'XGBRegressor trained on first 55 months per target; same features',
                'rf_month_calibrated':'RF_global daily predictions times target known-days sum / RF known-days sum in same test month excluding current gap',
                'xgb_month_calibrated':'XGB_global daily predictions times target known-days sum / XGB known-days sum in same test month excluding current gap'},
            'hyperparameters':{'random_forest':RF_CFG,'xgboost':XGB_CFG},
            'versions':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__,'xgboost':xgboost.__version__},
            'locked_baseline_reproduced':True,'results':final,'monthly_comparison_to_peer':diffs,
            'training_registry':train_meta,
            'limitations':[
                'Single-array missingness ONLY; original R55-EP5 paper evaluates whole-array common-day loss; do not pool',
                'Other 13 arrays are assumed to remain measured during the three masked days; not field verified',
                'Retrospective artificial gaps in one plant; overlapping positions and candidate decisions statistically dependent',
                'The 24 later months have already been inspected in earlier research, so this is NOT an independent confirmatory holdout',
                'Tree models trained on dev months only; monthly calibration uses only test-month target known days, never hidden y',
                'No per-array hardware specs, physics-informed limit, or actual outage event was observed',
                'Reference metric is normalized source output, not electrical kWh and not PV fault labels',
                'The result does not establish benefit on other sites, weather conditions, hardware faults or real outages',
                'No raw MORE-EU CC BY-NC telemetry copied into deliverables'],
            'runtime_seconds':round(time.monotonic()-t0,2)}
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    (out/'ML_RF_XGB_DECISION_BENCHMARK_RESEARCH_ONLY.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (out/'MODEL_COMPARISON_DERIVED_ONLY.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f)
        w.writerow(['model','cases','energy_wape_pct','energy_rmse_norm','correct_full_shortlists','shortlist_accuracy_pct','masked_member_correct','false_inclusions','false_exclusions','months_wins_vs_peer','months_ties_vs_peer','months_losses_vs_peer'])
        for m in MODELS:
            x=final[m];s=diffs.get(m,{})
            w.writerow([m,x['cases'],x['energy_wape_percent'],x['energy_rmse_normalized_day_sums'],x['full_shortlist_exact'],x['full_shortlist_accuracy_percent'],x['masked_membership_correct'],x['false_inclusions'],x['false_exclusions'],s.get('months_win'),s.get('months_tie'),s.get('months_lose')])
    with (out/'MONTH_LEVEL_MODEL_COMPARISONS_DERIVED_ONLY.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['month','model','cases','correct_full_shortlists','energy_wape_pct','masked_member_correct','false_inclusion','false_exclusion'])
        for month,v in sorted(monthly.items()):
            for m,a in v.items():
                w.writerow([month,m,a['cases'],a['full_exact'],100*a['abs_error']/a['true_gap'],a['masked_member_correct'],a['false_inclusion'],a['false_exclusion']])
    print('R55_ML_RF_XGB_SOURCE_VERIFIED_PASS',json.dumps({'baseline':final[b],
        'all_models':{m:{'WAPE':round(v['energy_wape_percent'],5),'full_shortlist_exact':v['full_shortlist_exact']} for m,v in final.items()},
        'runtime_sec':result['runtime_seconds']},sort_keys=True),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',default='R55_ML_RF_XGB_DERIVED_ONLY')
    args=ap.parse_args();run(args.source,args.out)
