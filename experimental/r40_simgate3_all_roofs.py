#!/usr/bin/env python3
"""R40 SIM-GATE3B: all-five-roof HKUST time-support and lineage falsification.

Use *the exact original 2024-vintage source ZIP* and *the pre-frozen R26I
admission register*; no new months, weather extrapolation, data imputation,
or physical calibration. The old figures compare 24h site versus 12h inverter
energy; this independently repeats and corrects that comparison across ALL
five roof cohorts, rather than only the Library extension.
This script outputs only tiny derived summaries; no raw/source records.
"""
from __future__ import annotations
import calendar, csv, datetime as dt, hashlib, io, json, math, statistics, zipfile
from collections import defaultdict
from pathlib import Path

SRC=Path("source/dataset_original_Zenodo10909062.zip")
COHORT=Path("r26i/CONDITIONAL_GROUP_COHORTS.csv")
OUT=Path("R40_SIM_GATE3B_AllRoofs");OUT.mkdir(exist_ok=True)
SHA="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
BASE="Dataset/Time series dataset/PV generation dataset/PV stations with panel level optimizer/"
MONTH_COUNTS={"Library":93,"S H Ho Sports Hall":93,"Wong Check She Research Centre":93,"Zone A2":31,"Zone D":62}
OLD_TABLE={"Library":(0.428,0.994),"S H Ho Sports Hall":(0.358,0.828),
 "Wong Check She Research Centre":(0.311,0.785),"Zone A2":(0.753,1.147),"Zone D":(0.348,0.905)}
W5={f"{h:02d}:{m:02d}:00" for h in range(6,18) for m in range(0,60,5)}
W15={f"{h:02d}:{m:02d}:00" for h in range(6,18) for m in (0,15,30,45)}
ALL15={f"{h:02d}:{m:02d}:00" for h in range(24) for m in (0,15,30,45)}
assert len(W5)==144 and len(W15)==48 and len(ALL15)==96
with SRC.open("rb") as f:
 h=hashlib.sha256()
 for chunk in iter(lambda:f.read(8<<20),b""):h.update(chunk)
assert h.hexdigest()==SHA
with COHORT.open(newline="",encoding="utf8") as f: cohorts=list(csv.DictReader(f))
assert len(cohorts)==5 and {r["group"] for r in cohorts}==set(MONTH_COUNTS)

def quantile(a,p):
 s=sorted(a)
 assert s
 t=(len(s)-1)*p;i=int(t)
 return s[i]+(t-i)*(s[min(i+1,len(s)-1)]-s[i])

def load(z,path,field,admitted):
 out=defaultdict(dict)
 with z.open(path) as f:
  reader=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
  assert "Time" in reader.fieldnames and field in reader.fieldnames,(path,reader.fieldnames)
  for rec in reader:
   day,time=rec["Time"][:10],rec["Time"][11:]
   if day not in admitted:continue
   assert time not in out[day],("duplicate",path,day,time)
   v=float(rec[field])
   assert math.isfinite(v),("nonfinite",path,day,time)
   out[day][time]=v
 return out

