"""R62 research-only. Nonnegative missing daily records; exact retrieval or HOLD.
No assumed physical upper bounds, no historical radii, no raw data export.
One, two and three targets with the same three-day mask. All-zero initial states held.
Offline optimum is hindsight only; practical orders see only observed records.
"""
import argparse, itertools, math, json
from collections import Counter
from pathlib import Path
import numpy as np
C=.95
EPS=1e-9
POLICIES=['calendar_day_first','array_id_first','low_retained_first','high_retained_first','low_retained_peer_day_first']

def rivals(x):
    j=np.argmax(x,axis=1)
    y=x.copy()
    y[np.arange(len(x)),j]=-np.inf
    m=np.broadcast_to(np.max(x,axis=1)[:,None],x.shape).copy()
    m[np.arange(len(x)),j]=np.max(y,axis=1)
    return m

def classify(x):
    return x>=C*np.max(x,axis=1)[:,None]-EPS

def label(lo,hi):
    inc=lo>=C*rivals(hi)-EPS
    out=hi<C*rivals(lo)-EPS
    assert not np.any(inc&out)
    return np.where(inc,1,np.where(out,-1,0))

def state(lo,rem):
    return label(lo,np.where(rem>0,np.inf,lo))

def threshold(a,b,strict=False):
    a,b=np.broadcast_arrays(a,b)
    result=np.empty(a.shape,float)
    np.divide(a,b,out=result,where=b>0)
    result=np.where(b>0,result,np.where((a>0) if strict else (a>=0),np.inf,-np.inf))
    return result

def precision(A,Y,mask,truth):
    """Sharp sup of common aggregate radius on restored targets, originally observed values exact.
    [max(A,Y-r*mask),Y+r*mask]. A per-record r/3 bound suffices by triangle inequality.
    """
    y=Y[:,:,None]; z=Y[:,None,:]; a=A[:,:,None]; b=A[:,None,:]
    i=mask[:,:,None].astype(float); k=mask[:,None,:].astype(float)
    t_in=np.maximum(threshold(y-C*z+EPS,i+C*k),threshold(a-C*z+EPS,C*k))
    t_out=np.maximum(threshold(C*z-y-EPS,i+C*k,True),threshold(C*b-y-EPS,i,True))
    diag=np.eye(Y.shape[1],dtype=bool)[None,:,:]
    t_in=np.min(np.where(diag,np.inf,t_in),axis=2)
    t_out=np.max(np.where(diag,-np.inf,t_out),axis=2)
    per=np.where(truth,t_in,t_out)
    assert np.all(per>=-1e-7)
    per=np.maximum(per,0)
    r=np.min(per,axis=1)
    strict=np.any((~truth)&(per==r[:,None]),axis=1)&np.isfinite(r)
    # Just below/above the limiting radius, independent label evaluation.
    f=np.isfinite(r)
    if f.any():
        Af,Yf,mf,tf,rf=A[f],Y[f],mask[f],truth[f],r[f]
        step=np.maximum(1e-7,np.abs(rf)*1e-7)
        for sign in [-1,1]:
            rr=np.maximum(0,rf+sign*step)[:,None]
            ll=np.maximum(Af,Yf-rr*mf);uu=Yf+rr*mf
            st=label(ll,uu)
            same=np.all(st==np.where(tf,1,-1),axis=1)
            assert np.all(same) if sign==-1 else not np.any(same)
    return r,strict,per

def oracle(A,Y,H,js,truth):
    """Return exact minimum # retrieved records and exact random-order stopping CDF.
    At most one incomplete candidate can remain; it must be the unique true shortlist member.
    """
    n,J=A.shape; k=js.shape[1]; m=3*k
    best=np.full(n,m,int)
    cdf=np.zeros((n,m+1),float);cdf[:,-1]=1.
    who=np.argmax(Y,axis=1)
    unique=(truth.sum(1)==1)&np.any(js==who[:,None],axis=1)
    ii=np.flatnonzero(unique)
    if len(ii):
        pos=np.argmax(js[ii]==who[ii,None],axis=1)
        vals=H[ii,pos,:]
        a=A[ii,who[ii]]
        M=rivals(Y)[ii,who[ii]]
        # Peer OUT uses strict inequality, consistent with the original EPS convention.
        enough=lambda x: M<C*(a+x)-EPS
        # All other missing candidates must be recovered in full; at most 2 winning records may be skipped.
        for r in range(3):
            count=np.zeros(len(ii),int)
            for sub in itertools.combinations(range(3),r):
                add=vals[:,list(sub)].sum(1) if r else np.zeros(len(ii))
                count+=enough(add)
            b=m-3+r
            cdf[ii,b]=count/math.comb(m,b)
            best[ii]=np.where((count>0)&(best[ii]==m),b,best[ii])
    assert np.all(np.diff(cdf,axis=1)>=-1e-12)
    return best,cdf,unique,who

