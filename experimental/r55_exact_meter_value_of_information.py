#!/usr/bin/env python3
"""Source-locked, research-only value-of-information experiment for MORE-EU.

No independent site-wide meter is asserted to exist. In the counterfactual
'exact total' arms, the hidden aggregate 3-day production T is read from the
original complete record as ORACLE information. Individual hidden array
values are never given to the membership rules, only to retrospective scoring.

The training min/max boxes are historical and not hard engineering limits.
The downstream conditional exactness requires both box and exact T to hold.
"""
from __future__ import annotations
import argparse,csv,json,random,time
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.optimize import linprog
import r55_pmedc_paired_bounds_original_source as parent

J=14; C=.95; EPS=1e-8

def box_total_classify(r,lo,hi,T,c=C,eps=EPS):
    """Exact universal/possible near-best membership over box intersect sum m_i=T."""
    n=len(r); total_lo=sum(lo);total_hi=sum(hi)
    assert total_lo-1e-6<=T<=total_hi+1e-6,(T,total_lo,total_hi)
    out=[]
    for j in range(n):
        # Robust inclusion via exact worst-case pairwise contrast.
        include=True
        for k in range(n):
            if k==j:continue
            lo_rest=total_lo-lo[j]-lo[k]
            hi_rest=total_hi-hi[j]-hi[k]
            mk_max=min(hi[k], T-lo_rest-lo[j])
            mj_min=max(lo[j],T-hi_rest-mk_max)
            assert lo[k]-1e-6<=mk_max<=hi[k]+1e-6
            assert lo[j]-1e-6<=mj_min<=hi[j]+1e-6
            rest=T-mk_max-mj_min
            assert lo_rest-1e-6<=rest<=hi_rest+1e-6,(rest,lo_rest,hi_rest)
            worst=(r[j]+mj_min)-c*(r[k]+mk_max)
            if worst < -eps:
                include=False
                break
        if include:
            out.append('I');continue
        # Potential inclusion: maximise j's hidden yield, then see whether
        # other candidates can absorb the remaining T below each challenger cap.
        other_lo=total_lo-lo[j]
        mj_max=min(hi[j],T-other_lo)
        rem=T-mj_max
        upper_sum=0.
        possible=mj_max>=lo[j]-eps
        for k in range(n):
            if k==j:continue
            rival_cap=(r[j]+mj_max)/c-r[k]
            kupper=min(hi[k],rival_cap)
            if kupper < lo[k]-eps:
                possible=False
            upper_sum+=kupper
        if rem>upper_sum+eps:possible=False
        if rem<other_lo-eps:possible=False
        out.append('?' if possible else 'E')
    return out

def oracle_total_no_box(r,T,c=C,eps=EPS):
    """Sharp status given only nonnegativity and exact total (same normalized units)."""
    n=len(r)
    ans=[]
    for j in range(n):
        mx=max(r[k] for k in range(n) if k!=j)
        if r[j]>=c*(mx+T)-eps:ans.append('I')
        elif r[j]+T < c*mx-eps:ans.append('E')
        else:ans.append('?')
    return ans

def stress_math_tests():
    """Independent numerical LP cross-validation of both exact tests."""
    rng=random.Random(54118)
    count=0
    for n in [3,4,5]:
        for _ in range(160):
            lo=[rng.uniform(0,2) for _ in range(n)]
            hi=[lo[i]+rng.uniform(.2,3) for i in range(n)]
            truth=[rng.uniform(lo[i],hi[i]) for i in range(n)]
            T=sum(truth)
            r=[rng.uniform(0,6) for _ in range(n)]
            ours=box_total_classify(r,lo,hi,T)
            for j in range(n):
                # Guaranteed inclusion: every pair's *minimum* margin nonnegative.
                incl=True
                for k in range(n):
                    if j==k:continue
                    coeff=np.zeros(n);coeff[j]=1;coeff[k]=-C
                    res=linprog(coeff,A_eq=[np.ones(n)],b_eq=[T],bounds=list(zip(lo,hi)),method='highs')
                    assert res.success,res.message
                    if (r[j]-C*r[k])+res.fun < -EPS:incl=False
                # Possible inclusion: system A x<=b with all j-vs-k inequalities.
                A=[];b=[]
                for k in range(n):
                    if j==k:continue
                    row=np.zeros(n);row[j]=-1;row[k]=C
                    A.append(row);b.append(r[j]-C*r[k])
                f=linprog(np.zeros(n),A_ub=A,b_ub=b,A_eq=[np.ones(n)],b_eq=[T],bounds=list(zip(lo,hi)),method='highs')
                expected='I' if incl else ('?' if f.success else 'E')
                assert expected==ours[j],(n,j,r,lo,hi,T,expected,ours[j])
                count+=1
    return count

