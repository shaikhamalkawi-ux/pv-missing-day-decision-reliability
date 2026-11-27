#!/usr/bin/env python3
"""Independent source-pinned audit of R56/R57 colleague common-gap suggestions.
Original MORE-EU Array Power.csv (Git blob verified by imported parser).
All 14 arrays lose the identical three days, not one-array gaps. Research-only.
Predictions never access hidden target days. Only aggregate derived outcomes exported.
"""
import argparse, json, math, collections
from pathlib import Path
import numpy as np
import r55_pmedc_paired_bounds_original_source as upstream

NARRAY=14; Q=.05; C=1-Q; EPS=1e-10
METHODS=['retained_no_fill','retained_month_mean','retained_month_median','boundary_linear_bridge']

def shortlist(totals):
    y=np.asarray(totals,dtype=float)
    assert y.shape==(NARRAY,) and np.isfinite(y).all()
    return y>=C*np.max(y)-EPS

def trial(y,start):
    n=len(y); mask=np.ones(n,bool); mask[start:start+3]=False
    k=y[mask]; h=y[start:start+3];
    ret=k.sum(axis=0);truth=h.sum(axis=0)
    before=y[start-1] if start>0 else None
    after=y[start+3] if start+3<n else None
    if before is not None and after is not None:
        bridge=1.5*(before+after)
    elif before is not None: bridge=3*before
    elif after is not None: bridge=3*after
    else: raise RuntimeError('unexpected all-missing month')
    # Exactly the only day-of-gap information available from these array records is nothing.
    # The retained-day arithmetic and boundary interpolation use only unmasked readings.
    return (truth, ret,{
        'retained_no_fill':np.zeros(NARRAY),
        'retained_month_mean':3*np.mean(k,axis=0),
        'retained_month_median':3*np.median(k,axis=0),
        'boundary_linear_bridge':bridge,
    })

def main(src,out):
    m=upstream.read_months(src)
    assert len(m)==79 and upstream.BLOB=='5611277efdd581bb839ec380239846a43ebe0ba7'
    test=m[55:];assert len(test)==24
    count={k:collections.Counter() for k in METHODS}
    months=[];counterexample=[]
    for mo in test:
        y=np.asarray(mo['days'],float);n=len(y)
        assert y.shape[1]==NARRAY and (y>=0).all()
        ref=shortlist(y.sum(axis=0));c={k:collections.Counter() for k in METHODS}
        for start in range(n-2):
            hidden,ret,pred=trial(y,start)
            unchanged=shortlist(ret)
            for method in METHODS:
                computed=shortlist(ret+pred[method]);truth=(computed==ref)
                for d in [count[method],c[method]]:
                    d['cases']+=1; d['exact']+=int(truth.all())
                    d['false_inclusion']+=int(np.sum(computed&~ref))
                    d['false_exclusion']+=int(np.sum(~computed&ref))
                    d['membership_wrong']+=int(np.sum(~truth))
                    d['new_correct']+=int(truth.all() and not (unchanged==ref).all())
                    d['new_wrong']+=int((not truth.all()) and (unchanged==ref).all())
                    if method!='retained_no_fill':
                        d['sum_abs_error']+=float(np.abs(pred[method]-hidden).sum())
                        d['sum_hidden']+=float(hidden.sum())
                if method=='retained_month_mean':
                    assert np.array_equal(computed,unchanged),('monthly-mean rank changed',mo['month'],start)
            if (shortlist(ret+pred['boundary_linear_bridge'])==ref).all() != (unchanged==ref).all():
                counterexample.append({'month':mo['month'],'day':start+1,
                    'interpolation_correct':bool((shortlist(ret+pred['boundary_linear_bridge'])==ref).all()),
                    'unchanged_correct':bool((unchanged==ref).all())})
        months.append({'month':mo['month'],**{q:{'cases':v['cases'],'exact':v['exact'],'repaired':v['new_correct'],'damaged':v['new_wrong']} for q,v in c.items()}})
    assert all(count[k]['cases']==680 for k in METHODS)
    assert count['retained_no_fill']['exact']==513
    assert count['retained_month_mean']['exact']==513
    assert count['boundary_linear_bridge']['exact']==519
    assert count['boundary_linear_bridge']['new_correct']==61
    assert count['boundary_linear_bridge']['new_wrong']==55
    # DO NOT assert colleague median until verified; calculate and disclose what source produces.
    overall={k:{'cases':v['cases'],'exact':v['exact'],
          'accuracy_pct':100*v['exact']/v['cases'],'repaired':v['new_correct'],
          'damaged':v['new_wrong'],'false_inclusion':v['false_inclusion'],
          'false_exclusion':v['false_exclusion'],'membership_errors':v['membership_wrong'],
          'wape_pct':100*v['sum_abs_error']/v['sum_hidden'] if k!='retained_no_fill' else None}
          for k,v in count.items()}
    result={'state':'RESEARCH_ONLY_NO_MANUSCRIPT_MUTATION',
      'source_git_blob_sha1':upstream.BLOB,'method':'original 14-array common three-day masks',
      'source_qualified_months':79,'development_months':55,'later_previously_inspected_months':24,
      'independent_mask_placements':680,'statistically_dependent_windows':True,'q':Q,
      'methods':{
       'retained_no_fill':'Remove same 3 days from all 14 arrays and classify retained totals directly',
       'retained_month_mean':'3x mean retained-day output for each array; positive common-factor scaling of all retained monthly totals',
       'retained_month_median':'3x median retained-day output for each array',
       'boundary_linear_bridge':'3-day linear bridge between immediately available day before and day after; 3x single-sided boundary at calendar edges'},
      'overall':overall,'by_month':months,'changed_cases':counterexample,
      'limits':['Same candidate set for all methods; source-normalized summed samples, not physical kWh',
       'No hidden day values used to impute; hidden complete days used only for hindsight scoring',
       'Already inspected 24 months; overlapping placements are not independent',
       'Linear bridge may require post-gap day, so this is retrospective not at outage onset',
       'No natural-outage ground truth, no 13 peers survive in this common-loss scenario',
       'These point imputation methods do not bound true yields or certify decisions']}
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    (out/'R57_COMMON_GAP_REPLAY_DERIVED.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print('R57_COMMON_GAP_REPLAY_PASS',json.dumps(overall,sort_keys=True),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',default='R57_COMMON_GAP_DERIVED')
    a=p.parse_args();main(a.source,a.out)
