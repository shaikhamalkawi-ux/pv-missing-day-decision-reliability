#!/usr/bin/env python3
"""R26L HKUST cross-meter observation audit, source original + frozen R26I cohort.

This audit compares native site generation(kWh) interval records and integrated
native site power(W) 15-min samples with summed inverter power(W) 5-min samples
on source-admitted months, WITHOUT filling any values or assuming calibration
independence. It additionally checks the published example 2022-08-31 Library.

It is not a per-inverter calibration certificate or proof of independent meters.
"""
from pathlib import Path
from collections import defaultdict
import hashlib,zipfile,csv,io,math,calendar,statistics,json
SRC=Path("source/dataset_original_Zenodo10909062.zip")
R26I=Path("r26i")
OUT=Path("R26L_HKUST_SiteVsInverter")
OUT.mkdir(exist_ok=True)
EXPECTED_SHA="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
s=hashlib.sha256()
with SRC.open("rb") as f:
    for c in iter(lambda:f.read(1<<20),b""):s.update(c)
assert s.hexdigest()==EXPECTED_SHA

def csvrows(filepath):
    with filepath.open("r",encoding="utf8",newline="") as f:
        return list(csv.DictReader(f))
cohorts=csvrows(R26I/"CONDITIONAL_GROUP_COHORTS.csv")
old_daily=csvrows(R26I/"DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv")
assert len(cohorts)==5
original_values={(r["group"],r["date"],r["inverter"]):float(r["sum_measured_power_W"]) for r in old_daily}
selected_dates=defaultdict(set)
months_by_group={}
for r in cohorts:
    g=r["group"];ml=r["month_list"].split(";")
    assert ml and len(ml)==int(r["months"])
    months_by_group[g]=ml
    for m in ml:
        y,k=map(int,m.split("-"))
        for day in range(1,calendar.monthrange(y,k)[1]+1):
            selected_dates[g].add(f"{m}-{day:02d}")

# Include published explicit reference day for independent benchmark, not q-L cohort.
SELECTED_EXAMPLE="2022-08-31"
selected_dates["Library"].add(SELECTED_EXAMPLE)

EXPECTED_5={f"{h:02d}:{m:02d}:00" for h in range(6,18) for m in range(0,60,5)}
EXPECTED_15={f"{h:02d}:{m:02d}:00" for h in range(24) for m in (0,15,30,45)}
assert len(EXPECTED_5)==144 and len(EXPECTED_15)==96

with zipfile.ZipFile(SRC) as z:
    assert z.testzip() is None
    allnames=z.namelist()
    raw=defaultdict(lambda:defaultdict(lambda:defaultdict(dict)))
    site=defaultdict(lambda:defaultdict(dict))
    inventories=[]
    for c in cohorts:
        group=c["group"]
        sitefile=next(n for n in allnames if n.endswith(f"/Site level dataset/{group}.csv"))
        ivpaths=sorted(n for n in allnames if "/Inverter level dataset/" in n and n.endswith(".csv") and
                       n.split("/")[-1].startswith(group+"_Inverter"))
        assert len(ivpaths)==int(c["inverters"]),(group,len(ivpaths),c["inverters"])
        inventories.append(dict(group=group,site_file=sitefile,inverter_files=[x.split("/")[-1] for x in ivpaths],
                                source_calendar_months=months_by_group[group]))
        with z.open(sitefile) as f:
            rd=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace"))
            assert rd.fieldnames==["Time","generation(kWh)","power(W)"],rd.fieldnames
            for r in rd:
                date=r["Time"][:10]
                if date not in selected_dates[group]:continue
                time=r["Time"][11:]
                assert time not in site[group][date],(group,date,time,"duplicate site clock")
                vals={}
                for k in ("generation(kWh)","power(W)"):
                    try:x=float(r[k])
                    except:x=float("nan")
                    vals[k]=x
                site[group][date][time]=vals
        for x in ivpaths:
            device=x.split("/")[-1]
            with z.open(x) as f:
                rd=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace"))
                assert "Time" in rd.fieldnames and "totalActivePower(W)" in rd.fieldnames
                for r in rd:
                    date=r["Time"][:10]
                    if date not in selected_dates[group]:continue
                    time=r["Time"][11:]
                    assert time not in raw[group][date][device],(group,date,device,time)
                    try:power=float(r["totalActivePower(W)"])
                    except:power=float("nan")
                    raw[group][date][device][time]=power

