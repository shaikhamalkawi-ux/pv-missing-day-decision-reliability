#!/usr/bin/env python3
"""R26K prospective baseline-preserved calibration x contiguous-day omission gate.

Scientific distinction (nonprobabilistic and source-conditional):
- Point-only: eta_j=1 for all devices.
- Unrestricted R26J: full/gap decision changes under some fixed eta in a box.
- R26K: the SAME eta must retain the original full-month candidate set before
  any deletion, then a contiguous gap no longer than L changes that set.

The original source-native 144-slot HKUST daily powers are not imputed.
Primary output is development evidence only, not a fourth validated cohort.
"""
from pathlib import Path
from collections import defaultdict
from itertools import product
import csv, json, math, hashlib
from scipy.optimize import linprog
D=Path("r26i");J=Path("r26j");OUT=Path("R26K_BaselinePreserved")
OUT.mkdir(exist_ok=True)
Q=.05
EPS_GRID=[0.0,.0025,.005,.01,.02,.03,.05]
MAX_L=3
STRICT=1e-9
LP_OPTS={"primal_feasibility_tolerance":1e-10,"dual_feasibility_tolerance":1e-10}
def read(name,folder):
    with (folder/name).open("r",newline="",encoding="utf8") as f:return list(csv.DictReader(f))
source=read("DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv",D)
cohorts=read("CONDITIONAL_GROUP_COHORTS.csv",D)
full_grid=read("GROUP_MONTH_DECISION_GRID.csv",D)
tiers=read("SOURCE_BASED_TIER_REGISTER.csv",D)
prior=read("PER_MONTH_L1_L3_L7_COMPARISON.csv",J)
source_cert=json.loads((D/"CALCULATION_CERTIFICATE.json").read_text())
prior_cert=json.loads((J/"R26J_CALIBRATION_GAP_CERTIFICATE.json").read_text())
assert source_cert["status"]=="PASS_DEVELOPMENT_ONLY"
assert source_cert["sha256"]==prior_cert["source_SHA256"]
assert len(full_grid)==420 and len(prior)==36
assert source_cert["sha256"]=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
per=defaultdict(lambda:defaultdict(dict))
for r in source:
    k=(r["group"],r["month"])
    assert r["inverter"] not in per[k][r["date"]]
    per[k][r["date"]][r["inverter"]]=float(r["normalized_observed_sample_sum"])
assert len(per)==12
tier={r["group"]:r["quality_tier"] for r in tiers}
def shortlist(y,t):
    M=max(y[k]*t[k] for k in y)
    assert M>0
    return tuple(sorted(k for k in y if y[k]*t[k]>=(1-Q)*M))
def totals(vals,dates,dev):
    return {j:sum(vals[d][j] for d in dates) for j in dev}
def membership_intervals(full,dev,eps):
    certain=[];possible=[]
    for j in dev:
        other=[k for k in dev if k!=j]
        if (1-eps)*full[j] >= (1-Q)*max((1+eps)*full[k] for k in other):certain.append(j)
        if (1+eps)*full[j] >= (1-Q)*max((1-eps)*full[k] for k in other):possible.append(j)
    return tuple(certain),tuple(possible)

