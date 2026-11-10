#!/usr/bin/env python3
"""R28 — baseline-preserving critical relative-gain radius (source development).

For each HKUST source-qualified co-roof month, identify the smallest symmetric
per-device gain box eps such that some constant eta vector preserves the
original full-month shortlist yet yields a different shortlist after a
contiguous gap of <=3 whole days.

This is a finite LP disjunction over full-month out-of-set challengers and
post-gap set membership flips.  It does NOT infer measured calibration error,
sensor covariance, outage probability or independent experimental replications.

Ref source: HKUST Zenodo 10909062, SHA-256 pinned by R26I/R26L.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import product
from pathlib import Path
from scipy.optimize import linprog
import csv,json,hashlib,math

I=Path("input")
O=Path("R28_CriticalGainMargin")
O.mkdir(parents=True,exist_ok=True)
SOURCE_HASH="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
Q=0.05
L_MAX=3
EPS_CAP=0.05
SLACK=2e-8  # normalized yield-unit strict separation for numerical witness
LP_OPTS={"primal_feasibility_tolerance":1e-10,"dual_feasibility_tolerance":1e-10}
def loadcsv(name):
    with (I/name).open("r",newline="",encoding="utf8") as f:
        return list(csv.DictReader(f))
source=loadcsv("DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
tiers={r["group"]:r["quality_tier"] for r in loadcsv("SOURCE_BASED_TIER_REGISTER.csv")}
r26k=loadcsv("R26K_SOURCE_MONTH_EPSILON_BASELINE_GATE.csv")
r26i=json.loads((I/"CALCULATION_CERTIFICATE.json").read_text())
assert r26i["sha256"]==SOURCE_HASH and r26i["status"]=="PASS_DEVELOPMENT_ONLY"
assert len(source)>1000 and len(r26k)==84 and len(tiers)==5
records=defaultdict(lambda:defaultdict(dict))
for r in source:
    k=(r["group"],r["month"]);day=r["date"];inv=r["inverter"]
    assert inv not in records[k][day],(k,day,inv)
    records[k][day][inv]=float(r["normalized_observed_sample_sum"])
assert len(records)==12
def shortlist(y,eta):
    m=max(y[k]*eta[k] for k in y)
    assert m>0
    return tuple(sorted(k for k in y if y[k]*eta[k] >= (1-Q)*m))
def sums(raw,days,names):
    return {k:sum(raw[d][k] for d in days) for k in names}

def ordered_lp_constraints(f,g,names,baseline,j,k=None,refout_comp=(),slack=SLACK,cap=EPS_CAP):
    """Minimize eps with eta_j in [1-eps,1+eps] and gap flip."""
    n=len(names);ix={a:i for i,a in enumerate(names)}
    A=[];B=[]
    def bound(a,b,margin):
        vec=[0.0]*(n+1)
        vec[ix[a]]+=margin[0]
        vec[ix[b]]+=margin[1]
        A.append(vec);B.append(-slack)
    # eta_i <= 1+eps ; eta_i >= 1-eps
    for x in names:
        v=[0.]*(n+1);v[ix[x]]=1.;v[-1]=-1.
        A.append(v);B.append(1.)
        v=[0.]*(n+1);v[ix[x]]=-1.;v[-1]=-1.
        A.append(v);B.append(-1.)
    # Full reference fixed; all original members must have strictly
    # positive eligibility margins over other devices.
    for x in baseline:
        for y in names:
            if x==y:continue
            bound(y,x,((1-Q)*f[y],-f[x]))
    # Full-month nonmembers must be strictly excluded by preselected
    # challenger (one per nonmember, enumerated outside).
    outset=[x for x in names if x not in baseline]
    assert len(outset)==len(refout_comp)
    for x,y in zip(outset,refout_comp):
        bound(x,y,(f[x],-(1-Q)*f[y]))
    if j in baseline:
        assert k is not None and j!=k
        # after deleting days, baseline member j gets strictly excluded
        bound(j,k,(g[j],-(1-Q)*g[k]))
    else:
        assert k is None
        # after deleting days, previously excluded j becomes an admitted
        # member, with positive margin against every competitor
        for x in names:
            if j==x:continue
            bound(x,j,((1-Q)*g[x],-g[j]))
    c=[0.]*(n+1);c[-1]=1.
    return c,A,B,[(0.01,2.)]*n+[(0.,cap)]

def source_witness(full,gap,names,baseline,cap=EPS_CAP,slack=SLACK):
    scale=max(full.values())
    assert scale>0
    f={k:full[k]/scale for k in names}
    g={k:gap[k]/scale for k in names}
    outsider=[a for a in names if a not in baseline]
    options=[tuple(k for k in names if k!=a) for a in outsider]
    assignments=product(*options) if options else [()]
    best=None;calls=0;infeasible=0
    for assignment in assignments:
        for j in names:
            challengers=tuple(k for k in names if k!=j) if j in baseline else (None,)
            for k in challengers:
                c,A,B,bounds=ordered_lp_constraints(f,g,names,baseline,j,k,
                                                    assignment,slack=slack,cap=cap)
                calls+=1
                res=linprog(c,A_ub=A,b_ub=B,bounds=bounds,method="highs",options=LP_OPTS)
                if res.status==2:
                    infeasible+=1;continue
                if res.status!=0:raise RuntimeError((res.status,res.message))
                eps=max(0.,float(res.x[-1]))
                eta={v:float(res.x[i]) for i,v in enumerate(names)}
                base=shortlist(full,eta);post=shortlist(gap,eta)
                if base!=baseline or post==baseline:
                    # Reject optimizer boundary artifacts; never treat them
                    # as certified witness.
                    continue
                if not all(1-eps-1e-8<=x<=1+eps+1e-8 for x in eta.values()):
                    raise AssertionError("Out-of-box factor")
                entry=dict(epsilon=eps,device=j,challenger=k,
                           full_nonmember_challengers=list(assignment),
                           eta=eta,baseline=list(base),after_gap=list(post),
                           strict_margin_slack=slack)
                if best is None or entry["epsilon"]<best["epsilon"]:
                    best=entry
    return best,calls,infeasible

primary=[];witnesses=[];total_solved=0
for (group,month),raw in sorted(records.items()):
    days=sorted(raw)
    names=sorted(raw[days[0]])
    assert len(days)==31 and len(names) in (2,3)
    assert all(sorted(raw[d])==names for d in days)
    full=sums(raw,days,names)
    ref=shortlist(full,{k:1. for k in names})
    best=None;search_calls=0;lower_bounds=[]
    for n in range(1,L_MAX+1):
        for first in range(len(days)-n+1):
            keep=days[:first]+days[first+n:]
            assert len(keep)>=10
            reduced=sums(raw,keep,names)
            positive,calls,_=source_witness(full,reduced,names,ref,slack=SLACK)
            search_calls+=calls
            # Relax all strict margins to equality. This is a LOWER
            # feasibility bound on the true infimum; it can be loose.
            relaxed,calls2,_=source_witness(full,reduced,names,ref,slack=0.)
            search_calls+=calls2
            if relaxed is not None:lower_bounds.append(relaxed["epsilon"])
            if positive is None:continue
            positive.update(group=group,month=month,
                            gap_length=n,omitted_first=days[first],
                            omitted_last=days[first+n-1])
            if best is None or positive["epsilon"]<best["epsilon"]:
                best=positive
    total_solved+=search_calls
    old=[r for r in r26k if r["group"]==group and r["month"]==month]
    assert len(old)==7
    from_old={float(r["epsilon"]):int(r["anchored_gap_flip"]) for r in old}
    if best is None:
        assert from_old[.05]==0,(group,month,"No witness up to 5% conflicts R26K")
    else:
        # Closures and strict slacks may affect near-equality cells. Check
        # epsilon-grid classifications with mild tolerance and never claim
        # exact comparisons at solver precision.
        for e,flag in from_old.items():
            if flag==1 and e+5e-7 < best["epsilon"]:
                raise AssertionError(("R26K certified feasible yet critical threshold larger",group,month,e,best["epsilon"]))
            if flag==0 and e>best["epsilon"]+5e-7:
                raise AssertionError(("R26K reported no witness yet critical threshold smaller",group,month,e,best["epsilon"]))
    lower=min(lower_bounds) if lower_bounds else None
    if lower is not None and best is not None and lower>best["epsilon"]+2e-7:
        raise AssertionError(("relaxation gives larger infimum",group,month,lower,best["epsilon"]))
    rec=dict(group=group,month=month,tier=tiers[group],inverters=len(names),
        gap_support=L_MAX,q=Q,eps_cap=EPS_CAP,
        relaxation_lower_bound=round(lower,12) if lower is not None else None,
        certified_witness_epsilon=round(best["epsilon"],12) if best is not None else None,
        width=round(best["epsilon"]-lower,12) if best and lower is not None else None,
        witness_gap_length=(best["gap_length"] if best else None),
        witness_start=(best["omitted_first"] if best else None),
        nominal_source_fragile=from_old[0.],
        earlier_r26k_eps5_flag=from_old[.05],
        critical_status="WITNESS_WITHIN_5PCT" if best else "NO_POSITIVE_WITNESS_UP_TO_5PCT",
        total_LP_calls=search_calls)
    primary.append(rec)
    if best:witnesses.append(best)
    print("CRITICAL_MONTH",json.dumps(rec),flush=True)
assert len(primary)==12
def save(name,lines):
    with (O/name).open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=list(lines[0]))
        w.writeheader();w.writerows(lines)
save("R28_CRITICAL_EPSILON_MONTHS.csv",primary)
(O/"R28_EXPLICIT_CRITICAL_GAIN_WITNESSES.json").write_text(json.dumps(witnesses,indent=2))
assert len(witnesses)==9
# independent direct numerical witness recomputation against source-daily data.
for w in witnesses:
    key=(w["group"],w["month"])
    raw=records[key];days=sorted(raw);names=sorted(raw[days[0]])
    ref=sums(raw,days,names)
    subset=[d for d in days if not(w["omitted_first"]<=d<=w["omitted_last"])]
    assert len(subset)==len(days)-w["gap_length"]
    delete=sums(raw,subset,names)
    assert shortlist(ref,w["eta"])==shortlist(ref,{name:1. for name in names})
    assert shortlist(delete,w["eta"])!=shortlist(ref,w["eta"])
    assert all(abs(w["eta"][k]-1.)<=w["epsilon"]+1e-7 for k in names)

table=[]
for group in sorted(tiers):
    subgroup=[x for x in primary if x["group"]==group]
    table.append(dict(group=group,tier=tiers[group],months=len(subgroup),
        within5=sum(x["critical_status"]=="WITNESS_WITHIN_5PCT" for x in subgroup),
        point_fragile=sum(x["nominal_source_fragile"] for x in subgroup),
        critical_eps_percent_list="; ".join(
            (f'{100*x["certified_witness_epsilon"]:.4f}%' if x["certified_witness_epsilon"] is not None else ">5%/HOLD")
            for x in subgroup),
        months_list="; ".join(x["month"] for x in subgroup)))
save("R28_GROUP_CRITICAL_GAIN_SUMMARY.csv",table)
cert=dict(status="SOURCE_CONDITIONAL_COMPUTATION_PASS",
      source="HKUST original Zenodo 10909062",source_sha256=SOURCE_HASH,
      month_checks=len(primary),witnesses=len(witnesses),
      LP_calls=total_solved, q=Q,Lmax=L_MAX,cap=EPS_CAP,
      method="Exhaustive finite comparator assignments, strict positive-margin LP for fixed full-month shortlist; lower relaxed LP is boundary-sensitive",
      note="Critical epsilon describes an analytical envelope on unobserved relative gain factors, not actual instrument error.",
      preserve_r25=True,retain_r27_science=True,exclude_Qatar_QEERI=True)
(O/"R28_CRITICAL_MARGIN_CERTIFICATE.json").write_text(json.dumps(cert,indent=2))
(O/"SHA256SUMS.txt").write_text("".join(
    f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in sorted(O.iterdir()) if f.name!="SHA256SUMS.txt"))
print("R28_CRITICAL_MARGIN_PRIMARY_PASS",json.dumps(cert),flush=True)
