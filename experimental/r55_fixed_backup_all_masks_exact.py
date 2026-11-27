#!/usr/bin/env python3
"""RESEARCH ONLY, source-locked optimal fixed backup per-array counter placement.

This is a counterfactual upper-bound engineering test, not proof that any such
independent counters exist. For arrays supplied with hypothetical perfect
independent three-day output, their missing values are treated as known;
remaining arrays retain development historical min/max boxes.
The installed counter positions are selected using the 55 development months
only and held constant over the last 24 previously studied months.
No original licensed telemetry is redistributed.
"""
import argparse, csv, json, itertools, math
from pathlib import Path
from collections import Counter
import numpy as np
import r55_pmedc_paired_bounds_original_source as original

J=14;C=.95;EPS=1e-10
K_CHOICES=tuple(range(J+1))

def masks_of_sizes(choices=K_CHOICES):
    return [(k,sum(1<<i for i in inds)) for k in choices for inds in itertools.combinations(range(J),k)]

def classify_masks(ret,hidden,lo,hi,bits):
    """Exact box robust statuses vectorized across mask rows.

    return certified bool array MxJ, included bool array MxJ,
    excluded bool array MxJ. Pairwise maxima *exclude self*.
    """
    M=len(bits)
    lower=np.where(bits,hidden,lo)+ret
    upper=np.where(bits,hidden,hi)+ret
    ix=np.arange(M)
    topi=np.argmax(upper,axis=1)
    max1=upper[ix,topi]
    tmp=upper.copy();tmp[ix,topi]=-np.inf
    max2=np.max(tmp,axis=1)
    comp_upper=np.where(np.arange(J)[None,:]==topi[:,None],max2[:,None],max1[:,None])
    li=np.argmax(lower,axis=1)
    lmax1=lower[ix,li]
    tmp=lower.copy();tmp[ix,li]=-np.inf
    lmax2=np.max(tmp,axis=1)
    comp_lower=np.where(np.arange(J)[None,:]==li[:,None],lmax2[:,None],lmax1[:,None])
    incl=lower>=C*comp_upper-EPS
    excl=upper<C*comp_lower-EPS
    assert not np.any(incl&excl)
    return incl|excl,incl,excl

def self_tests():
    import random
    rng=random.Random(202612)
    for n in range(100):
        jn=J
        r=np.array([rng.random()*100 for _ in range(jn)])
        lo=np.array([rng.random()*2 for _ in range(jn)])
        hi=lo+np.array([rng.random()*10 for _ in range(jn)])
        m=np.array([rng.uniform(lo[j],hi[j]) for j in range(jn)])
        qmask=np.array([[(i in rng.sample(range(jn),rng.randrange(jn+1))) for i in range(jn)] for _ in range(3)],dtype=bool)
        # construct deterministic random masks for test
        qmask=np.zeros((3,jn),dtype=bool)
        for t in range(3):
            for j in range(jn):qmask[t,j]=rng.random()<.5
        cert,inc,exc=classify_masks(r,m,lo,hi,qmask)
        true=np.array([r[j]+m[j]>=C*max(r+m)-EPS for j in range(jn)])
        assert np.all(inc<=true) and np.all(exc<=~true), 'unsound box certificate'
        for ii in range(3):
            l=np.where(qmask[ii],m,lo);u=np.where(qmask[ii],m,hi)
            for j in range(jn):
                ai=all(r[j]+l[j]>=C*(r[k]+u[k])-EPS for k in range(jn) if k!=j)
                ae=any(r[j]+u[j]<C*(r[k]+l[k])-EPS for k in range(jn) if k!=j)
                assert ai==inc[ii,j] and ae==exc[ii,j],(j,ai,ae,inc[ii,j],exc[ii,j])
    return True

