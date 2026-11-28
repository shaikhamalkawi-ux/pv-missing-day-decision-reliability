"""R62 second prespecified research-only audit: individual-label minimum exact retrieval.
Same cohorts, no physical upper bound. Costs are hypothetical daily record retrieval counts.
Independent minima for labels are NOT jointly attainable at the same budget in general.
"""
import argparse,itertools,json
from pathlib import Path
import numpy as np
import r62_minimum_measurement_recovery as base
C=base.C; EPS=base.EPS

def label_minimum(A,Y,H,js,truth):
    n,J=A.shape;k=js.shape[1];m=3*k;rows=np.arange(n)
    mask=np.zeros_like(A,dtype=bool);mask[rows[:,None],js]=True
    # Prefix sums of the largest recovered values are an offline witness construction.
    prefix=np.zeros((n,J,4),float)
    prefix[rows[:,None],js,1:]=np.cumsum(np.sort(H,axis=2)[:,:,::-1],axis=2)
    # Inclusion: every other missing candidate must have a finite upper endpoint.
    # The target needs enough retrieved production to reach c times the largest true rival.
    M=base.rivals(Y)
    inc_ok=A[:,:,None]+prefix>=C*M[:,:,None]-EPS
    inc_n=np.where(inc_ok.any(2),np.argmax(inc_ok,axis=2),m+1)
    inc_cost=3*(k-mask.astype(int))+inc_n
    # Exclusion: target must be exact; one sufficiently large rival lower endpoint suffices.
    # Independent candidate-specific witness, not a proposed live retrieval order.
    witness=np.full((n,J,J),m+1,int)
    diag=np.eye(J,dtype=bool)[None,:,:]
    for t in reversed(range(4)):
        ok=Y[:,:,None]<C*(A+prefix[:,:,t])[:,None,:]-EPS
        witness=np.where(ok&~diag,t,witness)
    out_cost=3*mask.astype(int)+witness.min(2)
    costs=np.where(truth,inc_cost,out_cost)
    assert (costs>=0).all() and (costs<=m).all()
    initial=base.state(A,3*mask)
    assert np.array_equal(costs==0,initial!=0)
    best,*_=base.oracle(A,Y,H,js,truth)
    assert np.all(costs.max(1)<=best)
    return costs,mask

def evaluate(test,ids,site,max_targets=3):
    J=len(ids);result={'site':site,'state':'RESEARCH_ONLY_R62_LABEL_RECOVERY','ids':ids,'test_months':[mo for mo,v in test],'by_mask_count':{}}
    for k in range(1,min(max_targets,J-1)+1):
        m=3*k;js0=np.asarray(list(itertools.combinations(range(J),k)),int);n=len(js0)
        mask0=np.zeros((n,J),bool);mask0[np.arange(n)[:,None],js0]=True
        groups=['all','masked_target','measured_peer','true_in','true_out']
        hist={g:np.zeros(m+1,np.int64) for g in groups}
        precision_parts={'masked_target':[],'measured_peer':[]}
        monthly=[];possible=eligible=held=0;checks=0
        for mo,v in test:
            v=np.asarray(v,float);assert np.isfinite(v).all() and (v>=0).all()
            Y0=v.sum(0);month_hist=np.zeros(m+1,np.int64);month_eligible=0
            for s in range(len(v)-2):
                hid=v[s:s+3].T
                retained=np.concatenate([v[:s],v[s+3:]],axis=0).sum(0)
                Y=np.broadcast_to(Y0,(n,J));A=np.where(mask0,retained,Y)
                good=A.max(1)>0;possible+=n;held+=int((~good).sum())
                if not good.any():continue
                a=A[good];y=Y[good];js=js0[good];truth=base.classify(y);H=hid[js]
                N=len(a);eligible+=N;month_eligible+=N
                cost,mask=label_minimum(a,y,H,js,truth);checks+=N*J
                masks={'all':np.ones_like(mask),'masked_target':mask,'measured_peer':~mask,'true_in':truth,'true_out':~truth}
                for g,b in masks.items():hist[g]+=np.bincount(cost[b],minlength=m+1)
                month_hist+=np.bincount(cost.ravel(),minlength=m+1)
                _,_,per=base.precision(a,y,mask,truth)
                for g,b in [('masked_target',mask),('measured_peer',~mask)]:precision_parts[g].append(per[b]/3)
            monthly.append({'month':mo,'eligible':month_eligible,'all_hist':month_hist.tolist()})
        assert hist['all'].sum()==eligible*J
        assert np.array_equal(hist['all'],hist['masked_target']+hist['measured_peer'])
        assert np.array_equal(hist['all'],hist['true_in']+hist['true_out'])
        assert np.array_equal(hist['all'],np.sum([a['all_hist'] for a in monthly],axis=0))
        metrics={}
        for g,h in hist.items():
            count=int(h.sum());unresolved=count-int(h[0])
            metrics[g]={'histogram':h.tolist(),'count':count,'initial_resolved':int(h[0]),'mean_minimum_queries':float(h@np.arange(m+1)/count) if count else None,
              'unresolved_mean_minimum_queries':float(h@np.arange(m+1)/unresolved) if unresolved else None,
              'individual_certificate_within_budget':np.cumsum(h).tolist(),'unresolved_resolvable_with_less_than_all':int(h[1:-1].sum()),'requires_all':int(h[-1])}
        pres={}
        for g,parts in precision_parts.items():
            p=np.concatenate(parts);f=p[np.isfinite(p)]
            pres[g]={'count':len(p),'infinite_count':int(np.isinf(p).sum()),'finite_count':len(f),'finite_quantiles_0_10_25_50_75_90_100':np.quantile(f,[0,.1,.25,.5,.75,.9,1]).tolist() if len(f) else []}
        r={'possible':possible,'eligible':eligible,'all_zero_hold':held,'records_per_mask':m,'metrics':metrics,'per_label_precision':pres,'monthly':monthly,'label_checks':checks}
        result['by_mask_count'][str(k)]=r
        print('R62_LABEL_PASS',site,k,json.dumps({x:r[x] for x in ['possible','eligible','all_zero_hold','metrics','per_label_precision','label_checks']}),flush=True)
    result['limits']=['Individual offline minima use hidden reference only in retrospective scoring; do not identify which measurements actually exist. Independent label minima cannot be added or treated as a joint policy.','Same nonnegative-recorded endpoint, exact retrieval, common three-day masks and zero-state HOLD as R62.','Per-label precision uses full recovered nominal reference, common absolute aggregate radius r divided by 3; finite tolerance quantiles are descriptive. No instrument specification.']
    return result

if __name__=='__main__':
    import r55_pmedc_paired_bounds_original_source as src
    a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--out',required=True);args=a.parse_args()
    months=src.read_months(args.source);assert len(months)==79 and src.BLOB=='5611277efdd581bb839ec380239846a43ebe0ba7'
    res=evaluate([(r['month'],np.asarray(r['days'],float)) for r in months[55:]],[str(i) for i in range(1,15)],'MORE-EU')
    Path(args.out).mkdir(parents=True,exist_ok=True);Path(args.out,'more_eu_r62_labels.json').write_text(json.dumps(res,indent=2)+'\n')
