#!/usr/bin/env python3
"""Source-locked research-only exact polyhedral selection-membership feasibility.
No engineering certification: historical bounds are not guaranteed for future days.
No edits to the author-approved Solar manuscript or redistribution of telemetry.
"""
import argparse,csv,json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
import r55_pmedc_paired_bounds_original_source as orig

C=.95; J=14; EPS=1e-9

def pair_Ab(lo,hi,pairlo,pairhi):
    A=[]; b=[]
    for j in range(len(lo)):
      for k in range(len(lo)):
        if j==k: continue
        a=np.zeros(len(lo));a[j]=1.;a[k]=-C
        A.append(a);b.append(pairhi[j][k])
        A.append(-a);b.append(-pairlo[j][k])
    return np.array(A),np.array(b)

def can_include(r,j,lo,hi,A,b,extra_eq=None,extra_b=None):
    n=len(r)
    B=[];bound=[]
    for k in range(n):
        if k==j:continue
        a=np.zeros(n);a[j]=-1.;a[k]=C
        B.append(a);bound.append(r[j]-C*r[k])
    AA=np.concatenate((A,np.array(B)),axis=0)
    bb=np.concatenate((b,np.array(bound)))
    res=linprog(np.zeros(n),A_ub=AA,b_ub=bb,bounds=list(zip(lo,hi)),A_eq=extra_eq,b_eq=extra_b,method='highs')
    if res.status not in [0,2]:raise RuntimeError(('LP solver status not supported',res.status,res.message))
    return res.status==0

def synthetic_test():
    # j=0 has zero yield, competitors' joint total is exactly 1.
    # Every feasible state excludes j but no one fixed rival beats it always.
    lo=[0.,0.,0.];hi=[0.,1.,1.]
    A=np.empty((0,3));b=np.empty(0)
    r=[0.,0.,0.]
    poss=can_include(r,0,lo,hi,A,b,extra_eq=[[0.,1.,1.]],extra_b=[1.])
    assert not poss
    return True

def run(source,out):
    assert synthetic_test()
    months=orig.read_months(source)
    lo,hi,pl,ph=orig.make_bounds(months[:55])
    A,b=pair_Ab(lo,hi,pl,ph)
    Ufeas=linprog(np.zeros(J),A_ub=A,b_ub=b,bounds=list(zip(lo,hi)),method='highs')
    assert Ufeas.success,Ufeas.message
    counts=Counter();records=[];month_logs=[]
    for mi,month in enumerate(months[55:]):
        full=[sum(v[j] for v in month['days']) for j in range(J)]
        truth=[int(v>=C*max(full)-orig.EPS) for v in full]
        ms=Counter()
        for s,hidden in orig.block_vectors(month):
            retained=[full[j]-hidden[j] for j in range(J)]
            old=orig.classify(retained,lo,hi,pl,ph,'paired')
            nold=sum(v!='?' for v in old)
            newer=old[:]
            for j in range(J):
                if old[j]!='?':continue
                if not can_include(retained,j,lo,hi,A,b):newer[j]='E'
            assert all((z!='?' or v=='?') for z,v in zip(newer,old))
            assert sum(z!='?' for z in newer)>=nold
            counts['scenarios']+=1
            counts['old_decided']+=nold
            counts['exact_decided']+=sum(v!='?' for v in newer)
            counts['extra_adaptive_rival_exclusions']+=sum(a=='?' and v=='E' for a,v in zip(old,newer))
            counts['exact_full_lists']+=int(all(v!='?' for v in newer))
            old_err=sum(v!='?' and ((v=='I')!=bool(truth[j])) for j,v in enumerate(old))
            newer_err=sum(v!='?' and ((v=='I')!=bool(truth[j])) for j,v in enumerate(newer))
            counts['old_wrong']+=old_err;counts['exact_wrong']+=newer_err
            counts['old_inclusion']+=old.count('I');counts['exact_inclusion']+=newer.count('I')
            counts['old_exclusion']+=old.count('E');counts['exact_exclusion']+=newer.count('E')
            ms['extra_adaptive_rival_exclusions']+=sum(a=='?' and v=='E' for a,v in zip(old,newer))
            ms['exact_decided']+=sum(v!='?' for v in newer)
            for j in range(J):records.append([month['month'],s,j+1,truth[j],old[j],newer[j]])
        month_logs.append({'month':month['month'],**dict(ms)})
        print('FINISHED_TEST_MONTH',mi+1,month['month'],'extra',ms['extra_adaptive_rival_exclusions'],flush=True)
    assert counts['scenarios']==680
    assert counts['old_decided']==1128 and counts['old_wrong']==1
    assert len(records)==9520
    result={'state':'RESEARCH_ONLY_EXACT_JOINT_POLYTOPE_NOT_OPERATIONAL_VALIDATION',
            'source_sha1':orig.BLOB,
            'U_definition':'box bounds AND ALL development pairwise contrast inequalities; includes training vectors but not all held-out vectors',
            'algorithm':'Necessary and sufficient candidate possibility by LP feasibility of joint inequalities; inclusion by minimum pairwise margins',
            'synthetic_no_fixed_rival_exclusion_test':'PASS',
            'counts':dict(counts),
            'limits':['The polytope includes all dev prototype blocks but not all later test blocks','No independent physically justified uncertainty set is claimed','All candidate decisions in a month share dependent observations','Model decisions are not true fault diagnoses','Main Solar manuscript and previous results untouched'],
            'redistribution_of_original_telemetry':False}
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    (out/'EXACT_COUPLED_POLYTOPE_RESEARCH_ONLY.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    (out/'EXACT_COUPLED_POLYTOPE_MONTHS.json').write_text(json.dumps(month_logs,indent=2),encoding='utf8')
    with (out/'EXACT_COUPLED_POLYTOPE_DERIVED_ONLY.csv').open('w',newline='',encoding='utf8') as f:
        wr=csv.writer(f);wr.writerow(['month','gap_start_day','array','true_membership','fixed_rival_status','exact_joint_status']);wr.writerows(records)
    print('R55_EXACT_COUPLED_POLYTOPE_PASS',json.dumps(dict(counts),sort_keys=True),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',default='R55_EXACT_POLYTOPE_OUTPUTS');a=p.parse_args();run(a.source,a.out)
