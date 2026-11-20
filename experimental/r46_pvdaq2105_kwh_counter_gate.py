#!/usr/bin/env python3
"""PVDAQ 2105: are 'AC output (kWh)' channels cumulative device counters?

Preliminary 2-inverter channel test, source-only. Strictly distinguish
cumulative monotonically increasing energy, per-interval kWh, and daily-reset
energy. Do not call an observed gap recoverable without source semantics,
calibrated device persistence, and a fault-supported test. No raw rows shared.
"""
import csv,datetime as dt,hashlib,json,math,statistics,urllib.request,re
from collections import Counter,defaultdict
from pathlib import Path

ROOT="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/2105_OEDI/"
FILES={"inv01":"data/2105_inv01_data.csv","inv02":"data/2105_inv02_data.csv",
 "meter":"data/2105_meter_data.csv","meta":"metadata/2105_system_metadata.json"}
RAW=Path("R46_2105_PRIVATE_CACHE");RAW.mkdir(exist_ok=True)
OUT=Path("R46_2105_COUNTER_SEMANTICS");OUT.mkdir(exist_ok=True)
def get(name):
 url=ROOT+FILES[name];f=RAW/Path(FILES[name]).name
 with urllib.request.urlopen(url,timeout=100) as r,f.open("wb") as w:
  h=hashlib.sha256()
  for b in iter(lambda:r.read(2<<20),b""):w.write(b);h.update(b)
 return f,{"url":url,"sha256":h.hexdigest(),"bytes":f.stat().st_size}
def numer(s):
 try:
  val=float(s)
  return val if math.isfinite(val) else None
 except (ValueError,TypeError):return None
def percentile(a,p):
 if not a:return None
 a=sorted(a);t=(len(a)-1)*p;i=int(t)
 return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(t-i)
def counter(name):
 p,rec=get(name)
 readings=[];missing=0;cols=[]
 with p.open(newline="",encoding="utf-8-sig") as f:
  reader=csv.DictReader(f);cols=reader.fieldnames
  col=next(x for x in cols if "ac_output_(kwh)" in x.lower())
  for row in reader:
   t=dt.datetime.fromisoformat(row["measured_on"])
   v=numer(row[col])
   if v is None:missing+=1
   readings.append((t,v))
 positives=[];negatives=[];zero=0;transitions=0;gap_sums=[];day_drops=0
 prev_t=prev_v=None;max_gap_hours=0;gap_events=0;days_negative=defaultdict(int)
 for t,v in readings:
  if prev_t is not None and prev_v is not None and v is not None:
   delta=v-prev_v;elapsed=(t-prev_t).total_seconds()/60
   if 0<elapsed<=6:
    if delta>1e-7:positives.append(delta)
    elif delta< -1e-7:negatives.append(delta);days_negative[t.date().isoformat()]+=1
    else:zero+=1
    transitions+=1
    if delta<0 and t.date()!=prev_t.date():day_drops+=1
   elif elapsed>30 and elapsed<24*60:
    gap_events+=1;max_gap_hours=max(max_gap_hours,elapsed/60)
    if delta>=0:gap_sums.append((elapsed,delta))
  prev_t=t;prev_v=v
 value_valid=[v for t,v in readings if v is not None]
 out={"field":col,"columns":cols,"source":rec,"n_records":len(readings),
 "n_valid":len(value_valid),"n_missing":missing,
 "first_timestamp":str(readings[0][0]),"last_timestamp":str(readings[-1][0]),
 "value_range":[min(value_valid),max(value_valid)] if value_valid else None,
 "regular_5min_transitions":transitions,"positive_differences":len(positives),
 "negative_differences":len(negatives),"zero_differences":zero,
 "negative_difference_rate":len(negatives)/transitions if transitions else None,
 "negative_diff_months":len({d[:7] for d in days_negative}),
 "midnight_negative_differences":day_drops,"median_positive_delta_kwh":statistics.median(positives) if positives else None,
 "p95_positive_delta_kwh":percentile(positives,.95),
 "median_negative_delta_kwh":statistics.median(negatives) if negatives else None,
 "long_clock_gap_ge_30min":gap_events,"max_gap_hours_lt_24h":max_gap_hours,
 "nondecreasing_cross_gap_ge_30min":len(gap_sums),
 "nondecreasing_gap_energy_median":statistics.median(v for m,v in gap_sums) if gap_sums else None}
 print("R46_2105_COUNTER_TEST",name,json.dumps({k:v for k,v in out.items() if k not in ("columns","source")},sort_keys=True)[:5000],flush=True)
 return out
def main():
 data={}
 for k in ("inv01","inv02"):
  data[k]=counter(k)
 meta,stamp=get("meta")
 m=json.loads(meta.read_text())
 data["system_meta"]={
 "original_sha256":stamp["sha256"],
 "system_kwdc":m.get("System",{}).get("power(kW DC)"),
 "module_groups":m.get("Modules",{}),
 "inverter_fields_count":len(m.get("Inverters",{})),
 "meter_fields_count":len(m.get("Meters",{}))}
 if isinstance(data["system_meta"]["module_groups"],dict):
  data["system_meta"]["module_groups"]={
    k:{j:v.get(j) for j in ("name","model","quantity","manufacturer","type","inverter_id")} for k,v in m["Modules"].items()}
 print("R46_2105_SYSTEM_METADATA",json.dumps(data["system_meta"],default=str),flush=True)
 meter,mi=get("meter")
 with meter.open(newline="",encoding="utf-8-sig") as f:
  rr=csv.DictReader(f)
  cols=rr.fieldnames
  data["meter"]={"source_sha256":mi["sha256"],"rows":sum(1 for _ in rr),"columns":cols}
 print("R46_2105_METER",json.dumps(data["meter"]),flush=True)
 data["status"]="CUMULATIVE_SEMANTICS_ONLY_NOT_PERFORMANCE_VALIDATION"
 data["raw_data_redistributed"]=False
 (OUT/"R46_2105_COUNTER_SEMANTICS_TEST.json").write_text(json.dumps(data,indent=2,default=str))
if __name__=="__main__":main()
