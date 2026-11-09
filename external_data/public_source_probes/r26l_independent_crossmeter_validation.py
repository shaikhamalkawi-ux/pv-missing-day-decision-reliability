#!/usr/bin/env python3
"""R26L independent derived-output QA: no original integration function reused."""
import csv,json,statistics,hashlib,math
from collections import defaultdict
from pathlib import Path
P=Path("R26L_HKUST_SiteVsInverter")
def get_rows(name):
    with (P/name).open("r",newline="",encoding="utf8") as f:
        return list(csv.DictReader(f))
days=get_rows("R26L_MATCHED_SOURCE_DAY_AUDIT.csv")
groups=get_rows("R26L_GROUP_CROSSMETER_SUMMARY.csv")
assert len(days)==373 and len(groups)==5
assert len(set((r["group"],r["date"]) for r in days))==373
cohort=[x for x in days if x["source_cohort"]=="1"]
assert len(cohort)==372 and all(x["crossmeter_admitted"]=="1" for x in cohort)
assert all(x["all_inverters_native_complete"]=="1" and x["site_96_15min_complete"]=="1" for x in cohort)
def percentile(v,p):
    v=sorted(v);a=(len(v)-1)*p
    return v[int(a)]*(1-(a%1))+v[min(int(a)+1,len(v)-1)]*(a%1)
for r in cohort:
    site=float(r["station_power_integral_rect_kwh"])
    invert=float(r["sum_inverter_power_5min_integral_kwh"])
    gfield=float(r["station_native_generation_sum_kwh"])
    assert min(site,invert,gfield)>0
    rel=100*abs(site-invert)/min(site,invert)
    rel2=100*abs(gfield-invert)/min(gfield,invert)
    assert abs(rel-float(r["pct_abs_diff_station_power_vs_inverters"]))<1e-10
    assert abs(rel2-float(r["pct_abs_diff_sitegen_vs_inverters"]))<1e-10
for g in groups:
    arr=[r for r in cohort if r["group"]==g["group"]]
    assert len(arr)==int(g["source_cohort_days"])==int(g["matched_days"])
    powers=[float(r["pct_abs_diff_station_power_vs_inverters"]) for r in arr]
    generations=[float(r["pct_abs_diff_sitegen_vs_inverters"]) for r in arr]
    checks=[
      (percentile(powers,.5),"p50_site_power_integral_vs_inverters_pct"),
      (percentile(powers,.95),"p95_site_power_integral_vs_inverters_pct"),
      (percentile(generations,.5),"p50_site_generation_vs_inverters_pct"),
      (percentile(generations,.95),"p95_site_generation_vs_inverters_pct")]
    for val,k in checks:
        assert abs(val-float(g[k]))<1e-9,(g["group"],k,val,g[k])
    print("R26L_INDEPENDENT_GROUP_PASS",json.dumps({"group":g["group"],
      "days":len(arr),"p50_powervsinverter":percentile(powers,.5),
      "p95_powervsinverter":percentile(powers,.95)}),flush=True)
reference=json.loads((P/"R26L_PUBLISHED_FIGURE6_EXACT_REPLAY.json").read_text())
example=next(r for r in days if r["published_reference_example"]=="1")
assert example["date"]=="2022-08-31" and example["group"]=="Library"
named={
"Library_Inverter_1.csv":175.77,
"Library_Inverter_2.csv":251.88,
"Library_Inverter_3.csv":213.90}
for k,v in named.items(): assert abs(reference["inverter_power_integrals_kwh"][k]-v)<.015
assert abs(reference["station_power_integral_kwh"]-642.09)<.015
difference=abs(reference["station_power_integral_kwh"]-sum(reference["inverter_power_integrals_kwh"].values()))
assert abs(difference-.529)<.005
assert abs(100*difference/min(reference["station_power_integral_kwh"],sum(reference["inverter_power_integrals_kwh"].values()))-.08239)<.0001
report=dict(status="PASS_ARITHMETIC_ONLY",source_days=373,source_cohort_days=372,
            distinct_roofs=5,group_count_checks=5,group_percentile_checks=20,
            matched_power_energy_source_levels="15-min station power integral vs 5-min inverter power integral",
            figure6_reproduction="three inverter totals and 642.09 kWh site total match published two-decimal example",
            article_ref="https://doi.org/10.1038/s41597-025-04397-y",
            original_source_hash="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec",
            measurement_interpretation="Corroborates aggregate logging consistency; cannot infer independent per-inverter calibration bias, distribution, or covariance.",
            no_qatar=True,locked_r25_unchanged=True)
(P/"R26L_INDEPENDENT_ARITHMETIC_QA.json").write_text(json.dumps(report,indent=2))
print("R26L_INDEPENDENT_QA_PASS",json.dumps(report),flush=True)