rows=[]
for c in cohorts:
    group=c["group"]
    for date in sorted(selected_dates[group]):
        sampled_site=site[group].get(date,{})
        iv=raw[group].get(date,{})
        dev=sorted({j for k in iv for j in [k]})
        expected_n=int(c["inverters"])
        assert len(dev)==expected_n,(group,date,dev,expected_n)
        pv_good=all(set(v)==EXPECTED_5 and all(math.isfinite(p) for p in v.values()) for v in iv.values())
        site_good=set(sampled_site)==EXPECTED_15 and all(
            math.isfinite(v["generation(kWh)"]) and math.isfinite(v["power(W)"])
            for v in sampled_site.values())
        power_W=sum(sum(p for p in v.values()) for v in iv.values()) if pv_good else None
        sitegen=sum(v["generation(kWh)"] for v in sampled_site.values()) if site_good else None
        sitepower=sum(v["power(W)"] for v in sampled_site.values())*.25/1000 if site_good else None
        pv_kwh=power_W/12/1000 if pv_good else None
        if pv_good and date!=SELECTED_EXAMPLE:
            for device,observations in iv.items():
                key=(group,date,device)
                assert key in original_values,(group,date,device)
                delta=abs(original_values[key]-sum(observations.values()))
                assert delta<0.0001,(key,delta)
        match=pv_good and site_good and pv_kwh>0 and sitegen>0 and sitepower>0
        def rel(a,b):
            return 100*abs(a-b)/min(a,b) if min(a,b)>0 else None
        rows.append(dict(group=group,date=date,source_cohort=int(date!=SELECTED_EXAMPLE or group!="Library"),
            published_reference_example=int(group=="Library" and date==SELECTED_EXAMPLE),
            source_inverters=len(dev),source_site_15min_n=len(sampled_site),
            all_inverters_native_complete=int(pv_good),site_96_15min_complete=int(site_good),
            crossmeter_admitted=int(match),
            station_native_generation_sum_kwh=sitegen,
            station_power_integral_rect_kwh=sitepower,
            sum_inverter_power_5min_integral_kwh=pv_kwh,
            abs_diff_sitegen_vs_inverters_kwh=abs(sitegen-pv_kwh) if match else None,
            pct_abs_diff_sitegen_vs_inverters=rel(sitegen,pv_kwh) if match else None,
            pct_abs_diff_station_power_vs_inverters=rel(sitepower,pv_kwh) if match else None,
            pct_abs_diff_sitegen_vs_sitepower=rel(sitegen,sitepower) if match else None))
