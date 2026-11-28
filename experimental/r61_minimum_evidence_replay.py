"""R61 research-only evidence requests, matched staged policy and alternatives.
Prespecified post-hoc replay on R60 cohorts. No raw records exported.
"""
import argparse, math, json, itertools
from pathlib import Path
from collections import Counter
import numpy as np
import r57_partial_resolution_source_replay as orig
import r55_single_array_peer_prediction as peer
import r60_observation_constrained_replay as r60
C=.95; EPS=orig.EPS

def record(st,truth,j):
    a=np.array(st); resolved=a!='?'
    wrong=resolved&((a=='I')!=truth)
    return dict(possible=1,labels=len(a),resolved=int(resolved.sum()),wrong=int(wrong.sum()),full=int(resolved.all()),wrong_full=int(resolved.all() and wrong.any()),target_resolved=int(resolved[j]),target_wrong=int(wrong[j]),peer_resolved=int(resolved.sum()-resolved[j]),peer_wrong=int(wrong.sum()-wrong[j]))

def median_predict(v,s,j):
    peer_y=np.delete(v,j,axis=1).mean(1)
    keep=np.ones(len(v),bool);keep[s:s+3]=False
    good=keep&(peer_y>0)
    if not good.any():return None
    return float(np.median(v[good,j]/peer_y[good])*peer_y[s:s+3].sum())

def predict(v,s,j,method):
    masked=v.copy();masked[s:s+3,j]=0.
    if method=='boundary':p=peer.evaluate_models(masked,s,j,np.ones(v.shape[1])).get('peer_boundary_ratio')
    else:p=median_predict(masked,s,j)
    if p is not None:assert np.isfinite(p) and p>=0
    return p

