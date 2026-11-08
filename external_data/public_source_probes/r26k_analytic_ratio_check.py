#!/usr/bin/env python3
"""R26K independent validation without scipy.

For every two-inverter source-month at each epsilon, partition the admissible
ratio theta_1/theta_2 at the exact shortlist threshold crossings in the source
full month and each possible contiguous gap of up to three days.  Check each
open cell and each threshold separately. For three-inverter cases, directly
recompute source baseline and gap witness with the published factors.

The source is the original R26I derived observation matrix, not new imputation.
"""
import csv,json,math,hashlib,collections
from pathlib import Path
SOURCE=Path("r26i");TEST=Path("r26k");OUT=Path("R26K_IndependentRatioQA");OUT.mkdir(exist_ok=True)
Q=.05
def rows(folder,name):
    with (folder/name).open("r",newline="",encoding="utf8") as f:return list(csv.DictReader(f))
source=rows(SOURCE,"DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
grid=rows(TEST,"SOURCE_MONTH_EPSILON_BASELINE_GATE.csv")
witnesses=json.loads((TEST/"BASELINE_PRESERVED_CONCRETE_WITNESSES.json").read_text())
cert=json.loads((TEST/"R26K_PRIMARY_CERTIFICATE.json").read_text())
assert cert["source_sha"]=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
assert cert["no_qatar"] and cert["R25_SE1_unchanged"]
per=collections.defaultdict(lambda:collections.defaultdict(dict))
for r in source:
    key=(r["group"],r["month"]);dev=r["inverter"];d=r["date"]
    per[key][d][dev]=float(r["normalized_observed_sample_sum"])
def sums(daydata,dates,dev):
    return {k:sum(daydata[d][k] for d in dates) for k in dev}
def candidates(y,t):
    M=max(y[k]*t[k] for k in y)
    return tuple(sorted(k for k in y if y[k]*t[k]>=(1-Q)*M))
def theta_for_ratio(r,epsilon,dev):
    lo=1-epsilon;hi=1+epsilon
    lower=max(lo,lo/r);upper=min(hi,hi/r)
    if lower>upper+1e-12:return None
    b=(lower+upper)/2
    a=r*b
    if min(a,b)<lo-1e-10 or max(a,b)>hi+1e-10:return None
    return {dev[0]:a,dev[1]:b}
def strong_flip(ref,gap,theta,dev,baseline,margin=5e-10):
    """Independent numerical separation from every membership boundary."""
    scale=max(ref.values())
    for j in dev:
        others=[k for k in dev if k!=j]
        score=ref[j]*theta[j]-(1-Q)*max(ref[k]*theta[k] for k in others)
        if j in baseline and score < margin*scale:return False
        if j not in baseline and score > -margin*scale:return False
    old=candidates(ref,theta);new=candidates(gap,theta)
    if old!=baseline or new==baseline:return False
    for j in dev:
        if (j in baseline)==(j in new):continue
        score=gap[j]*theta[j]-(1-Q)*max(gap[k]*theta[k] for k in dev if k!=j)
        if j in baseline and score > -margin*scale:return False
        if j not in baseline and score < margin*scale:return False
        return True
    return False

def analytic_exists(ref,gap,devices,eps,baseline):
    assert len(devices)==2
    a,b=devices
    ratio_full=ref[a]/ref[b]
    ratio_gap=gap[a]/gap[b]
    assert ratio_full>0 and ratio_gap>0
    lo=(1-eps)/(1+eps)
    hi=(1+eps)/(1-eps)
    points=[lo,hi]
    for x in (ratio_full,ratio_gap):
        points+=[v/x for v in (1-Q,1/(1-Q)) if lo<v/x<hi]
    points=sorted(set(points))
    trials=set(points)
    for x,y in zip(points[:-1],points[1:]):
        trials.add((x+y)/2)
    # Include small nearby perturbations in case exact equality causes
    # different inclusion semantics (>=) than strict exclusion.
    for p in points:
        for delta in (-1,1):
            x=p*(1+delta*1e-10)
            if lo<=x<=hi:trials.add(x)
    for r in sorted(trials):
        theta=theta_for_ratio(r,eps,devices)
        if theta is None:continue
        if strong_flip(ref,gap,theta,devices,baseline):
            return theta
    return None
checks=[];two_count=0;three_count=0
for (group,month),data in sorted(per.items()):
    dates=sorted(data);dev=sorted(data[dates[0]])
    full=sums(data,dates,dev)
    original=candidates(full,{k:1. for k in dev})
    for gridrow in [r for r in grid if r["group"]==group and r["month"]==month]:
        eps=float(gridrow["epsilon"]);assert eps in cert["EPS_GRID"]
        source_flag=int(gridrow["anchored_gap_flip"])
        sourcew=next((w for w in witnesses if w["group"]==group and w["month"]==month and
                      float(w["epsilon"])<=eps and
                      w["full_shortlist"]==list(original)),None)
        if len(dev)==2:
            found=None
            for ln in range(1,4):
                for start in range(len(dates)-ln+1):
                    subset=dates[:start]+dates[start+ln:]
                    gap=sums(data,subset,dev)
                    theta=analytic_exists(full,gap,dev,eps,original)
                    if theta is not None:
                        found=(ln,start,theta);break
                if found:break
            independent=int(found is not None)
            if independent!=source_flag:
                print("R26K_DIAGNOSTIC",json.dumps({"group":group,"month":month,"epsilon":eps,
                    "ref":full,"baseline":original,"independent":independent,
                    "source_flag":source_flag,"found":found,"source_cert_row":gridrow}),flush=True)
                raise AssertionError(("analytic 2-device mismatch",group,month,eps,independent,source_flag))
            if found:
                n,start,theta=found
                assert strong_flip(full,sums(data,dates[:start]+dates[start+n:],dev),theta,dev,original)
            checks.append(dict(group=group,month=month,epsilon=eps,devices=2,
                source_flag=source_flag,independent_flag=independent,
                method="exact_ratio_interval_partition",status="PASS"))
            two_count+=1
        else:
            if source_flag:
                assert sourcew is not None,(group,month,eps)
                theta=sourcew["theta"]
                assert all(1-eps-1e-10<=float(x)<=1+eps+1e-10 for x in theta.values())
                start=sourcew["omitted_start"];end=sourcew["omitted_end"]
                after=[d for d in dates if not(start<=d<=end)]
                assert len(dates)-len(after)==int(sourcew["length"])
                assert strong_flip(full,sums(data,after,dev),theta,dev,original)
            checks.append(dict(group=group,month=month,epsilon=eps,devices=3,
                source_flag=source_flag,independent_flag=(source_flag if source_flag else ""),
                method=("three_device_explicit_witness" if source_flag else
                        "negative_lp_only_not_independent"),status=("PASS" if source_flag else "LP_ONLY")))
            if source_flag:three_count+=1
assert len(checks)==len(grid)==84
with (OUT/"INDEPENDENT_RATIO_AND_WITNESS_GRID.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
outcert=dict(source_version="HKUST Zenodo 10909062 original",source_checksum=cert["source_sha"],
    exact_2device_analytic_cells=two_count,three_device_explicit_positive_witnesses=three_count,
    three_device_negative_cases="LP-only, not claimed independent proof of absence",
    all_2device_cells_matched=True,all_recorded_positive_witnesses_valid=True,
    no_qatar=True,r25_se1_unchanged=True)
(OUT/"R26K_INDEPENDENT_QA_CERTIFICATE.json").write_text(json.dumps(outcert,indent=2))
(OUT/"SHA256SUMS.txt").write_text("".join(
  f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n"
  for f in sorted(OUT.iterdir()) if f.is_file() and f.name!="SHA256SUMS.txt"))
print("R26K_INDEPENDENT_QA_PASS",json.dumps(outcert),flush=True)