assert len(rows)==sum(len(x) for x in selected_dates.values())
with (OUT/"R26L_MATCHED_SOURCE_DAY_AUDIT.csv").open("w",encoding="utf8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
group_summary=[]
for c in cohorts:
    g=c["group"]
    rr=[r for r in rows if r["group"]==g and r["source_cohort"]==1]
    a=[r for r in rr if r["crossmeter_admitted"]==1]
    def quantile(vals,p):
        vals=sorted(vals)
        if not vals:return None
        x=(len(vals)-1)*p;lo=int(x);hi=min(lo+1,len(vals)-1)
        return vals[lo]+(x-lo)*(vals[hi]-vals[lo])
    errors=[r["pct_abs_diff_sitegen_vs_inverters"] for r in a]
    powerrs=[r["pct_abs_diff_station_power_vs_inverters"] for r in a]
    group_summary.append(dict(group=g,source_cohort_days=len(rr),matched_days=len(a),
        site_missing_or_nan_days=len(rr)-sum(r["site_96_15min_complete"] for r in rr),
        p50_site_generation_vs_inverters_pct=quantile(errors,.5),
        p95_site_generation_vs_inverters_pct=quantile(errors,.95),
        max_site_generation_vs_inverters_pct=max(errors) if errors else None,
        p50_site_power_integral_vs_inverters_pct=quantile(powerrs,.5),
        p95_site_power_integral_vs_inverters_pct=quantile(powerrs,.95),
        days_sitegen_mismatch_over_5pct=sum(x>5 for x in errors),
        days_sitegen_mismatch_over_10pct=sum(x>10 for x in errors)))
    print("GROUP_CROSSMETER",json.dumps(group_summary[-1]),flush=True)
with (OUT/"R26L_GROUP_CROSSMETER_SUMMARY.csv").open("w",encoding="utf8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(group_summary[0]));w.writeheader();w.writerows(group_summary)
example=next(r for r in rows if r["group"]=="Library" and r["date"]==SELECTED_EXAMPLE)
library_inverter_example={device:sum(ts.values())/12000 for device,ts in raw["Library"][SELECTED_EXAMPLE].items()}
assert len(library_inverter_example)==3
published_example={"Library_Inverter_1.csv":175.77,"Library_Inverter_2.csv":251.88,"Library_Inverter_3.csv":213.90}
for d,expected in published_example.items():
    assert abs(library_inverter_example[d]-expected)<0.015,(d,library_inverter_example[d],expected)
assert abs(example["station_power_integral_rect_kwh"]-642.09)<0.015
assert abs(example["sum_inverter_power_5min_integral_kwh"]-sum(published_example.values()))<0.02
(OUT/"R26L_PUBLISHED_FIGURE6_EXACT_REPLAY.json").write_text(json.dumps({
    "source_original":"Zenodo 10909062","date":SELECTED_EXAMPLE,
    "inverter_power_integrals_kwh":library_inverter_example,
    "published_inverter_energy_kwh":published_example,
    "station_power_integral_kwh":example["station_power_integral_rect_kwh"],
    "station_generation_field_sum_kwh":example["station_native_generation_sum_kwh"],
    "source_ratio_abs_pct":example["pct_abs_diff_station_power_vs_inverters"],
    "published_station_integral_kwh":642.09,
    "source_comparison":"15min station power(W) vs 5min inverter totalActivePower(W)",
    "result":"PASS within published two-decimal rounding",
    "metrology_boundary":"Cross-channel consistency, not independent sensor calibration"
},indent=2))
print("R26L_PUBLISHED_FIGURE6_REPLAY",json.dumps(library_inverter_example),flush=True)
(OUT/"R26L_PUBLISHED_DAY_REFERENCE.json").write_text(json.dumps({
 "date":"2022-08-31","paper":"Lin et al. 2025 Scientific Data, Fig. 6",
 "paper_site_reported_kwh":642.09,
 "paper_sum_of_three_inverters_reported_kwh":175.77+251.88+213.90,
 "paper_reported_difference_kwh":0.529,
 "our_source_mapped_2024_zenodo":example,
 "do_not_require_exact_parity_if_published_vintage_or_quadrature_unknown":True
},indent=2))
summary={"original_zenodo_record":"10909062","original_sha256":EXPECTED_SHA,
  "source_files_by_roof":inventories,"daily_rows_including_published_example":len(rows),
  "matched_cohort_days":sum(r["matched_days"] for r in group_summary),
  "source_site_channel":"generation(kWh) at 15-minute site telemetry. Field is summed as recorded; interval-energy interpretation provisional and must be checked against integrated site power(W).",
  "inverter_channel":"totalActivePower(W) at 5-minute inverter telemetry; rectangular integration",
  "source_cadence_gap":"Site 96 15-minute fields over full day vs inverter 144 five-minute daylight fields, timing quadrature/source-processing not independent metrology",
  "not_per_inverter_calibration":True,
  "not_independent_reference_meter_certified":True,
  "data_imputation":False,"q_L_original_unchanged":True,"no_qatar":True,
  "claim":"Cross-channel source-consistency audit, NOT a direct estimate of relative inverter gain errors."}
(OUT/"R26L_SOURCE_CROSSMETER_CERTIFICATE.json").write_text(json.dumps(summary,indent=2))
print("FIGURE_6_SOURCE_COMPARISON",json.dumps(example),flush=True)
print("R26L_SOURCE_CROSSMETER_GATE_COMPLETE",json.dumps({"matched_days":summary["matched_cohort_days"],
  "source_rows":len(rows),"groups":len(group_summary),"no_qatar":True}),flush=True)