summaries=[]
with zipfile.ZipFile(SRC) as z:
 assert z.testzip() is None
 for c in cohorts:
  g=c["group"]
  months=c["month_list"].split(";")
  assert len(months)==int(c["months"])
  days=set()
  for m in months:
   y,mo=map(int,m.split("-"))
   days.update(f"{m}-{i:02d}" for i in range(1,calendar.monthrange(y,mo)[1]+1))
  assert len(days)==MONTH_COUNTS[g],(g,len(days))
  sitepath=BASE+f"Site level dataset/{g}.csv"
  invpaths=[BASE+f"Inverter level dataset/{g}_Inverter_{j}.csv" for j in range(1,int(c["inverters"])+1)]
  assert sitepath in z.namelist() and all(f in z.namelist() for f in invpaths),(g,sitepath,invpaths)
  site=load(z,sitepath,"power(W)",days)
  streams=[load(z,p,"totalActivePower(W)",days) for p in invpaths]
  diffs_old=[];diffs_new=[];sidekwh=[];residuals=[];waveform_errors=[];day_support=[]
  for day in sorted(days):
   sr=site[day]
   assert set(sr)==ALL15,("site_incomplete",g,day,len(sr))
   iv=[d[day] for d in streams]
   assert all(W5.issubset(d) for d in iv),("inverter_incomplete",g,day)
   E_full=sum(sr.values())/4000.
   E_day=sum(sr[t] for t in W15)/4000.
   E_inv=sum(sum(d[t] for t in W5) for d in iv)/12000.
   assert min(E_full,E_day,E_inv)>0,("nonpositive_energy",g,day)
   diffs_old.append(100*abs(E_full-E_inv)/min(E_full,E_inv))
   diffs_new.append(100*abs(E_day-E_inv)/min(E_day,E_inv))
   sidekwh.append(E_full-E_day)
   residuals.append((E_full-E_inv)-(E_full-E_day))
   for t in W15:
    hh,mm,ss=map(int,t.split(":"))
    stamps=[f"{hh:02d}:{mm+shift:02d}:{ss:02d}" for shift in (0,5,10)]
    reconstructed=sum(sum(d[s] for d in iv) for s in stamps)/3.
    waveform_errors.append(sr[t]-reconstructed)
  exp_old=OLD_TABLE[g]
  actual_old=(statistics.median(diffs_old),quantile(diffs_old,.95))
  assert all(abs(v-e)<.001 for v,e in zip(actual_old,exp_old)),("old_table_not_reproduced",g,actual_old,exp_old)
  result={
    "group":g,"original_cohort_months":months,"n_days":len(days),"n_inverters":len(streams),
    "n_15min_daylight_values":len(waveform_errors),
    "old_24h_site_vs_12h_inverter_median_pct":actual_old[0],
    "old_24h_site_vs_12h_inverter_p95_pct":actual_old[1],
    "matched_12h_site_vs_12h_inverter_median_pct":statistics.median(diffs_new),
    "matched_12h_site_vs_12h_inverter_p95_pct":quantile(diffs_new,.95),
    "matched_12h_site_vs_12h_inverter_max_pct":max(diffs_new),
    "max_abs_matched_energy_difference_kwh":max(abs(x) for x in residuals),
    "total_site_energy_outside_06_to_18_kwh":sum(sidekwh),
    "site_minus_forward_mean_inverter_MAE_W":statistics.mean(abs(x) for x in waveform_errors),
    "site_minus_forward_mean_inverter_maxabs_W":max(abs(x) for x in waveform_errors),
    "n_forward_match_abs_at_most_0p01_W":sum(abs(x)<=.01000001 for x in waveform_errors),
    "n_forward_match_abs_at_most_0p1_W":sum(abs(x)<=.10000001 for x in waveform_errors),
    "claim":"source-channel time-support and deterministic dependence diagnostics only; not independent calibration",
  }
  summaries.append(result)
  print("SIM_GATE3B_ROOF",json.dumps(result,sort_keys=True),flush=True)
summary={"gate":"R40_SIM_GATE3B_ALL_ROOFS","R40_science_baseline":"UNCHANGED",
  "R41_status":"HOLD","source_sha256":SHA,"source_admission":"frozen R26I register",
  "n_roofs":len(summaries),"total_source_days":sum(x["n_days"] for x in summaries),
  "total_native_daylight_site_records":sum(x["n_15min_daylight_values"] for x in summaries),
  "all_original_table_S5_values_reproduced":True,
  "no_raw_source_redistributed":True,
  "independent_sensor_evidence":"NOT ESTABLISHED",
  "groups":summaries}
(OUT/"R40_SIM_GATE3B_ALL_ROOFS_RESULTS.json").write_text(json.dumps(summary,sort_keys=True,indent=2),encoding="utf8")
with (OUT/"R40_SIM_GATE3B_ROOF_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
 d=csv.DictWriter(f,fieldnames=[k for k in summaries[0] if k not in ("original_cohort_months","claim")])
 d.writeheader()
 for v in summaries:d.writerow({k:v[k] for k in d.fieldnames})
print("R40_SIM_GATE3B_DONE",json.dumps({k:v for k,v in summary.items() if k!="groups"},sort_keys=True),flush=True)