def simulate(A,H,js,truth,peer_days,name):
    n,J=A.shape;k=js.shape[1];m=3*k
    rows=np.arange(n)
    low=np.argsort(np.take_along_axis(A,js,axis=1),axis=1,kind='stable')
    if name=='high_retained_first':low=np.argsort(-np.take_along_axis(A,js,axis=1),axis=1,kind='stable')
    if name=='array_id_first':low=np.broadcast_to(np.arange(k),(n,k))
    if name=='calendar_day_first':
        order=np.broadcast_to(np.array([j*3+d for d in range(3) for j in range(k)]),(n,m))
    else:
        day_order=np.argsort(-peer_days,axis=1,kind='stable') if name=='low_retained_peer_day_first' else np.broadcast_to(np.arange(3),(n,3))
        order=(low[:,:,None]*3+day_order[:,None,:]).reshape(n,m)
    lo=A.copy();rem=np.zeros_like(A,dtype=int);rem[rows[:,None],js]=3
    cost=np.full(n,m,int);stopped=np.zeros(n,bool)
    true_labels=np.where(truth,1,-1);prev=None;curve=[]
    for b in range(m+1):
        st=state(lo,rem)
        assert np.all((st==0)|(st==true_labels))
        if prev is not None:assert np.all((prev==0)|(prev==st))
        full=np.all(st!=0,axis=1)
        new=full&~stopped;cost[new]=b;stopped|=full
        curve.append({'budget':b,'resolved':int((st!=0).sum()),'full':int(full.sum()),'target_resolved':int((st[rows[:,None],js]!=0).sum())})
        prev=st
        if b<m:
            action=order[:,b];p=action//3;d=action%3
            jj=js[rows,p]
            lo[rows,jj]+=H[rows,p,d];rem[rows,jj]-=1
    assert stopped.all()
    return cost,curve