def run(source,out):
    tests=stress_math_tests()
    months=parent.read_months(source)
    assert len(months)==79
    lo,hi,pairlo,pairhi=parent.make_bounds(months[:55])
    totals=Counter();detailed=[];monthly=[];first_cases=[]
    for month in months[55:]:
        d=month['days'];n=len(d)
        full=[sum(day[j] for day in d) for j in range(J)]
        fullset={j for j,x in enumerate(full) if x>=C*max(full)-parent.EPS}
        monthstats=Counter()
        for s,hidden in parent.block_vectors(month):
            T=sum(hidden)
            ret=[full[j]-hidden[j] for j in range(J)]
            truth=[int(j in fullset) for j in range(J)]
            box=parent.classify(ret,lo,hi,pairlo,pairhi,'independent')
            pair=parent.classify(ret,lo,hi,pairlo,pairhi,'paired')
            total_only=oracle_total_no_box(ret,T)
            box_total=box_total_classify(ret,lo,hi,T)
            assert all(lo[j]-1e-7<=hidden[j]<=hi[j]+1e-7 for j in range(J))
            assert sum(z!='?' for z in box_total)>=sum(z!='?' for z in box)
            paircover=all(pairlo[j][k]-1e-7<=hidden[j]-C*hidden[k]<=pairhi[j][k]+1e-7 for j in range(J) for k in range(J))
            totals['windows']+=1
            totals['pair_joint_covered']+=int(paircover)
            for model,model_status in [('box',box),('pair',pair),('total_only',total_only),('box_plus_exact_total',box_total)]:
                decided=sum(z!='?' for z in model_status)
                wrong=sum(z!='?' and (z=='I')!=bool(truth[j]) for j,z in enumerate(model_status))
                totals[model+'_decided']+=decided
                totals[model+'_wrong']+=wrong
                totals[model+'_inclusions']+=model_status.count('I')
                totals[model+'_exclusions']+=model_status.count('E')
                totals[model+'_full_lists']+=int(decided==J)
                monthstats[model+'_decided']+=decided
                if wrong and len(first_cases)<8:first_cases.append({'model':model,'month':month['month'],'gap_start':s,'wrong':wrong,'T_oracle':T})
            for j in range(J):
                detailed.append([month['month'],s,j+1,truth[j],box[j],pair[j],total_only[j],box_total[j],int(paircover)])
        monthly.append({'month':month['month'],**dict(monthstats)})
    assert totals['windows']==680,totals
    assert totals['pair_joint_covered']==419,totals
    assert totals['box_decided']==375,totals
    assert totals['pair_decided']==1128,totals
    assert totals['pair_wrong']==1,totals
    assert totals['total_only_wrong']==0 and totals['box_plus_exact_total_wrong']==0
    assert len(detailed)==9520
    result={
        'run_type':'RESEARCH_ONLY_COUNTERFACTUAL_NOT_MANUSCRIPT_DATA',
        'pinned_source_git_blob':parent.BLOB,
        'historical_split':'55 development months; 24 later months (previously inspected cohort)',
        'development_windows':1557,'test_windows':680,'test_candidate_labels':9520,
        'tests':'Independent random LP oracle checks of exact scalar-budget formulas',
        'number_of_lp_math_crosschecks':tests,
        'models':{
           'box':'Historical per-array min/max without extra meter: observed data plus development envelope',
           'pair':'Historical paired-contrast min/max without extra meter: excludes some actual test vectors',
           'total_only':'Ideal independent exact aggregate three-day production T; no candidate bounds',
           'box_plus_exact_total':'Ideal independent exact aggregate three-day production T AND historical per-array box',
        },
        'counts':dict(totals),
        'counterexample_cases':first_cases,
        'unavoidable_limits':[
           'T is read from intentionally hidden original output solely to model a hypothetical independent meter; that meter is not observed in MORE-EU',
           'Historical min/max envelopes are empirically admitted only, never hard physical maxima',
           'Same-month overlapping gap windows and candidate decisions are statistically dependent',
           'No confidence interval, causal benefit, actual fault detection, operational guarantee, or full-source replay beyond MORE-EU is claimed',
           'All results are post hoc on original test months analysed in the past'],
        'raw_telemetry_redistributed':False}
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'EXACT_METER_VALUE_OF_INFORMATION_RESEARCH_ONLY.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    (out/'MONTHLY_MODEL_AGGREGATES_DERIVED_ONLY.json').write_text(json.dumps(monthly,indent=2),encoding='utf8')
    with (out/'CANDIDATE_LABELS_DERIVED_ONLY.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.writer(f);w.writerow(['month','start_day','array_id','full_reference_in','box','paired','oracle_total_only','box_plus_oracle_total','paired_all_constraints_covered']);w.writerows(detailed)
    print('R55_EXACT_METER_RESEARCH_ONLY_PASS',json.dumps({'counts':dict(totals),'lp_crosschecks':tests},sort_keys=True),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',default='R55_EXACT_METER_GATE')
    a=ap.parse_args();run(a.source,a.out)
