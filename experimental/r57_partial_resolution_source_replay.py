#!/usr/bin/env python3
"""R57 original MORE-EU source-locked engineering partial-resolution / false-decision audit.

Research only: retrospective source-month envelopes are not hard physical bounds.
Only derived numerical summaries are released, not original telemetry.
Requires r55_pmedc_paired_bounds_original_source.py and r55_single_array_peer_prediction.py.
"""
import argparse, csv, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import r55_pmedc_paired_bounds_original_source as src
import r55_single_array_peer_prediction as peer

J=14; Q=.05; C=1-Q; EPS=1e-9
LABELS=('monthly_max_90pct','development_max')

def statuses(pred_full, target, radius):
    lo=np.asarray(pred_full,float).copy(); hi=lo.copy()
    lo[target]=max(0.,lo[target]-radius)
    hi[target]=hi[target]+radius
    ans=[]
    for j in range(J):
        rivals=[k for k in range(J) if k!=j]
        if lo[j]>=C*max(hi[k] for k in rivals)-EPS:ans.append('I')
        elif hi[j]<C*max(lo[k] for k in rivals)-EPS:ans.append('E')
        else:ans.append('?')
    return ans

def classify(totals):
    v=np.asarray(totals,float)
    return v>=C*v.max()-EPS

def test_logic():
    import itertools
    rng=np.random.default_rng(127026)
    for _ in range(150):
        lo=rng.uniform(0,30,3); hi=lo+rng.uniform(0,20,3)
        for q in range(3):
            corner=np.array(list(itertools.product(*zip(lo,hi))))
            truths=corner>=C*np.max(corner,axis=1)[:,None]-EPS
            assert (lo[q]>=C*max(hi[k] for k in range(3) if k!=q)-EPS)==np.all(truths[:,q])
            assert (hi[q]<C*max(lo[k] for k in range(3) if k!=q)-EPS)==np.all(~truths[:,q])
    assert list(classify([100,95]+[0]*12))[:2]==[True,True]
    return True

def count_missing_reason(y,s,j):
    n=len(y);p=np.delete(y,j,axis=1).mean(axis=1)
    left=s>0 and p[s-1]>0
    right=(s+3<n) and p[s+3]>0
    if left or right:return 'available'
    if s==0:return 'start_edge_no_usable_after'
    if s+3==n:return 'end_edge_no_usable_before'
    return 'both_adjacent_peer_denominators_zero'

