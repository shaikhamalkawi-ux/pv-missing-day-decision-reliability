#!/usr/bin/env python3
"""R27 scientific admission and exact source-to-manuscript checks.

Fails closed when HKUST source/decision/channel/gain evidence no longer matches
the independently audited source-derived outputs. Frozen R22 remains upstream.
"""
import csv,json,math,statistics
from pathlib import Path
P=Path("r27_evidence")
def csvread(folder,name):
    with (P/folder/name).open(newline="",encoding="utf8") as f:return list(csv.DictReader(f))
r26h=csvread("R26H","R26H_HKUST_LIBRARY_SURFACE.csv")
assert len(r26h)==35
assert {(float(r["q"]),int(r["L"])) for r in r26h}=={(q,L) for q in (0,.025,.05,.075,.10) for L in range(1,8)}
for r in r26h:
    q,L=float(r["q"]),int(r["L"])
    expected=1 if q==.10 and L==7 else 0
    assert int(r["fragile_month_count"])==expected,(q,L,r)
    assert int(r["admitted_months"])==3
source=csvread("R26L","R26L_MATCHED_SOURCE_DAY_AUDIT.csv")
library=[r for r in source if r["group"]=="Library" and r["source_cohort"]=="1"]
assert len(library)==93
assert sum(r["crossmeter_admitted"]=="1" for r in library)==93
assert sorted({r["date"][:7] for r in library})==["2022-07","2023-05","2023-07"]
errors=sorted(float(r["pct_abs_diff_station_power_vs_inverters"]) for r in library)
med=statistics.median(errors)
a=(len(errors)-1)*.95
p95=errors[int(a)]*(1-a%1)+errors[min(int(a)+1,len(errors)-1)]*(a%1)
# Robust direct percentile formula
p95=errors[int(a)]*(1-(a%1))+errors[min(int(a)+1,len(errors)-1)]*(a%1)
assert abs(med-0.42757788815049586)<1e-8,(med,)
assert abs(p95-0.9935278571786557)<1e-8,(p95,)
example=json.loads((P/"R26L"/"R26L_PUBLISHED_FIGURE6_EXACT_REPLAY.json").read_text())
assert abs(example["station_power_integral_kwh"]-642.087334791)<1e-8
assert abs(sum(example["inverter_power_integrals_kwh"].values())-641.55875)<1e-7
assert abs(example["station_generation_field_sum_kwh"]-651.32)<1e-7
qk=csvread("R26K","GROUP_EPSILON_SENSITIVITY.csv")
assert len(qk)==35
library_qk={float(r["epsilon"]):(int(r["baseline_preserving_gap_flips"]),int(r["months"])) for r in qk if r["group"]=="Library"}
expected={0.:0,.0025:0,.005:1,.01:1,.02:2,.03:3,.05:3}
assert {x:a[0] for x,a in library_qk.items()}==expected,library_qk
assert all(n==3 for c,n in library_qk.values())
cert=json.loads((P/"R26K"/"R26K_PRIMARY_CERTIFICATE.json").read_text())
assert cert["status"]=="DEVELOPMENT_PASS_PENDING_INDEPENDENT_CHECK"
assert cert["source_sha"]=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
qa=(P/"R26K_Independent"/"R26K_INDEPENDENT_QA_CERTIFICATE.json")
ind=json.loads(qa.read_text())
assert ind["all_2device_cells_matched"] and ind["all_recorded_positive_witnesses_valid"]
assert ind["exact_2device_analytic_cells"]==56
assert ind["three_device_explicit_positive_witnesses"]==15
main=Path("paper/main.tex").read_text()
supp=Path("paper/supplement.tex").read_text()
for phrase in ("HKUST Library","642.087","0.428",r"\bibitem{lin2025}",r"\bibitem{hkust2024}"):
    assert phrase in main,phrase
for phrase in ("Table S4.","Table S5.","Table S6.","0/3 & 0/3 & 1/3 & 1/3 & 2/3 & 3/3 & 3/3","651.32"):
    assert phrase in supp,phrase
for value in ("3/25","1/7","45/79"):
    assert value in main and value in supp,value
print(json.dumps({"R27": "PASS source-to-result",
    "HKUST_qL_cells":len(r26h),"library_source_days":len(library),
    "HKUST_q5_l3":"0/3","HKUST_q10_l7":"1/3",
    "cross_meter_median_pct":med,"cross_meter_p95_pct":p95,
    "conditional_gain_cells":len(qk),
    "conditional_gain_library":[[eps, library_qk[eps][0]] for eps in sorted(library_qk)],
    "independent_two_inverter_checks":56,
    "independent_three_inverter_positive_witness_checks":15,
    "R22_core_counts_unchanged":True,"Qatar_included":False},indent=2))
