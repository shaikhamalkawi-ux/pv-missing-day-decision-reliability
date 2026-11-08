#!/usr/bin/env python3
"""R26J systematic relative-calibration vs missing-day stress (HKUST).

Independent development-only analytical extension to R26I; no changes to locked
R22/R25 publication. Data: source-verified daily sums, original-source RDF
DC-STC capacities. Each candidate's bounded multiplicative factor theta_j
is fixed across reference and every missing-day counterfactual for that month.
theta_j in [0.95,1.05]; this is a deliberately conservative analytical
stress informed by reported +/-5% calculated-power accuracy, NOT a calibrated
independent measurement error distribution, confidence interval, or probability.

Check existence of any theta-vector in the box that changes one candidate's
set membership after a contiguous deletion, using linear programs with exact
inclusion inequalities and strict exclusion objective. No imputation.

Journal source: Lin et al. (2025), Scientific Data 12, 63, doi:
10.1038/s41597-025-04397-y. Publisher's ±5% derived generation power accuracy.
"""
import collections, csv, json, math, hashlib
from pathlib import Path
from scipy.optimize import linprog

INPUT = Path("input")
OUT = Path("R26J_HKUST_CalibrationGapAudit")
OUT.mkdir(exist_ok=True)
Q = 0.05
EPS = 0.05
ABS_VIOL = 1e-8
INSIDE_SLACK = 1e-8
SOLVER_OPTIONS = {"primal_feasibility_tolerance": 1e-10,
                  "dual_feasibility_tolerance": 1e-10}
DAYS_FN = "DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv"
SOURCE_SHA = "610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"

def rows(fn):
    with (INPUT / fn).open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

day_rows = rows(DAYS_FN)
cohort_rows = rows("CONDITIONAL_GROUP_COHORTS.csv")
grid_rows = rows("GROUP_MONTH_DECISION_GRID.csv")
source_tier_rows = rows("SOURCE_BASED_TIER_REGISTER.csv")
r26i_cert = json.loads((INPUT / "CALCULATION_CERTIFICATE.json").read_text())
r26i_independent = json.loads((INPUT / "INDEPENDENT_ARITHMETIC_VERIFICATION.json").read_text())
assert r26i_cert["sha256"] == SOURCE_SHA
assert r26i_cert["status"] == "PASS_DEVELOPMENT_ONLY"
assert r26i_independent["pass"] is True
assert len(grid_rows) == 420
tier = {r["group"]:r["quality_tier"] for r in source_tier_rows}
assert len(tier) == 5
by_month = collections.defaultdict(lambda:collections.defaultdict(dict))
for r in day_rows:
    group,month,day,inv = r["group"],r["month"],r["date"],r["inverter"]
    assert inv not in by_month[(group,month)][day],(group,month,day,inv)
    p=float(r["normalized_observed_sample_sum"])
    assert math.isfinite(p)
    by_month[(group,month)][day][inv] = p
assert len(by_month) == 12, len(by_month)

def shortlist(y,q,theta):
    mx = max(y[k]*theta[k] for k in y)
    assert mx>0
    return tuple(sorted(k for k in y if y[k]*theta[k] >= (1-q)*mx))

def baseline_ambiguity(y,q,eps):
    devices=list(y)
    certain=[];possible=[]
    for j in devices:
        rest=[k for k in devices if k!=j]
        worst_comp=max((1+eps)*y[k] for k in rest)
        best_comp=max((1-eps)*y[k] for k in rest)
        if (1-eps)*y[j] >= (1-q)*worst_comp:
            certain.append(j)
        if (1+eps)*y[j] >= (1-q)*best_comp:
            possible.append(j)
    return tuple(sorted(certain)),tuple(sorted(possible))