def emit_csv(path,fields,rows):
    with open(path,'w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def run(source,outdir):
    assert test_logic()
    m=src.read_months(source)
    assert len(m)==79 and src.BLOB=='5611277efdd581bb839ec380239846a43ebe0ba7'
    dev,test=m[:55],m[55:]
    devmax=np.zeros(J); monthly_mx=[]
    dev_missing=Counter();dev_eligible=Counter();missing_reasons=Counter();miss_by_month=Counter()
    for mt in dev:
        v=np.asarray(mt['days'],float);current=np.zeros(J)
        for s in range(len(v)-2):
            for j in range(J):
                d=peer.evaluate_models(v,s,j,np.ones(J))
                pred=d.get('peer_boundary_ratio')
                if pred is None:
                    dev_missing[j]+=1;miss_by_month[mt['month']]+=1
                    missing_reasons[count_missing_reason(v,s,j)]+=1
                    continue
                dev_eligible[j]+=1
                hidden=float(v[s:s+3,j].sum())
                current[j]=max(current[j],abs(pred-hidden))
        devmax=np.maximum(devmax,current);monthly_mx.append(current)
    assert sum(dev_missing.values())==196,(sum(dev_missing.values()),dict(missing_reasons))
    monthly_mx=np.stack(monthly_mx);assert monthly_mx.shape==(55,J)
    def higher(v,p):return np.sort(v,axis=0)[max(0,min(len(v)-1,math.ceil(p*len(v))-1))]
    bands={'development_max':devmax,'monthly_max_90pct':higher(monthly_mx,.90)}
    all_stats={b:Counter() for b in LABELS}
    by_masked={b:{j:Counter() for j in range(J)} for b in LABELS}
    by_month={b:{month['month']:Counter() for month in test} for b in LABELS}
    wrong_full=[]; test_missing=Counter();test_reason=Counter();reference_count=Counter()
    # Same-day shared-gap endpoint is computed per unique month/start, NOT as a natural single-target scenario.
    for mt in test:
        v=np.asarray(mt['days'],float);full=v.sum(axis=0);truth=classify(full)
        n=len(v)
        for s in range(n-2):
            block=v[s:s+3,:].sum(axis=0)
            common=classify(full-block)
            reference_count['unique_common_day_windows']+=1
            reference_count['common_day_correct']+=int(np.array_equal(common,truth))
            for j in range(J):
                known=full.copy();known[j]-=block[j]
                z=peer.evaluate_models(v,s,j,np.ones(J)).get('peer_boundary_ratio')
                if z is None:
                    test_missing[j]+=1;test_reason[count_missing_reason(v,s,j)]+=1
                    continue
                point=known.copy();point[j]+=z
                point_truth=classify(point)
                reference_count['single_target_masks']+=1
                reference_count['peer_point_correct']+=int(np.array_equal(point_truth,truth))
                reference_count['zero_target_correct']+=int(np.array_equal(classify(known),truth))
                reference_count['common_day_comparator_repeated_correct']+=int(np.array_equal(common,truth))
                for b in LABELS:
                    a=all_stats[b]; t=by_masked[b][j];mon=by_month[b][mt['month']]
                    radius=float(bands[b][j]); st=statuses(point,j,radius)
                    resolved=[k for k in range(J) if st[k]!='?']
                    wrong=[k for k in resolved if (st[k]=='I')!=bool(truth[k])]
                    fi=[k for k in wrong if st[k]=='I']
                    fe=[k for k in wrong if st[k]=='E']
                    if len(wrong)>0 and abs(z-block[j])<=radius+EPS:
                        raise AssertionError('False conclusion despite contained true total')
                    full_resolved=len(resolved)==J
                    coverage=abs(z-block[j])<=radius+EPS
                    value={
                     'cases':1,'fully_resolved':int(full_resolved),
                     'resolved_wrong':int(full_resolved and bool(wrong)),
                     'unresolved_full':int(not full_resolved),
                     'resolved_labels':len(resolved), 'unresolved_labels':J-len(resolved),
                     'false_inclusion_labels':len(fi),'false_exclusion_labels':len(fe),
                     'wrong_labels':len(wrong), 'interval_covers_hidden':int(coverage),
                     'full_resolved_outside':int(full_resolved and not coverage),
                     'target_membership_resolved':int(st[j]!='?'),
                     'target_membership_wrong':int(j in wrong),
                     'other_membership_wrong':int(sum(k!=j for k in wrong)),
                     'target_false_inclusion':int(j in fi), 'target_false_exclusion':int(j in fe),
                     'point_full_correct':int(np.array_equal(point_truth,truth))
                    }
                    for name,vv in value.items():a[name]+=vv;t[name]+=vv;mon[name]+=vv
                    if full_resolved and wrong:
                        wrong_full.append({
                          'envelope':b,'month':mt['month'],'gap_start_day':s+1,'masked_array':j+1,
                          'predicted_gap_abs_error':round(abs(z-block[j]),6),
                          'historical_error_radius':round(radius,6),
                          'true_gap_outside_interval':not coverage,
                          'wrong_included_array_ids':','.join(str(k+1) for k in fi) or '-',
                          'wrong_excluded_array_ids':','.join(str(k+1) for k in fe) or '-',
                          'error_on_masked_array':bool(j in wrong),
                          'error_on_other_array':bool(any(k!=j for k in wrong)),
                          'number_of_wrong_memberships':len(wrong)
                        })
    assert not test_missing,(test_missing,test_reason)
    assert reference_count['single_target_masks']==9520
    assert reference_count['unique_common_day_windows']==680
    assert reference_count['common_day_correct']==513
    assert reference_count['peer_point_correct']==9145
    assert reference_count['zero_target_correct']==2444
    assert reference_count['common_day_comparator_repeated_correct']==7182
    assert all_stats['development_max']['fully_resolved']==422
    assert all_stats['monthly_max_90pct']['fully_resolved']==2084
    assert all_stats['development_max']['resolved_labels']==35696
    assert all_stats['monthly_max_90pct']['resolved_labels']==110515
    assert all_stats['monthly_max_90pct']['resolved_wrong']==10
    assert all_stats['monthly_max_90pct']['wrong_labels']==27
    assert len(wrong_full)==10
    assert all(v['true_gap_outside_interval'] for v in wrong_full)
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    env_rows=[]
    for j in range(J):
        row={'array_id':j+1,'development_max':round(float(devmax[j]),6),
         'development_p90_monthlymax':round(float(bands['monthly_max_90pct'][j]),6),
         'development_available_masks':int(dev_eligible[j]),'development_excluded_masks':int(dev_missing[j])}
        for b in LABELS:
            s=by_masked[b][j]
            for k in ('cases','interval_covers_hidden','fully_resolved','resolved_wrong','resolved_labels','unresolved_labels','target_membership_resolved','target_membership_wrong','false_inclusion_labels','false_exclusion_labels','wrong_labels'):
                row[b+'_'+k]=s[k]
        env_rows.append(row)
    emit_csv(out/'R57_ARRAY_BOUND_AND_PARTIAL_RESOLUTION_DERIVED.csv',list(env_rows[0]),env_rows)
    month_rows=[]
    for b in LABELS:
        for month,st in sorted(by_month[b].items()):
            mrow={'envelope':b,'month':month}
            for field in ('cases','fully_resolved','resolved_wrong','unresolved_full','resolved_labels','wrong_labels','false_inclusion_labels','false_exclusion_labels','interval_covers_hidden','target_membership_resolved','target_membership_wrong'):
                mrow[field]=st[field]
            mrow['full_resolution_percent']=round(100*st['fully_resolved']/st['cases'],4)
            mrow['candidate_resolution_percent']=round(100*st['resolved_labels']/(J*st['cases']),4)
            mrow['selective_full_error_percent']=round(100*st['resolved_wrong']/st['fully_resolved'],4) if st['fully_resolved'] else None
            month_rows.append(mrow)
    emit_csv(out/'R57_MONTHLY_GATE_PERFORMANCE_DERIVED.csv',list(month_rows[0]),month_rows)
    emit_csv(out/'R57_TEN_WRONG_FULL_RESOLUTIONS_DERIVED.csv',list(wrong_full[0]),wrong_full)
    result={
      'state':'R57_RESEARCH_ONLY_CONDITIONAL_NOT_FIELD_CERTIFICATION',
      'source_sha1':src.BLOB,'months_development':55,'months_test_previously_inspected':24,
      'comparison_margin_q':Q,'masked_single_array_cases':9520,
      'common_day_unique_windows':680,
      'peer_estimator':'Same as R55/R56 boundary ratio, may require right boundary after outage; retrospective only',
      'envelopes':{k:[float(x) for x in bands[k]] for k in LABELS},
      'development_excluded_masks':sum(dev_missing.values()),'development_missing_by_month':dict(miss_by_month),
      'development_missing_reasons':dict(missing_reasons),
      'test_missing_reasons':dict(test_reason),
      'reference_comparison':dict(reference_count),
      'aggregate_by_envelope':{k:dict(v) for k,v in all_stats.items()},
      'source_results_consistency':'R56 complete-list and label counts asserted exactly',
      'wrong_full_case_count':len(wrong_full),
      'limits':['The assumed envelope is an empirical historical error band, not a physical or calibrated coverage guarantee',
        'The exact Cartesian-box inequalities do not assume statistical independence, but treat the full interval product as admissible',
        'All 14 candidate membership decisions within the same mask are dependent, as are overlapping 3-day windows',
        'Common-day comparator hides all 14 streams, unlike the single-target reconstruction; compare as a distinct missingness option',
        'More detailed grid data are retained only as derived diagnostics, not original licensed source rows',
        'No independently valid actual outage ground truth, no operational alarm or maintenance action, no kWh conversion',
        'Cross-site R57 partial-resolution transfer is not executed or claimed'],
      'files':['R57_ARRAY_BOUND_AND_PARTIAL_RESOLUTION_DERIVED.csv','R57_MONTHLY_GATE_PERFORMANCE_DERIVED.csv','R57_TEN_WRONG_FULL_RESOLUTIONS_DERIVED.csv']
    }
    (out/'R57_PARTIAL_GATE_AUDIT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('R57_PARTIAL_RESOLUTION_SOURCE_REPLAY_PASS',json.dumps({'aggregate':result['aggregate_by_envelope'],'reference':dict(reference_count),'wrong_cases':len(wrong_full),'dev_missing_reasons':dict(missing_reasons)}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',default='R57_DERIVED_ONLY')
    x=p.parse_args();run(x.source,x.out)
