"""R60: predeclared observation-only and observation-constrained resolution.
Research only; original empirical envelopes are not physical bounds.
No raw telemetry is emitted. Single missing target, nonnegative recorded daily values.
"""
import argparse, math, json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import r57_partial_resolution_source_replay as orig
import r55_single_array_peer_prediction as peer
Q=.05; C=.95; EPS=orig.EPS

def classify(y): return orig.classify(y)

def labels(lo,hi):
    lo=np.asarray(lo,float);hi=np.asarray(hi,float)
    assert (lo>=0).all() and (hi>=lo).all()
    return ['I' if lo[i]>=C*max(np.delete(hi,i))-EPS else 'E' if hi[i]<C*max(np.delete(lo,i))-EPS else '?' for i in range(len(lo))]

def bounds(known,j,p,r,mode):
    lo=known.copy();hi=known.copy()
    if mode=='observed_only':
        hi[j]=np.inf
    else:
        lo[j]=max(0.,known[j]+p-r) if mode=='legacy' else known[j]+max(0.,p-r)
        hi[j]=known[j]+p+r
    return lo,hi

def evaluate(dev,test,ids,site):
    J=len(ids);orig.J=peer.J=J
    monthly=[]; dc=Counter()
    for mo,v in dev:
        e=np.zeros(J)
        for s in range(len(v)-2):
            for j in range(J):
                masked=v.copy();masked[s:s+3,j]=0.
                p=peer.evaluate_models(masked,s,j,np.ones(J)).get('peer_boundary_ratio')
                dc['possible']+=1
                if p is None:dc['unavailable']+=1;continue
                dc['eligible']+=1;e[j]=max(e[j],abs(p-v[s:s+3,j].sum()))
        monthly.append(e)
    mx=np.array(monthly);bands={'wide':mx.max(0),'p90':np.sort(mx,axis=0)[math.ceil(.9*len(mx))-1]}
    # Preserve distinct envelopes only; same result is explicitly noted when coincident.
    if np.array_equal(bands['wide'],bands['p90']):del bands['p90']
    methods=['observed_only']+[b+'_'+m for b in bands for m in ['legacy','constrained']]
    stats={m:Counter() for m in methods}; target={m:{i:Counter() for i in ids} for m in methods}
    per_month={m:{} for m in methods};delta={b:Counter() for b in bands};delta_month={b:{} for b in bands}
    comparator=Counter();errors=[];checks=Counter()
    for mo,v in test:
        truth_total=v.sum(0);truth=classify(truth_total)
        cm={m:Counter() for m in methods};dm={b:Counter() for b in bands}
        for s in range(len(v)-2):
            hidden=v[s:s+3,:].sum(0)
            common=classify(truth_total-hidden)
            for j in range(J):
                masked=v.copy();masked[s:s+3,j]=0.;known=masked.sum(0)
                p=peer.evaluate_models(masked,s,j,np.ones(J)).get('peer_boundary_ratio')
                assert p==peer.evaluate_models(v,s,j,np.ones(J)).get('peer_boundary_ratio')
                checks['hidden_perturbation']+=1
                assert p is None or (np.isfinite(p) and p>=0)
                comparator['possible']+=1
                comparator['common_retained_correct_all']+=int(np.array_equal(common,truth))
                if p is not None:
                    point=known.copy();point[j]+=p
                    exact=np.array_equal(classify(point),truth);common_exact=np.array_equal(common,truth)
                    comparator.update({'eligible':1,'point_correct':int(exact),'zero_correct':int(np.array_equal(classify(known),truth)),'common_retained_correct_eligible':int(common_exact),'point_repairs_common':int(exact and not common_exact),'point_damages_common':int(common_exact and not exact)})
                else:comparator['unavailable']+=1
                def record(m,st,contained,eligible=True):
                    res=[k for k in range(J) if st[k]!='?']
                    wrong=[k for k in res if (st[k]=='I')!=bool(truth[k])]
                    fi=[k for k in wrong if st[k]=='I'];fo=[k for k in wrong if st[k]=='E']
                    assert not(contained and wrong)
                    c={'possible':1,'eligible':int(eligible),'all_possible':J,'peer_possible':J-1,
                       'full_resolved':int(len(res)==J),'full_wrong':int(len(res)==J and bool(wrong)),
                       'all_resolved':len(res),'all_wrong':len(wrong),'target_resolved':int(j in res),'target_wrong':int(j in wrong),
                       'peer_resolved':len(res)-int(j in res),'peer_wrong':len(wrong)-int(j in wrong),
                       'false_in':len(fi),'false_out':len(fo),'target_in':int(st[j]=='I'),'target_out':int(st[j]=='E'),
                       'peer_in':sum(st[k]=='I' for k in range(J) if k!=j),'peer_out':sum(st[k]=='E' for k in range(J) if k!=j),
                       'contained':int(contained) if eligible else 0,'wrong_outside':len(wrong) if not contained else 0}
                    for d in [stats[m],target[m][ids[j]],cm[m]]:d.update(c)
                    if wrong:errors.append({'month':mo,'start_day':s+1,'target':ids[j],'method':m,'contained':bool(contained),'wrong':[{'id':ids[k],'status':st[k],'truth':'I' if truth[k] else 'E'} for k in wrong]})
                    return c
                a,z=bounds(known,j,None,None,'observed_only'); obs=labels(a,z)
                # Exact unbounded rule: target IN iff its retained yield reaches relative threshold;
                # peers OUT iff below threshold of retained target or other measured rivals.
                direct=['?' for k in range(J)]
                if known[j]>=C*max(np.delete(known,j))-EPS:direct[j]='I'
                for k in range(J):
                    if k!=j and known[k]<C*max(np.delete(known,k))-EPS:direct[k]='E'
                assert obs==direct
                assert truth_total[j]>=known[j]-EPS
                record('observed_only',obs,True);checks['observed_exact']+=1
                for b,rad in bands.items():
                    if p is None:
                        for mode in ['legacy','constrained']:record(b+'_'+mode,['?']*J,False,False)
                        continue
                    R=float(rad[j]);covered=abs(p-hidden[j])<=R+EPS
                    l,u=bounds(known,j,p,R,'legacy');lt,ut=bounds(known,j,p,R,'constrained')
                    assert lt[j]>=l[j]-EPS and np.allclose(u,ut,rtol=0,atol=EPS)
                    old=labels(l,u);new=labels(lt,ut)
                    assert old==orig.statuses(point,j,R)
                    # Independent endpoints, since only one target varies and membership is monotone.
                    for x,y,st in [(l,u,old),(lt,ut,new)]:
                        f0,f1=classify(x),classify(y)
                        assert st==['I' if a and b else 'E' if not a and not b else '?' for a,b in zip(f0,f1)]
                        checks['finite_endpoint_labels']+=J
                    assert all(x=='?' or x==y for x,y in zip(old,new))
                    assert all(x=='?' or x==y for x,y in zip(obs,new))
                    assert covered==bool(lt[j]-EPS<=truth_total[j]<=ut[j]+EPS)
                    co=record(b+'_legacy',old,covered);cn=record(b+'_constrained',new,covered)
                    more=[k for k in range(J) if old[k]=='?' and new[k]!='?']
                    addwrong=[k for k in more if (new[k]=='I')!=bool(truth[k])]
                    d={'eligible':1,'changed_lower_endpoint':int(lt[j]>l[j]+EPS),'additional_full_lists':cn['full_resolved']-co['full_resolved'],
                       'additional_labels':len(more),'additional_target':int(j in more),'additional_peer':len(more)-int(j in more),'additional_wrong':len(addwrong),'additional_wrong_target':int(j in addwrong)}
                    delta[b].update(d);dm[b].update(d);checks['nested_interval_checks']+=1
        for m in methods:per_month[m][mo]=dict(cm[m])
        for b in bands:delta_month[b][mo]=dict(dm[b])
    for m,c in stats.items():
        assert c['all_resolved']==c['target_resolved']+c['peer_resolved']
        assert c['all_wrong']==c['target_wrong']+c['peer_wrong']==c['false_in']+c['false_out']
    assert stats['observed_only']['all_wrong']==0
    for b,d in delta.items():
        assert stats[b+'_constrained']['all_resolved']-stats[b+'_legacy']['all_resolved']==d['additional_labels']
        assert stats[b+'_constrained']['all_wrong']-stats[b+'_legacy']['all_wrong']==d['additional_wrong']
    return {'state':'RESEARCH_ONLY_R60_OBSERVATION_CONSTRAINED','site':site,'ids':ids,'dev_months':[m for m,v in dev],'test_months':[m for m,v in test],
            'development':dict(dc),'radii':{k:v.tolist() for k,v in bands.items()},'p90_equals_max':'p90' not in bands,'metrics':{k:dict(c) for k,c in stats.items()},
            'by_target':{m:{i:dict(c) for i,c in rows.items()} for m,rows in target.items()},'by_month':per_month,'increment':{b:dict(d) for b,d in delta.items()},'increment_monthly':delta_month,'comparators':dict(comparator),'checks':dict(checks),'wrong_events':errors,
            'limits':'Single target nonnegative recorded daily yield; exact observation-only conditional on surviving reference values, not instrument truth; historical intervals conditional on coverage; post-hoc R60 diagnostic, not fresh untouched test; no tuning.'}

def more_eu(srcfile,out):
    import r55_pmedc_paired_bounds_original_source as src
    m=src.read_months(srcfile);assert len(m)==79 and src.BLOB=='5611277efdd581bb839ec380239846a43ebe0ba7'
    rows=[(r['month'],np.asarray(r['days'],float)) for r in m]
    result=evaluate(rows[:55],rows[55:],[str(i) for i in range(1,15)],'MORE-EU')
    assert result['development']['unavailable']==196
    for b,counts in [('wide',(422,35696,0)),('p90',(2084,110515,27))]:
        c=result['metrics'][b+'_legacy'];assert (c['full_resolved'],c['all_resolved'],c['all_wrong'])==counts
    assert result['comparators']['point_correct']==9145 and result['comparators']['common_retained_correct_eligible']==7182
    Path(out).mkdir(parents=True,exist_ok=True);Path(out,'more_eu_r60.json').write_text(json.dumps(result,indent=2)+'\n')
    print('R60_MORE_EU_PASS',json.dumps({k:result[k] for k in ['metrics','increment','comparators','checks']}),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--out',required=True);args=a.parse_args();more_eu(args.source,args.out)