def find_flip_lp(ref,gap,devices,q,eps):
    """Feasibility witness of shortlist membership change under the SAME theta in full and gap.

    Direction 1: j is admitted in reference, excluded in gap by some k.
    Direction 2: j excluded in reference by k, admitted in gap.
    Inclusion requires n-1 linear half-spaces.
    Strict exclusion is obtained by max'ing positive threshold violation.
    """
    scale=max(ref.values())
    assert scale>0
    a={j:ref[j]/scale for j in devices}
    b={j:gap[j]/scale for j in devices}
    n=len(devices); idx={k:i for i,k in enumerate(devices)}
    bounds=[(1-eps,1+eps)]*n
    opts=SOLVER_OPTIONS
    max_attempts=0
    for direction in ("full_in_gap_out","gap_in_full_out"):
        inside,outside=(a,b) if direction=="full_in_gap_out" else (b,a)
        for j in devices:
            A=[]
            for k in devices:
                if j==k:continue
                # -theta_j*inside_j + (1-q)*theta_k*inside_k <= 0
                r=[0.0]*n
                r[idx[j]]=-inside[j]
                r[idx[k]]=(1-q)*inside[k]
                A.append(r)
            for k in devices:
                if k==j:continue
                # minimize theta_j*outside_j - (1-q)*theta_k*outside_k
                c=[0.0]*n
                c[idx[j]]=outside[j]
                c[idx[k]]=-(1-q)*outside[k]
                max_attempts+=1
                result=linprog(c,A_ub=A,b_ub=[-INSIDE_SLACK]*len(A),
                               bounds=bounds,method="highs",options=opts)
                if result.status == 2:
                    continue # infeasible inside-membership constraints
                if result.status != 0:
                    raise RuntimeError(f"LP status={result.status}, {result.message}")
                positive_violation=-float(result.fun)
                if positive_violation<=ABS_VIOL:continue
                factors={name:float(result.x[idx[name]]) for name in devices}
                full_set=shortlist(ref,q,factors)
                gap_set=shortlist(gap,q,factors)
                if (full_set==gap_set or
                    not all(1-eps-1e-9<=v<=1+eps+1e-9 for v in factors.values())):
                    continue  # Boundary-roundoff/non-robust optimizer point, do not assert a witness
                return dict(direction=direction,member_j=j,witness_k=k,
                            normalized_violation=positive_violation,
                            factors=factors,
                            full_shortlist=list(full_set),
                            gap_shortlist=list(gap_set),
                            solver_attempts=max_attempts)
    return None

def numeric_daily_table(data,days,devices):
    return {name:sum(data[d][name] for d in days) for name in devices}

member_rows=[];cert_rows=[];witnesses=[]
for (group,month),data in sorted(by_month.items()):
    dates=sorted(data)
    assert len(dates) in (28,29,30,31), (group,month,len(dates))
    assert all(d.startswith(month) for d in dates)
    devices=sorted(data[dates[0]])
    assert all(sorted(data[d])==devices for d in dates)
    full=numeric_daily_table(data,dates,devices)
    point_theta={j:1.0 for j in devices}
    full_point=shortlist(full,Q,point_theta)
    certain,possible=baseline_ambiguity(full,Q,EPS)
    assert set(certain).issubset(set(possible))
    # Exhaustive finite deletion search by increasing gap length.
    point_length=None
    cal_length=None
    cal_witness=None
    checked_gaps=0
    verified_lp_evaluations=0
    for length in range(1,8):
        if point_length is not None and cal_length is not None:break
        for start in range(len(dates)-length+1):
            if len(dates)-length<10:continue
            retained=dates[:start]+dates[start+length:]
            gap=numeric_daily_table(data,retained,devices)
            if point_length is None and shortlist(gap,Q,point_theta)!=full_point:
                point_length=length
            if cal_length is None:
                check=find_flip_lp(full,gap,devices,Q,EPS)
                verified_lp_evaluations+=1
                if check is not None:
                    cal_length=length
                    cal_witness=dict(group=group,month=month,
                        omitted_start=dates[start],
                        omitted_end=dates[start+length-1],
                        length=length,**check)
            checked_gaps+=1
            if point_length is not None and cal_length is not None:break
    # Compare EXACT original point fragility counts per source month:
    original=[r for r in grid_rows if
              r["group"]==group and r["month"]==month and float(r["q"])==Q]
    assert len(original)==7
    for r in original:
        L=int(r["L"])
        check=int(point_length is not None and point_length<=L)
        if int(r["changed"])!=check:
            raise AssertionError(("POINT R26I mismatch",group,month,L,r["changed"],check))
    if point_length is not None:
        assert cal_length is not None and cal_length<=point_length
    row=dict(group=group,month=month,quality_tier=tier[group],
             n_devices=len(devices),n_days=len(dates),q=Q,
             baseline_point_set=";".join(full_point),
             baseline_certain_members=";".join(certain),
             baseline_possible_members=";".join(possible),
             baseline_set_identified=int(certain==possible),
             minimum_point_gap_to_change=point_length if point_length is not None else "",
             minimum_gap_with_some_fixed_independent_calibration=cal_length if cal_length is not None else "",
             tested_observed_gap_cases=checked_gaps,
             lp_gap_cases_executed=verified_lp_evaluations,
             calibration_half_width=EPS,
             threshold_violation_min=ABS_VIOL)
    member_rows.append(row)
    if cal_witness is not None:witnesses.append(cal_witness)
    for L in (1,3,7):
        cert_rows.append(dict(group=group,month=month,tier=tier[group],q=Q,L=L,
           point_fragile=int(point_length is not None and point_length<=L),
           exists_fixed_calibration_gap_flip=int(cal_length is not None and cal_length<=L),
           full_reference_baseline_identified=int(certain==possible)))
    print("MONTH",json.dumps(row),flush=True)