def anchored_lp(full,gap,devices,baseline,eps):
    """Linear feasibility, full-month exact categorical baseline retained.

    Original-baseline nonmembers require a strict exclusion competitor each.
    Those disjunctions are exhaustively enumerated, because n<=3.
    A gap flip occurs when a member becomes strictly out, or a previously
    excluded member becomes in. All purported witnesses are recomputed.
    """
    max_y=max(full.values());assert max_y>0
    f={j:full[j]/max_y for j in devices}
    g={j:gap[j]/max_y for j in devices}
    n=len(devices);ix={j:i for i,j in enumerate(devices)}
    inbase=[j for j in devices if j in baseline]
    outbase=[j for j in devices if j not in baseline]
    candidates=[tuple(k for k in devices if k!=j) for j in outbase]
    assignments=product(*candidates) if candidates else [()]
    bound=[(1-eps,1+eps)]*n
    calls=0
    for comps in assignments:
        A=[];b=[]
        for j in inbase:
            for k in devices:
                if j==k:continue
                r=[0.]*n
                r[ix[j]]=-f[j]
                r[ix[k]]=(1-Q)*f[k]
                A.append(r);b.append(0.)
        for j,k in zip(outbase,comps):
            r=[0.]*n
            r[ix[j]]=f[j]
            r[ix[k]]=-(1-Q)*f[k]
            A.append(r);b.append(-STRICT)
        for j in inbase:
            for k in devices:
                if j==k:continue
                # Maximize positive gap exclusion violation.
                obj=[0.]*n
                obj[ix[j]]=g[j]
                obj[ix[k]]=-(1-Q)*g[k]
                calls+=1
                res=linprog(obj,A_ub=A or None,b_ub=b or None,bounds=bound,
                            method="highs",options=LP_OPTS)
                if res.status==2:continue
                if res.status!=0:raise RuntimeError("LP failure "+str(res.message))
                if -float(res.fun)<=STRICT:continue
                theta={u:float(res.x[ix[u]]) for u in devices}
                base=shortlist(full,theta);deleted=shortlist(gap,theta)
                if base==baseline and deleted!=baseline:
                    return dict(theta=theta,full_shortlist=list(base),gap_shortlist=list(deleted),
                                change_direction="baseline_member_excluded_after_gap",member=j,challenger=k,
                                strict_gap_margin=-float(res.fun),lp_calls=calls)
        for j in outbase:
            # Feasibility for inclusion after deletion; support slack on all
            # competitor inequalities to avoid borderline false positives.
            A2=[r.copy() for r in A]
            b2=b.copy()
            for k in devices:
                if j==k:continue
                row=[0.]*n
                row[ix[j]]=-g[j]
                row[ix[k]]=(1-Q)*g[k]
                A2.append(row);b2.append(-STRICT)
            calls+=1
            res=linprog([0.]*n,A_ub=A2,b_ub=b2,bounds=bound,
                        method="highs",options=LP_OPTS)
            if res.status==2:continue
            if res.status!=0:raise RuntimeError("LP feasibility failed: "+res.message)
            theta={u:float(res.x[ix[u]]) for u in devices}
            base=shortlist(full,theta);deleted=shortlist(gap,theta)
            if base==baseline and deleted!=baseline:
                return dict(theta=theta,full_shortlist=list(base),gap_shortlist=list(deleted),
                            change_direction="baseline_excluded_member_in_after_gap",member=j,
                            strict_gap_margin=None,lp_calls=calls)
    return None

