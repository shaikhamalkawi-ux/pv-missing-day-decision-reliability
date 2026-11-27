#!/usr/bin/env python3
"""SOURCE-LOCKED RESEARCH ONLY: evaluate engineer abstention under empirical error envelopes.

The exact near-best interval logic is proved only conditional on a VALID error bound.
Here the envelopes are retrospective, development-month maxima and are NOT
physical guarantees. Test months have been studied before: not prospective.
No source rows or trained machine learning objects are redistributed.
"""
import argparse, json, math, hashlib
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import r55_pmedc_paired_bounds_original_source as old
import r55_single_array_peer_prediction as peer

Q=.05; J=14; C=1-Q; EPS=1e-9

def status_1unknown(full_observed, target, estimate, margin):
    # All peers have exact full-month normalized totals, one target is uncertain.
    lo=full_observed.copy();hi=full_observed.copy()
    lo[target]=max(0.,estimate-margin);hi[target]=estimate+margin
    status=[]
    for j in range(len(lo)):
        maxu=max(hi[k] for k in range(len(lo)) if k!=j)
        maxl=max(lo[k] for k in range(len(lo)) if k!=j)
        if lo[j]>=C*maxu-EPS:status.append('I')
        elif hi[j]<C*maxl-EPS:status.append('E')
        else:status.append('?')
    return status

def evaluate(src,out):
    months=old.read_months(src)
    assert len(months)==79
    dev,test=months[:55],months[55:]
    devmax=np.zeros(J);monthly_mx=[];skipped_dev=0
    for mt in dev:
        vals=np.asarray(mt['days'],float)
        current=np.zeros(J)
        for s in range(len(vals)-2):
            for j in range(J):
                pred=peer.evaluate_models(vals,s,j,np.ones(J)).get('peer_boundary_ratio')
                if pred is None:
                    skipped_dev+=1
                    continue
                truth=float(vals[s:s+3,j].sum())
                current[j]=max(current[j],abs(pred-truth))
        devmax=np.maximum(devmax,current)
        monthly_mx.append(current)
    mx=np.stack(monthly_mx)
    def higher_quantile(a,p):
        # Source months (not overlapping windows) are units for envelope choice.
        return np.sort(a,axis=0)[max(0,min(len(a)-1,math.ceil(p*len(a))-1))]
    envelope={'monthly_max_90pct':higher_quantile(mx,.90), 'development_max':devmax}
    stats={name:Counter() for name in envelope}
    monthly={name:defaultdict(Counter) for name in envelope}
    for mt in test:
        yy=np.asarray(mt['days'],float); full=yy.sum(axis=0); truth_memb=full>=C*full.max()-EPS
        for s in range(len(yy)-2):
            for j in range(J):
                hidden=float(yy[s:s+3,j].sum());ret=full.copy();ret[j]-=hidden
                predicted=peer.evaluate_models(yy,s,j,np.ones(J))['peer_boundary_ratio']
                reco=ret.copy();reco[j]+=predicted
                point=reco>=C*reco.max()-EPS
                for name,env in envelope.items():
                    st=stats[name];smon=monthly[name][mt['month']]
                    band=float(env[j]);resid=abs(predicted-hidden)
                    mask=status_1unknown(reco,j,reco[j],band)
                    resolved=all(x!='?' for x in mask)
                    conditional_set=np.array([x=='I' for x in mask])
                    wrong=bool(resolved and np.any(conditional_set!=truth_memb))
                    st['cases']+=1;st['point_full_correct']+=int(np.array_equal(point,truth_memb))
                    st['interval_contains_truth']+=int(resid<=band+EPS)
                    st['fully_resolved']+=int(resolved)
                    st['resolved_wrong']+=int(wrong)
                    st['certified_candidate_memberships']+=sum(x!='?' for x in mask)
                    st['candidate_label_wrong']+=sum(x!='?' and (x=='I')!=bool(truth_memb[k]) for k,x in enumerate(mask))
                    st['resolved_not_covered']+=int(resolved and resid>band+EPS)
                    st['prediction_abs_error_sum']+=resid
                    st['true_hidden_sum']+=abs(hidden)
                    for key,v in [('cases',1),('fully_resolved',int(resolved)),('resolved_wrong',int(wrong)),('interval_contains_truth',int(resid<=band+EPS))]:smon[key]+=v
    assert all(x['cases']==9520 for x in stats.values())
    d={
       'state':'RESEARCH_ONLY_EMPIRICAL_ERROR_ENVELOPES_NOT_OPERATIONAL_CERTIFICATION',
       'source_sha1':old.BLOB,
       'protocol':'55 source-calendar months development, 24 later previously studied months; one masked target array per 3-day block, other 13 remain observed',
       'source_pinned':True,
       'error_envelope':'For each array, per-calendar-development-month maximum over all 3-day masked starts of |peer-boundary estimated hidden 3-day sum - actual 3-day sum|. Quantile is higher discrete order statistic across months. No physical error theorem or distribution-free confidence.',
       'q':Q, 'arrays':J,'development_months':55,'test_months':24,'cases':9520,
       'development_missing_predictor_excluded_count':skipped_dev,
       'thresholds':{k:[float(z) for z in v] for k,v in envelope.items()},
       'results':{k:dict(v) for k,v in stats.items()},
       'test_monthly_counts':{k:{mon:dict(stat) for mon,stat in v.items()} for k,v in monthly.items()},
       'claim_limits':[
        'Historical empirical envelope is not an independently physically justified hard bound',
        'A conditionally resolved shortlist is not an operational certificate even if test error=0',
        '24 later months were already inspected in prior experiments',
        'Overlapping windows and site-specific array measurements are dependent',
        'Masking all arrays together is fundamentally different and not solved by peer imputation',
        'Only normalized source output; do not convert to kWh',
        'No original data redistributed']}
    dst=Path(out);dst.mkdir(exist_ok=True,parents=True)
    (dst/'R56_CONDITIONAL_INTERVAL_SOURCE_RESULTS.json').write_text(json.dumps(d,indent=2)+'\n')
    print('R56_CONDITIONAL_GATE_SOURCE_REPLAY_PASS',json.dumps({k:{y:v.get(y) for y in ('cases','fully_resolved','resolved_wrong','interval_contains_truth','point_full_correct','candidate_label_wrong')} for k,v in d['results'].items()}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',default='R56_CONDITIONAL_GATE_DERIVED_ONLY');a=p.parse_args();evaluate(a.source,a.out)