for row in member_rows:
    if row["minimum_point_gap_to_change"]:
        assert row["minimum_gap_with_some_fixed_independent_calibration"] not in ("",None)
assert len(member_rows)==12 and len(cert_rows)==36

def save_csv(filename,arr):
    with (OUT/filename).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(arr[0]))
        w.writeheader();w.writerows(arr)
save_csv("PER_MONTH_CALIBRATION_AND_DELETION_GATES.csv",member_rows)
save_csv("PER_MONTH_L1_L3_L7_COMPARISON.csv",cert_rows)
(OUT/"EXPLICIT_SHARED_CALIBRATION_LP_WITNESSES.json").write_text(json.dumps(witnesses,indent=2))
group_totals=[]
for group in sorted({r["group"] for r in member_rows}):
    rs=[r for r in member_rows if r["group"]==group]
    for L in (1,3,7):
        ds=[r for r in cert_rows if r["group"]==group and r["L"]==L]
        group_totals.append(dict(group=group,tier=tier[group],q=Q,L=L,
               months=len(ds),point_fragile=sum(r["point_fragile"] for r in ds),
               exists_fixed_independent_calibration_flip=sum(r["exists_fixed_calibration_gap_flip"] for r in ds),
               baseline_unidentified=sum(not r["full_reference_baseline_identified"] for r in ds)))
save_csv("SOURCE_GROUP_CALIBRATION_SENSITIVITY.csv",group_totals)
cert=dict(source="HKUST Zenodo 10909062",source_SHA256=SOURCE_SHA,
          comparison="fixed per-inverter monthly multiplicative theta_j in [0.95,1.05], common across reference and every deleted-day variant",
          tolerance="analytical bounded stress, not confidence, calibrated uncertainty or physical outage probability",
          source_derived_accuracy="Author reports ±5% accuracy for derived PV generation power/energy",
          q=Q,L_support=[1,3,7],original_R22_R25_locked_unchanged=True,
          independent_source_months=12,source_group_surfaces=group_totals,
          lp_existence_witnesses=len(witnesses),
          month_screens=len(member_rows),
          decision_grid_crosscheck="ALL R26I q5 L1-7 source-month point flags verified against R26I",
          role="DEVELOPMENT_ONLY not manuscript release",
          no_qatar_data=True)
(OUT/"R26J_CALIBRATION_GAP_CERTIFICATE.json").write_text(json.dumps(cert,indent=2))
(OUT/"SHA256SUMS.txt").write_text("".join(
    f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
    for p in sorted(OUT.iterdir()) if p.is_file() and p.name!="SHA256SUMS.txt"))
print("R26J_CALIBRATION_AUDIT_PASS",json.dumps(cert),flush=True)