results=[];certs=[];witnesses=[]
for (group,month),meas in sorted(per.items()):
    dates=sorted(meas)
    assert len(dates)==31 and all(x.startswith(month) for x in dates),(group,month,len(dates))
    dev=sorted(meas[dates[0]])
    assert len(dev) in (2,3) and all(sorted(meas[d])==dev for d in dates)
    full=totals(meas,dates,dev)
    baseline=shortlist(full,{k:1. for k in dev})
    existing_l3=next(int(r["changed"]) for r in full_grid
                     if r["group"]==group and r["month"]==month and float(r["q"])==Q and int(r["L"])==3)
    prior_l3=next(int(r["exists_fixed_calibration_gap_flip"]) for r in prior
                  if r["group"]==group and r["month"]==month and int(r["L"])==3)
    previous_flag=None
    for eps in EPS_GRID:
        certain,possible=membership_intervals(full,dev,eps)
        identified=(certain==possible)
        found=None;cases=0
        if previous_flag is not None:
            # Epsilon boxes are nested. A previously verified witness is
            # still feasible; reuse under the broader box.
            found=previous_flag.copy()
            assert all(1-eps-1e-12<=v<=1+eps+1e-12 for v in found["theta"].values())
        else:
            for ln in range(1,MAX_L+1):
                for i in range(len(dates)-ln+1):
                    if len(dates)-ln<10:continue
                    remain=dates[:i]+dates[i+ln:]
                    gap=totals(meas,remain,dev)
                    cases+=1
                    v=anchored_lp(full,gap,dev,baseline,eps)
                    if v is not None:
                        found=dict(group=group,month=month,epsilon=eps,length=ln,
                                omitted_start=dates[i],omitted_end=dates[i+ln-1],**v)
                        break
                if found is not None:break
        if found is not None:
            previous_flag=found.copy()
            theta=found["theta"]
            removed=[d for d in dates if not(found["omitted_start"]<=d<=found["omitted_end"])]
            assert shortlist(full,theta)==baseline
            assert shortlist(totals(meas,removed,dev),theta)!=baseline
            if eps==0.:assert existing_l3==1
        flag=int(found is not None)
        if eps==0.:assert flag==existing_l3,(group,month,flag,existing_l3)
        if eps==.05:assert flag<=prior_l3,(group,month,flag,prior_l3)
        row=dict(group=group,month=month,source_grade=tier[group],
                 epsilon=eps,q=Q,max_L=MAX_L,n_days=len(dates),n_inverters=len(dev),
                 point_fragile=existing_l3,
                 unrestricted_R26J_epsilon5_fragile=prior_l3,
                 baseline_identified=int(identified),
                 baseline_certain=";".join(certain),
                 baseline_possible=";".join(possible),
                 anchored_gap_flip=flag,first_witness_gap_days=(found["length"] if found else ""),
                 direct_LP_gap_tests=cases)
        results.append(row)
        if found is not None and found["epsilon"]==eps:witnesses.append(found)
        print("R26K_GRID_ROW",json.dumps(row),flush=True)
assert len(results)==12*len(EPS_GRID)
for (group,month),_ in per.items():
    rows=[r for r in results if r["group"]==group and r["month"]==month]
    flags=[r["anchored_gap_flip"] for r in rows]
    assert flags==sorted(flags),(group,month,"epsilon monotonicity")
group_sums=[]
for group in sorted(tier):
    for eps in EPS_GRID:
        subset=[r for r in results if r["group"]==group and r["epsilon"]==eps]
        assert subset
        group_sums.append(dict(group=group,source_grade=tier[group],epsilon=eps,
            months=len(subset),point_fragile=sum(r["point_fragile"] for r in subset),
            baseline_ambiguous=sum(1-r["baseline_identified"] for r in subset),
            baseline_preserving_gap_flips=sum(r["anchored_gap_flip"] for r in subset)))
def csvout(name,rows):
    with (OUT/name).open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
csvout("SOURCE_MONTH_EPSILON_BASELINE_GATE.csv",results)
csvout("GROUP_EPSILON_SENSITIVITY.csv",group_sums)
(OUT/"BASELINE_PRESERVED_CONCRETE_WITNESSES.json").write_text(json.dumps(witnesses,indent=2))
cert=dict(status="DEVELOPMENT_PASS_PENDING_INDEPENDENT_CHECK",
          source="HKUST Zenodo 10909062 original",
          source_sha=source_cert["sha256"],
          q=Q,L_max=3,EPS_GRID=EPS_GRID,
          measurement_model="Fixed source-month eta_j per inverter, same gain in reference and all gaps, eta_j in [1-eps,1+eps]",
          baseline_preservation="The full-month shortlist MUST exactly equal recorded-source full-month shortlist for the same eta used to stress deletions",
          source_months=len(per),rows=len(results),group_cells=len(group_sums),
          epsilon_monotonicity=True,point_flag_crosscheck_12of12=True,
          no_qatar=True,R25_SE1_unchanged=True,
          caveat="Sensitivity envelope is NOT a calibrated probability, independently measured error model or a new theorem")
(OUT/"R26K_PRIMARY_CERTIFICATE.json").write_text(json.dumps(cert,indent=2))
print("R26K_PRIMARY_GATE",json.dumps(cert),flush=True)