def evaluate(dev,test,ids,site,cap=None):
    J=len(ids);orig.J=peer.J=J
    methods=['boundary','median']
    monthly_max={m:[] for m in methods}
    dev_counts={m:Counter() for m in methods}
    for mo,v in dev:
        errors={m:[[] for i in range(J)] for m in methods}
        for s in range(len(v)-2):
            for j in range(J):
                h=v[s:s+3,j].sum()
                for m in methods:
                    p=predict(v,s,j,m);dev_counts[m]['possible']+=1
                    if p is None:continue
                    dev_counts[m]['eligible']+=1;errors[m][j].append(abs(p-h))
        for m in methods:
            monthly_max[m].append([max(e) if e else 0. for e in errors[m]])
    rad={}
    for m in methods:
        z=np.array(monthly_max[m]);wide=z.max(0);p90=np.sort(z,axis=0)[math.ceil(.9*len(z))-1]
        rad[m]={'wide':wide}
        if not np.array_equal(wide,p90):rad[m]['p90']=p90
    polnames=['obs_only']+[m+'_'+b+'_staged' for m in methods for b in rad[m]]
    if cap is not None:polnames+=['rated_cap_only','rated_cap_plus_boundary_wide']
    allcounts={m:Counter() for m in polnames}; monthcounts={m:{} for m in polnames}
    preds={m:Counter() for m in methods}; monthpred={m:{} for m in methods}
    routes={m:Counter() for m in polnames}; evidence=Counter(); evidence_month={}; requirements=[]
    paircounts={'obs_only':Counter()};pair_month={'obs_only':{}}
    if cap is not None:paircounts['rated_cap']=Counter();pair_month['rated_cap']={}
    checks=Counter();scenario=Counter()
    for mo,v in test:
        full=v.sum(0);truth=orig.classify(full)
        mc={m:Counter() for m in polnames};mp={m:Counter() for m in methods};me=Counter();pc={m:Counter() for m in paircounts}
        for s in range(len(v)-2):
            h=v[s:s+3].sum(0)
            for j in range(J):
                known=full.copy();known[j]-=h[j]
                assert known[j]>=-EPS;known[j]=max(0.,known[j])
                a=known.copy();u=known.copy();u[j]=np.inf
                obs=r60.labels(a,u);assert not record(obs,truth,j)['wrong']
                zero=max(known)<=0
                unresolved=not all(x!='?' for x in obs)
                ev=Counter(possible=1,zero_hold=int(zero),already_full=int(not unresolved and not zero))
                if not zero and unresolved:
                    ev['needs_evidence']=1
                    # Feasibility of obtaining sufficient one-sided information, using hidden h ONLY for retrospective scoring.
                    # Neither bound is issued or supplied to the policy.
                    up=known.copy();up[j]+=h[j]
                    low=known.copy();low[j]+=h[j]
                    us=r60.labels(known,up);ls=r60.labels(low,u)
                    uf=all(x!='?' for x in us);lf=all(x!='?' for x in ls)
                    assert not (uf and lf) # Otherwise the whole domain would already be resolved.
                    ev.update(upper_only_feasible=int(uf),lower_only_feasible=int(lf),two_sided_required=int(not uf and not lf))
                    # For [0,B] the smallest upper switching threshold across unresolved memberships is decisive.
                    # Target OUT: B < c*M-A (strict). Peer IN: B <= Y_i/c-A (inclusive).
                    # Preserve ties and report no threshold using hidden output.
                    thresholds=[]
                    if obs[j]=='?':thresholds.append((C*max(np.delete(known,j))-known[j],True))
                    for i in range(J):
                        if i!=j and obs[i]=='?':thresholds.append((known[i]/C-known[j],False))
                    assert thresholds
                    t=min(x[0] for x in thresholds); strict=any(sx and abs(x-t)<=EPS for x,sx in thresholds)
                    # Lower-only full resolution: target IN and all peers OUT, use max threshold.
                    t2=max(x[0] for x in thresholds)
                    strict2=any((not sx) and abs(x-t2)<=EPS for x,sx in thresholds)
                    requirements.append({'month':mo,'target':ids[j],'upper_cap_threshold':float(t),'upper_strict':bool(strict),'lower_floor_threshold':float(t2),'lower_strict':bool(strict2)})
                    checks['threshold_requests']+=1
                evidence.update(ev);me.update(ev)
                def add(m,st,route):
                    c=record(st,truth,j);allcounts[m].update(c);mc[m].update(c);routes[m][route]+=1
                add('obs_only',['?']*J if zero else obs,'zero_hold' if zero else 'observations')
                estimates={}
                for m in methods:
                    p=predict(v,s,j,m);estimates[m]=p
                    d={'possible':1,'eligible':int(p is not None)}
                    if p is not None:
                        y=known.copy();y[j]+=p
                        d.update(point_correct=int(np.array_equal(orig.classify(y),truth)),abs_error=abs(p-h[j]),reference=h[j])
                    preds[m].update(d);mp[m].update(d)
                    for b,R in rad[m].items():
                        name=m+'_'+b+'_staged'
                        if zero:add(name,['?']*J,'zero_hold');continue
                        if not unresolved:add(name,obs,'observation_full_skip');continue
                        if p is None:add(name,obs,'unavailable_retain_obs');continue
                        l,uu=r60.bounds(known,j,p,float(R[j]),'constrained')
                        st=r60.labels(l,uu)
                        assert all(x=='?' or x==y for x,y in zip(obs,st))
                        covered=abs(p-h[j])<=R[j]+EPS
                        c=record(st,truth,j)
                        assert not (covered and c['wrong'])
                        add(name,st,'historical_conditional')
                        # Separate local empirical containment from correctness of available observations.
                        for ctr in (allcounts[name],mc[name]):
                            ctr['empirical_evaluated']+=1;ctr['empirical_contained']+=int(covered)
                        checks['staged_union_checks']+=1
                if cap is not None:
                    B=float(cap[j]);scenario['possible']+=1;scenario['contains_recorded_gap']+=int(h[j]<=B+EPS)
                    hi=known.copy();hi[j]+=B
                    st=r60.labels(known,hi)
                    if h[j]<=B+EPS:assert not record(st,truth,j)['wrong']
                    add('rated_cap_only',['?']*J if zero else st,'zero_hold' if zero else 'cap_scenario')
                    p=estimates['boundary']
                    if zero:add('rated_cap_plus_boundary_wide',['?']*J,'zero_hold')
                    elif p is None:add('rated_cap_plus_boundary_wide',st,'cap_only_unavailable')
                    else:
                        lo,up=r60.bounds(known,j,p,float(rad['boundary']['wide'][j]),'constrained')
                        up[j]=min(up[j],hi[j])
                        if lo[j]>up[j]+EPS:
                            scenario['interval_conflicts']+=1;add('rated_cap_plus_boundary_wide',obs,'conflict_hold_empirical')
                        else:add('rated_cap_plus_boundary_wide',r60.labels(lo,up),'intersection_scenario')
            # Exact two-target same-window masks: no claim of peer prediction with two missing targets.
            for js in itertools.combinations(range(J),2):
                known=full.copy();known[list(js)]-=h[list(js)];known=np.maximum(known,0)
                zero=max(known)<=0
                hi=known.copy();hi[list(js)]=np.inf
                # With two unbounded candidates, only complete peers can be universally OUT.
                st=['?' if i in js or not (known[i]<C*max(np.delete(known,i))-EPS) else 'E' for i in range(J)]
                assert all((x=='?') or not truth[i] for i,x in enumerate(st))
                for name,labels in [('obs_only',st)]+([('rated_cap',r60.labels(known,known+np.array([cap[i] if i in js else 0. for i in range(J)])))] if cap is not None else []):
                    if zero:labels=['?']*J
                    a=np.array(labels);resolved=a!='?';wrong=resolved&((a=='I')!=truth)
                    dd=dict(possible=1,labels=J,resolved=int(resolved.sum()),wrong=int(wrong.sum()),full=int(resolved.all()),missing_target_labels=2,missing_target_resolved=int(resolved[list(js)].sum()),peer_resolved=int(resolved.sum()-resolved[list(js)].sum()),zero_hold=int(zero))
                    paircounts[name].update(dd);pc[name].update(dd)
                    if name=='rated_cap':
                        finite_hi=known+np.array([cap[i] if i in js else 0. for i in range(J)])
                        corners=[]
                        for bits in itertools.product([0,1],repeat=2):
                            z=known.copy()
                            for i,b in zip(js,bits):z[i]=finite_hi[i] if b else known[i]
                            corners.append(orig.classify(z))
                        corners=np.array(corners)
                        alt=['I' if corners[:,i].all() else 'E' if not corners[:,i].any() else '?' for i in range(J)]
                        if not zero:assert alt==labels
                        checks['two_target_corner_checks']+=1
        for m in polnames:monthcounts[m][mo]=dict(mc[m])
        for m in methods:monthpred[m][mo]=dict(mp[m])
        for m in paircounts:pair_month[m][mo]=dict(pc[m])
        evidence_month[mo]=dict(me)
    assert evidence['needs_evidence']==evidence['upper_only_feasible']+evidence['lower_only_feasible']+evidence['two_sided_required']
    assert allcounts['obs_only']['wrong']==0 and paircounts['obs_only']['wrong']==0
    summary={}
    for m,c in allcounts.items():
        vals=[]
        for mo,mm in monthcounts[m].items():
            vals.append((c['resolved']-mm['resolved'])/(c['labels']-mm['labels']))
        summary[m]={'monthly_macro_coverage':float(np.mean([d['resolved']/d['labels'] for d in monthcounts[m].values()])), 'leave_one_month_out_min':min(vals),'leave_one_month_out_max':max(vals)}
        assert sum(routes[m].values())==c['possible']
    # Only aggregate thresholds (not raw values) are exported.
    th={}
    for label in ['upper_cap_threshold','lower_floor_threshold']:
        x=[r[label] for r in requirements]
        th[label]={'n':len(x),'min':min(x) if x else None,'median':float(np.median(x)) if x else None,'max':max(x) if x else None}
    return {'state':'RESEARCH_ONLY_R61','site':site,'ids':ids,'development':{m:dict(c) for m,c in dev_counts.items()},'dev_months':[m for m,v in dev],'test_months':[m for m,v in test],
    'radii':{m:{b:r.tolist() for b,r in bb.items()} for m,bb in rad.items()},'prediction':{m:dict(c) for m,c in preds.items()},'prediction_by_month':monthpred,
    'staged':{m:dict(c) for m,c in allcounts.items()},'routes':{m:dict(c) for m,c in routes.items()},'staged_monthly':monthcounts,'month_sensitivity':summary,
    'evidence_feasibility':dict(evidence),'evidence_by_month':evidence_month,'threshold_summary':th,'two_target':{m:dict(c) for m,c in paircounts.items()},'two_target_monthly':pair_month,
    'rated_cap':None if cap is None else cap.tolist(),'rated_cap_diagnostic':dict(scenario),'checks':dict(checks),
    'limits':['Previously inspected cohorts, post-hoc diagnostic, overlapping masks not independent','One-sided feasibility uses hidden recorded output only for hindsight, not available evidence or operational performance','Nameplate x72h scenario not a physical certified upper bound or calibrated meter interval','Median retained-day peer ratios fixed without tuning; no new predictive claim','Two-target common gaps observation-only or explicit cap scenario; no multi-target reconstruction','All-zero retained comparison held in staged policy']}

if __name__=='__main__':
    import r55_pmedc_paired_bounds_original_source as src
    a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--out',required=True);args=a.parse_args()
    m=src.read_months(args.source);assert len(m)==79 and src.BLOB=='5611277efdd581bb839ec380239846a43ebe0ba7'
    rows=[(r['month'],np.asarray(r['days'],float)) for r in m]
    res=evaluate(rows[:55],rows[55:],[str(i) for i in range(1,15)],'MORE-EU')
    assert res['staged']['obs_only']['resolved']==31022
    assert res['staged']['boundary_wide_staged']['resolved']==35723
    assert res['staged']['boundary_p90_staged']['resolved']==110520
    Path(args.out).mkdir(parents=True,exist_ok=True);Path(args.out,'more_eu_r61.json').write_text(json.dumps(res,indent=2)+'\n')
    print('R61_MORE_EU_PASS',json.dumps({k:res[k] for k in ['staged','routes','prediction','evidence_feasibility','two_target','checks']}),flush=True)
