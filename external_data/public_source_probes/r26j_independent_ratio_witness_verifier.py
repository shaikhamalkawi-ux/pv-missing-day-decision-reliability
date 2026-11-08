#!/usr/bin/env python3
"""Independent R26J readback and 2-device analytic-ratio verification.

Does not use scipy or the primary LP function. The independent two-inverter
geometric test finds whether fixed relative calibration rho=theta1/theta2
has any admissible value in [0.95/1.05,1.05/0.95] such that deletion
changes one shortlist member. Candidate-set thresholds in ratio space
are exactly 1-q and 1/(1-q); evaluate every open cell midpoint and boundary.

For three-inverter groups verify actual certified LP theta witnesses
against original derived daily sums independently, without solver libraries.
"""
import collections,csv,json,hashlib,math,calendar
from pathlib import Path
S=Path("source");R=Path("result");O=Path("R26J_IndependentReadback")
O.mkdir(exist_ok=True)
Q=.05; E=.05; TOL=1e-8
def csvrows(p):
    with p.open("r",newline="",encoding="utf8") as f:return list(csv.DictReader(f))
data=csvrows(S/"DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
month=csvrows(R/"PER_MONTH_CALIBRATION_AND_DELETION_GATES.csv")
rows=csvrows(R/"PER_MONTH_L1_L3_L7_COMPARISON.csv")
witnesses=json.loads((R/"EXPLICIT_SHARED_CALIBRATION_LP_WITNESSES.json").read_text())
certificate=json.loads((R/"R26J_CALIBRATION_GAP_CERTIFICATE.json").read_text())
assert certificate["source_SHA256"]=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
assert len(month)==12 and len(rows)==36
orig=collections.defaultdict(lambda:collections.defaultdict(dict))
for row in data:
    key=(row["group"],row["month"])
    date=row["date"];device=row["inverter"]
    assert device not in orig[key][date]
    orig[key][date][device]=float(row["normalized_observed_sample_sum"])

def sum_y(month,dates,devs):
    return {name:sum(month[d][name] for d in dates) for name in devs}

def set_y(y,q,theta):
    M=max(y[n]*theta[n] for n in y)
    return tuple(sorted(n for n in y if y[n]*theta[n]>=(1-q)*M))

def get_theta(rho,lo=1-E,hi=1+E):
    low=max(lo,lo/rho);high=min(hi,hi/rho)
    if low>high+1e-12:return None
    y=(low+high)/2
    x=rho*y
    if x<lo-1e-11 or x>hi+1e-11:return None
    return (x,y)

def robust_set_difference(ref,gap,theta,devs,q):
    a=set_y(ref,q,theta);b=set_y(gap,q,theta)
    if a==b:return False
    scale=max(ref.values())
    for j in devs:
        if (j in a)==(j in b):continue
        rest=[k for k in devs if k!=j]
        state_in=ref if j in a else gap
        state_out=gap if j in a else ref
        i_m=theta[j]*state_in[j]-(1-q)*max(theta[k]*state_in[k] for k in rest)
        o_m=(1-q)*max(theta[k]*state_out[k] for k in rest)-theta[j]*state_out[j]
        if i_m/scale>TOL and o_m/scale>TOL:return True
    return False

def ratios_source_has_flip(ref,gap,devs,q):
    assert len(devs)==2
    x,y=devs
    if ref[y]<=0 or gap[y]<=0 or ref[x]<=0 or gap[x]<=0:
        raise AssertionError("Unexpected nonpositive monthly y")
    rf=ref[x]/ref[y];rg=gap[x]/gap[y]
    lo=(1-E)/(1+E);hi=(1+E)/(1-E)
    cutoff=(1-q,1/(1-q))
    bounds=[lo,hi]
    for rt in (rf,rg):
        for threshold in cutoff:
            p=threshold/rt
            if lo<p<hi:bounds.append(p)
    bounds=sorted(set(bounds))
    points=bounds.copy()
    points.extend((bounds[i]+bounds[i+1])/2 for i in range(len(bounds)-1))
    for rho in sorted(set(points)):
        xy=get_theta(rho)
        if xy is None:continue
        theta=dict(zip(devs,xy))
        if robust_set_difference(ref,gap,theta,devs,q):return True
    return False

evidence=[]
for rec in month:
    group,ym=rec["group"],rec["month"]
    local=orig[(group,ym)];days=sorted(local);devs=sorted(local[days[0]])
    full=sum_y(local,days,devs)
    orig_len=rec["minimum_gap_with_some_fixed_independent_calibration"]
    want=(None if not orig_len else int(orig_len))
    if len(devs)==2:
        found=None
        for ln in range(1,8):
            for first in range(len(days)-ln+1):
                remain=days[:first]+days[first+ln:]
                gap=sum_y(local,remain,devs)
                if ratios_source_has_flip(full,gap,devs,Q):
                    found=ln
                    break
            if found is not None:break
        if found != want:
            raise AssertionError(("independent analytical ratio vs LP mismatch",group,ym,found,want))
        evidence.append(dict(group=group,month=ym,method="INDEPENDENT_EXACT_TWO_DEVICE_RATIO_PARTITION",
                             source_minimum_gap=want,verified_gap=found,status="PASS"))
    else:
        w=next((x for x in witnesses if x["group"]==group and x["month"]==ym),None)
        if want is None:
            evidence.append(dict(group=group,month=ym,method="SOURCE_LP_FULL_SEARCH_NO_WITNESS",
                                 source_minimum_gap=None,verified_gap=None,status="LP_ONLY"))
        else:
            assert w is not None and int(w["length"])==want
            start=w["omitted_start"];end=w["omitted_end"]
            assert start in days and end in days
            indices=[i for i,d in enumerate(days) if start<=d<=end]
            assert len(indices)==want and indices==list(range(indices[0],indices[0]+want))
            remain=[d for d in days if not(start<=d<=end)]
            gap=sum_y(local,remain,devs)
            theta=w["factors"]
            assert set(theta)==set(devs)
            assert all(1-E-1e-9<=theta[x]<=1+E+1e-9 for x in theta)
            assert robust_set_difference(full,gap,theta,devs,Q),(group,ym,w)
            evidence.append(dict(group=group,month=ym,method="INDEPENDENT_THREE_DEVICE_EXPLICIT_WITNESS_RECOMPUTATION",
                                 source_minimum_gap=want,verified_gap=int(w["length"]),status="PASS"))

assert all(r["status"]=="PASS" for r in evidence)
assert len(evidence)==12
for r in rows:
    want=next(x for x in evidence if x["group"]==r["group"] and x["month"]==r["month"])
    L=int(r["L"]);expected=int(want["verified_gap"] is not None and int(want["verified_gap"])<=L)
    assert expected==int(r["exists_fixed_calibration_gap_flip"]) if "exists_fixed_calibration_gap_flip" in r else expected==int(r["exists_fixed_independent_calibration_gap_flip"])
with (O/"INDEPENDENT_MATH_CROSSCHECK.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(evidence[0]))
    w.writeheader();w.writerows(evidence)
cert=dict(independent_checks=len(evidence),two_inverter_exact_ratio_count=sum(x["method"].startswith("INDEPENDENT_EXACT") for x in evidence),
          three_inverter_source_witness_direct_checks=sum("THREE_DEVICE" in x["method"] for x in evidence),
          results="PASS",sample="12 source-months, q=5%, 1-to-7-day stress",
          no_qatar=True,original_r25_unchanged=True,
          important="This verifies existence under fixed, independently bounded per-device gain factors; it cannot certify the actual measured calibration.")
(O/"INDEPENDENT_R26J_REPRODUCIBILITY.json").write_text(json.dumps(cert,indent=2))
(O/"SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(O.iterdir()) if p.name!="SHA256SUMS.txt"))
print("R26J_INDEPENDENT_RATIO_AND_WITNESS_AUDIT_PASS",json.dumps(cert),flush=True)
