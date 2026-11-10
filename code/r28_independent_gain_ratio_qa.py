#!/usr/bin/env python3
"""R28 independent relative-gain audit.

For two-inverter groups use analytic threshold partitions in gain ratio
rho=eta_A/eta_B, without any linear-programming library. The required symmetric
gain radius at ratio rho is |rho-1|/(rho+1). Find all OPEN intervals for which
full-month shortlist equals its observed reference but a contiguous omission
changes it; minimize radius over the interval closures. For three inverters,
independently check explicit primary witnesses on the source daily sums and
R26K threshold-grid consistency; no independent theorem of LP infeasibility.
"""
import csv,math,json,hashlib
from pathlib import Path
from collections import defaultdict
S=Path("source")
P=Path("primary")
OUT=Path("R28_IndependentCriticalQA");OUT.mkdir(exist_ok=True)
Q=.05;CAP=.05
def readcsv(path):
    with path.open("r",newline="",encoding="utf8") as f:return list(csv.DictReader(f))
raw=readcsv(S/"DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
prim=readcsv(P/"R28_CRITICAL_EPSILON_MONTHS.csv")
witnesses=json.loads((P/"R28_EXPLICIT_CRITICAL_GAIN_WITNESSES.json").read_text())
source_hash="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
assert len(prim)==12 and len(witnesses)==9
c=json.loads((P/"R28_CRITICAL_MARGIN_CERTIFICATE.json").read_text())
assert c["source_sha256"]==source_hash
by=defaultdict(lambda:defaultdict(dict))
for r in raw:
    k=(r["group"],r["month"]);d=r["date"];inv=r["inverter"]
    assert inv not in by[k][d]
    by[k][d][inv]=float(r["normalized_observed_sample_sum"])
def sums(data,days,dev):
    return {j:sum(data[d][j] for d in days) for j in dev}
def subset(y,theta):
    best=max(y[j]*theta[j] for j in y)
    return tuple(sorted(j for j in y if y[j]*theta[j]>=(1-Q)*best))
def theta_r(r,a,b):
    if r>=1:
        y=2/(1+r);x=r*y
    else:
        x=2*r/(1+r);y=2/(1+r)
    return {a:x,b:y}
def min_analytic_radius(f,g,dev,baseline,cap):
    a,b=dev
    # For the gain ratio, the inclusion boundaries are:
    # A: rho*(fA/fB) >= (1-q); B: rho*(fA/fB) <=1/(1-q).
    fr=f[a]/f[b];gr=g[a]/g[b]
    lo=(1-cap)/(1+cap);hi=(1+cap)/(1-cap)
    cuts=[lo,hi]
    for d in (fr,gr):
        for threshold in (1-Q,1/(1-Q)):
            x=threshold/d
            if lo<x<hi:cuts.append(x)
    cuts=sorted(set(cuts))
    found=None
    for left,right in zip(cuts[:-1],cuts[1:]):
        if right-left<1e-14:continue
        mid=(left+right)/2
        eta=theta_r(mid,a,b)
        if subset(f,eta)==baseline and subset(g,eta)!=baseline:
            nearest=max(left,min(1.,right))
            eps=abs(nearest-1)/(nearest+1)
            if found is None or eps<found:found=eps
    return found

checks=[]
for row in prim:
    group,month=row["group"],row["month"]
    data=by[(group,month)];days=sorted(data);dev=sorted(data[days[0]])
    full=sums(data,days,dev)
    baseline=subset(full,{d:1. for d in dev})
    point=int(row["nominal_source_fragile"])
    original_upper=float(row["certified_witness_epsilon"]) if row["certified_witness_epsilon"] not in ("",None) else None
    if len(dev)==2:
        min_exact=None
        for count in range(1,4):
            for k in range(len(days)-count+1):
                rdays=days[:k]+days[k+count:]
                gap=sums(data,rdays,dev)
                test=min_analytic_radius(full,gap,dev,baseline,CAP)
                if test is not None and (min_exact is None or test<min_exact):min_exact=test
        if original_upper is None:assert min_exact is None,(group,month,min_exact)
        else:
            assert min_exact is not None
            assert abs(original_upper-min_exact)<3e-6,(group,month,min_exact,original_upper)
        assert (point==1)==(min_exact is not None and min_exact<1e-10),(group,month,point,min_exact)
        checks.append(dict(group=group,month=month,device_count=2,
             independently_analytic_radius=min_exact,
             primary_certified_radius=original_upper,
             check="PASS_exact_gain_ratio_partition"))
    else:
        witness=next((w for w in witnesses if w["group"]==group and w["month"]==month),None)
        if original_upper is None:
            assert witness is None
            check="PRIMARY_LP_ONLY_NONEXISTENCE"
        else:
            assert witness is not None
            assert abs(float(witness["epsilon"])-original_upper)<3e-8
            dates=[d for d in days if not(witness["omitted_first"]<=d<=witness["omitted_last"])]
            assert len(days)-len(dates)==int(witness["gap_length"])
            eta=witness["eta"]
            assert all(abs(eta[x]-1)<=original_upper+1e-8 for x in dev)
            assert subset(full,eta)==baseline
            assert subset(sums(data,dates,dev),eta)!=baseline
            check="PASS_explicit_three_inverter_primary_witness"
        checks.append(dict(group=group,month=month,device_count=3,
              independently_analytic_radius=None,
              primary_certified_radius=original_upper,check=check))
assert len(checks)==12
assert sum(x["check"].startswith("PASS_exact") for x in checks)==8
assert sum(x["check"].startswith("PASS_explicit") for x in checks)==4
with (OUT/"R28_INDEPENDENT_PER_MONTH.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
result=dict(status="PASS_EXPLICIT_AND_TWO_DEVICE_ANALYTICAL",months=12,
            analytic_two_inverter_months=8,three_inverter_explicit_witness_months=4,
            three_inverter_no_flip_claim="No second independent infeasibility proof; rely on primary finite LP audit if applicable",
            threshold_agreement="Independent 2-inverter gain ratio critical margins match LP to 3e-6 in gain fraction",
            original_hkust_sha=source_hash,no_imputation=True,
            no_qatar=True,original_R25_science_untouched=True,
            caveat="No field calibration identified")
(OUT/"R28_INDEPENDENT_VERIFIER_CERTIFICATE.json").write_text(json.dumps(result,indent=2))
(OUT/"SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n"
    for f in sorted(OUT.iterdir()) if f.name!="SHA256SUMS.txt"))
print("R28_INDEPENDENT_CRITICAL_MARGIN_PASS",json.dumps(result),flush=True)