def evaluate(test,ids,site,max_targets=3):
    J=len(ids); result={'site':site,'ids':ids,'state':'RESEARCH_ONLY_R62','test_months':[m for m,v in test],'by_mask_count':{}}
    for k in range(1,min(max_targets,J-1)+1):
        m=3*k;comb=np.array(list(itertools.combinations(range(J),k)),int);n=len(comb)
        rows=np.arange(n);mask=np.zeros((n,J),bool);mask[rows[:,None],comb]=True
        monthly=[]; cost_hist={p:np.zeros(m+1,int) for p in POLICIES+['offline_optimum']}
        random_cdf=np.zeros(m+1); curves={p:[Counter() for _ in range(m+1)] for p in POLICIES}
        prec=[];strict_n=0;held=0;eligible=0;possible=0; oracle_unique=0
        first_match={p:0 for p in POLICIES}; optimal_savable=0; checks=Counter(); init=Counter()
        # Do not sort hidden values in policies. Peer-day ordering uses only originally complete channels.
        for mo,v in test:
            assert np.isfinite(v).all() and (v>=0).all()
            Y0=v.sum(0);mo_cost={p:0 for p in POLICIES+['offline_optimum']};mo_elig=0;mo_held=0;mo_full_savings=0
            for s in range(len(v)-2):
                hidden=v[s:s+3].T
                retained=np.concatenate([v[:s],v[s+3:]],axis=0).sum(0)
                Y=np.broadcast_to(Y0,(n,J));A=np.where(mask,retained,Y)
                # All-zero comparisons are held, as in R61. No retrospective exclusion based on outcomes.
                good=np.max(A,axis=1)>0
                possible+=n;held+=int((~good).sum());mo_held+=int((~good).sum())
                if not good.any():continue
                aa=A[good];yy=Y[good];js=comb[good];ms=mask[good];H=hidden[js];t=classify(yy)
                pday=(~ms).astype(float)@hidden
                N=len(aa);eligible+=N;mo_elig+=N
                best,cdf,unique,who=oracle(aa,yy,H,js,t)
                optimal_savable+=int((best<m).sum());oracle_unique+=int(unique.sum())
                cost_hist['offline_optimum']+=np.bincount(best,minlength=m+1);random_cdf+=cdf.sum(0)
                mo_cost['offline_optimum']+=int(best.sum());mo_full_savings+=int((best<m).sum())
                initial=state(aa,ms*3)
                init.update({'resolved':int((initial!=0).sum()),'full':int(np.all(initial!=0,axis=1).sum()),'target_resolved':int((initial[np.arange(N)[:,None],js]!=0).sum())})
                for policy in POLICIES:
                    cost,curve=simulate(aa,H,js,t,pday,policy)
                    assert np.all(cost>=best)
                    first_match[policy]+=int((cost==best).sum())
                    cost_hist[policy]+=np.bincount(cost,minlength=m+1);mo_cost[policy]+=int(cost.sum())
                    for b,c in enumerate(curve):curves[policy][b].update({x:y for x,y in c.items() if x!='budget'})
                    checks['monotone_safe_label_states']+=N*(m+1)
                r,strict,per=precision(aa,yy,ms,t)
                assert np.array_equal(np.isinf(r),np.all(initial!=0,axis=1))
                prec.extend((r/3).tolist());strict_n+=int(strict.sum())
                checks['precision_cases']+=N;checks['oracle_policy_comparisons']+=N*len(POLICIES)
            monthly.append({'month':mo,'eligible':mo_elig,'zero_hold':mo_held,'oracle_savable':mo_full_savings,'total_queries':mo_cost})
        assert eligible+held==possible
        p=np.asarray(prec,float);finite=p[np.isfinite(p)]
        summary={}
        for name,h in cost_hist.items():
            summary[name]={'cost_histogram':h.tolist(),'queries':int(h@np.arange(m+1)),'mean_queries':float(h@np.arange(m+1)/eligible) if eligible else None,'early_stops':int(h[:-1].sum()),'savings':int(eligible*m-h@np.arange(m+1)),'matches_offline_optimum':first_match.get(name,eligible)}
        rcdf=random_cdf/eligible if eligible else random_cdf
        random_mean=float(np.sum(1-rcdf[:-1]))
        base={'possible':possible,'eligible':eligible,'all_zero_hold':held,'records_per_mask':m,'initial':dict(init),'offline_savable':optimal_savable,'unique_winner_is_masked':oracle_unique,'methods':summary,
              'uniform_random_exact_expected_queries':random_mean,'uniform_random_full_resolution_cdf':rcdf.tolist(),'curves':{a:[dict(b) for b in c] for a,c in curves.items()},
              'precision':{'endpoint':'common absolute aggregate error r on each restored target; r/3 sufficient uniform absolute error per restored daily record; original retained records assumed exact',
                'finite_n':len(finite),'infinite_n':int(np.isinf(p).sum()),'strict_finite_n':strict_n,'zero_or_near_zero_n':int((finite<=1e-9).sum()),
                'finite_quantiles_0_10_25_50_75_90_100':np.quantile(finite,[0,.1,.25,.5,.75,.9,1]).tolist() if len(finite) else []},
              'monthly':monthly,'checks':dict(checks)}
        result['by_mask_count'][str(k)]=base
        print('R62_COUNTS',site,k,json.dumps({x:base[x] for x in ['possible','eligible','all_zero_hold','initial','offline_savable','methods','uniform_random_exact_expected_queries','precision','checks']}),flush=True)
    result['limits']=['Recorded reference and nonnegative missing daily totals, exact hypothetical archival retrieval, no proof of archive availability or real cost savings','All-zero initial comparison HOLD; held masks kept in denominator and not queried','No upper bounds, independent nonnegative completion; one, two or three simultaneous targets, common three-day gap','Offline optimum uses hidden reference only for hindsight; policies use retained totals and complete peers only; ties deterministic','Uniform random exact CDF from subset counting, no random seed or probabilistic model of output','Precision: independent aggregate error box, per-record bound is sufficient by triangle inequality, not a calibration specification','Previously inspected months, descriptive not fresh validation; no inference of independent mask samples','Georgia is native index only, not physical energy']
    return result

if __name__=='__main__':
    import r55_pmedc_paired_bounds_original_source as source
    a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--out',required=True);args=a.parse_args()
    m=source.read_months(args.source);assert len(m)==79 and source.BLOB=='5611277efdd581bb839ec380239846a43ebe0ba7'
    res=evaluate([(r['month'],np.asarray(r['days'],float)) for r in m[55:]],[str(i) for i in range(1,15)],'MORE-EU')
    assert res['by_mask_count']['1']['possible']==9520 and res['by_mask_count']['1']['initial']['resolved']==31022
    assert res['by_mask_count']['2']['possible']==61880 and res['by_mask_count']['2']['initial']['resolved']==181107
    Path(args.out).mkdir(parents=True,exist_ok=True);Path(args.out,'more_eu_r62.json').write_text(json.dumps(res,indent=2)+'\n')