def run(source,out):
    assert self_tests()
    months=original.read_months(source)
    lo,hi,_,_=original.make_bounds(months[:55]);lo=np.array(lo);hi=np.array(hi)
    choices=masks_of_sizes()
    masks=np.array([mk for _,mk in choices],dtype=np.uint16)
    bits=((masks[:,None]>>np.arange(J)[None,:])&1).astype(bool)
    print('CANDIDATE_FIXED_BACKUP_CONFIGS',len(masks),'TRAIN_MONTHS',55,flush=True)
    meta=np.array([k for k,_ in choices]);uniq={k:np.where(meta==k)[0] for k in K_CHOICES}
    train_full=np.zeros(len(masks),dtype=np.int64)
    train_labels=np.zeros(len(masks),dtype=np.int64)
    trainwins=0
    for month_index,month in enumerate(months[:55]):
        days=month['days'];full=np.sum(np.array(days),axis=0)
        for s,hidden in original.block_vectors(month):
            hidden=np.array(hidden)
            ret=full-hidden
            cert,inc,exc=classify_masks(ret,hidden,lo,hi,bits)
            n=cert.sum(axis=1)
            train_labels+=n
            train_full+=(n==J)
            trainwins+=1
        if month_index in (0,9,19,29,39,49,54):print('DEV_MONTHS_PROCESSED',month_index+1,flush=True)
    assert trainwins==1557,trainwins
    # Prespecified lexicographic objective: full-list certificates first; total
    # resolved candidate memberships next; lower mask identifier for ties.
    selected=[]
    for k in K_CHOICES:
        ind=uniq[k]
        best=sorted(ind,key=lambda i:(-train_full[i],-train_labels[i],int(masks[i])))[0]
        selected.append((k,int(masks[best]),int(best)))
    selected_rows=[]
    teststatus={k:Counter() for k in K_CHOICES}
    testwins=0
    for month in months[55:]:
        full=np.sum(np.array(month['days']),axis=0)
        month_fullset=full>=C*full.max()-EPS
        fixed_bits=bits[[best for _,_,best in selected]]
        for s,hid in original.block_vectors(month):
            hidden=np.array(hid);ret=full-hidden
            assert np.all((hidden>=lo-1e-7)&(hidden<=hi+1e-7))
            cert,inc,exc=classify_masks(ret,hidden,lo,hi,fixed_bits)
            assert np.all(inc<=month_fullset) and np.all(exc<=~month_fullset)
            for i,(k,m,best) in enumerate(selected):
                decided=int(cert[i].sum())
                st=teststatus[k]
                st['test_windows']+=1;st['decided_memberships']+=decided
                st['inclusions']+=int(inc[i].sum());st['exclusions']+=int(exc[i].sum())
                st['fully_certified']+=int(decided==J)
                st['any_decision']+=int(decided>0)
                st['changed_window']+=int(set(np.where(month_fullset)[0])!=set(np.where(ret>=C*ret.max()-EPS)[0]))
                st['invalid_certifications']+=int(np.any(inc[i]&~month_fullset)|np.any(exc[i]&month_fullset))
                selected_rows.append([k,m,month['month'],s,decided,int(decided==J),int(inc[i].sum()),int(exc[i].sum())])
            testwins+=1
    assert testwins==680
    assert teststatus[0]['decided_memberships']==375
    assert teststatus[0]['fully_certified']==0
    assert teststatus[14]['decided_memberships']==9520
    assert teststatus[14]['fully_certified']==680
    assert not any(st['invalid_certifications'] for st in teststatus.values())
    outputs=[]
    for k,m,best in selected:
        st=teststatus[k]
        outputs.append({'independent_backup_counter_count':k,
            'development_selected_array_ids':[j+1 for j in range(J) if (m>>j)&1],
            'development_fully_certified_windows':int(train_full[best]),
            'development_decided_memberships':int(train_labels[best]),
            'test_counts':dict(st),
            'test_full_list_fraction':st['fully_certified']/680,
            'test_candidate_decision_fraction':st['decided_memberships']/(680*J),
            'test_invalid_decisions':int(st['invalid_certifications'])})
    report={'state':'RESEARCH_ONLY_COUNTERFACTUAL_FIXED_SENSOR_DESIGN',
        'source_git_blob_sha1':original.BLOB,'development_windows':trainwins,'test_windows':testwins,
        'source_arrays':J,'models':'perfect hypothetical per-array backup readings; no such devices independently verified',
        'optimization':'fixed subset chosen on first 55 months by (full shortlist count, resolved members, lexicographic IDs); tested on final 24 already previously studied months',
        'candidate_subsets_tested_in_development':len(masks),
        'witness_test':'all test hidden values within development boxes; 0 invalid certificate labels conditional on box',
        'outputs':outputs,'licence':'Only derived aggregates; never distribute original telemetry',
        'limitations':['Purely counterfactual measurements: source does not establish independent backup meters or wiring','Historical min/max bounds are not hard future guarantees','Selected arrays fixed across months, but study cohort is post hoc and months share a plant','Optimality is within each prespecified fixed budget k, not economic optimality','Array counts are not procurement costs']}
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    (out/'FIXED_BACKUP_COUNTER_RESEARCH_ONLY.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    with (out/'TEST_SELECTED_SUBSET_OUTCOMES_DERIVED_ONLY.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow(['backup_count','mask','month','start_day','certified_memberships','fully_certified','included','excluded']);w.writerows(selected_rows)
    print('R55_FIXED_BACKUP_ORIGINAL_SOURCE_PASS',json.dumps({'groups':outputs,'configuration_count':len(masks)},sort_keys=True),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',default='R55_FIXED_BACKUP_OUTPUTS')
    args=ap.parse_args();run(args.source,args.out)
