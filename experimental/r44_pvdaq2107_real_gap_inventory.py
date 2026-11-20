#!/usr/bin/env python3
"""R44 PVDAQ 2107 real-missingness inventory and meter-side plausibility gate.

Descriptive source QA only; never treat missing original inverter readings as
known-zero energy or invent a full-month reference. No raw data redistributed.
"""
from collections import Counter, defaultdict
import csv, hashlib, io, json, math, re, urllib.request
from datetime import datetime,date,timedelta
from pathlib import Path
ROOT="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/2107_OEDI"
FILES={
 "electrical":("data/2107_electrical_data_2025.csv","f1c93d2124b6d7e20a3b77206cb104b99586a8a3d1c70615cc0737e7f6100d1d"),
 "meter":("data/2107_meter_15m_data_2025.csv",None)}
OUT=Path("R44_REAL_GAP_DERIVED_ONLY");OUT.mkdir(exist_ok=True)
C=Path("R44_REAL_GAP_PRIVATE_SOURCE");C.mkdir(exist_ok=True)
def get(name):
 f,expected=FILES[name];target=C/Path(f).name
 if not target.exists():
  with urllib.request.urlopen(ROOT+"/"+f,timeout=120) as r,target.open("wb") as o:
   for chunk in iter(lambda:r.read(2<<20),b""):o.write(chunk)
 sha=hashlib.sha256(target.read_bytes()).hexdigest()
 if expected:assert sha==expected,(name,sha)
 return target,{"url":ROOT+"/"+f,"sha256":sha,"bytes":target.stat().st_size}
def intervals():
 return [f"{hh:02d}:{mm:02d}" for hh in range(10,14) for mm in range(0,60,5)]
def main():
 e,eid=get("electrical")
 matrix=defaultdict(dict);n=0
 with e.open(newline="",encoding="utf-8-sig") as f:
  reader=csv.DictReader(f)
  cols=sorted((c for c in reader.fieldnames if re.fullmatch(r"inv_\d{2}_ac_power_inv_\d+",c)),
              key=lambda t:int(t.split("_")[1]))
  assert len(cols)==24
  for row in reader:
   t=datetime.fromisoformat(row["measured_on"])
   if t.year!=2025 or not 10<=t.hour<14:continue
   month=t.date().isoformat();time=t.strftime("%H:%M")
   vals=[]
   for c in cols:
    try:
     raw=row[c].strip();v=float(raw) if raw else float("nan")
     vals.append(math.isfinite(v) and v>=0)
    except ValueError: vals.append(False)
   assert time not in matrix[month]
   matrix[month][time]=vals;n+=1
 all_dates=[date(2025,1,1)+timedelta(days=i) for i in range(365)]
 window=intervals()
 perdev=[]
 for j,col in enumerate(cols):
  bad_days=[]; missing=0;total=0;entire_days=0;dates=[]
  for d in all_dates:
   day=str(d);rows=matrix.get(day,{})
   avail=sum(t in rows and rows[t][j] for t in window)
   missing+=48-avail;total+=48
   if avail<48:bad_days.append(day)
   if avail==0:entire_days+=1;dates.append(day)
  runs=[];start=prev=None
  for dtxt in dates:
   curr=date.fromisoformat(dtxt)
   if start is None:start=curr;prev=curr
   elif curr==prev+timedelta(days=1):prev=curr
   else:runs.append((str(start),str(prev),(prev-start).days+1));start=prev=curr
  if start is not None:runs.append((str(start),str(prev),(prev-start).days+1))
  runs.sort(key=lambda x:(-x[2],x[0]))
  perdev.append({"device_index":j+1,"channel":col,"midday_missing_slots":missing,
   "midday_slot_count":total,"days_with_any_midday_missing":len(bad_days),
   "days_without_any_midday_record":entire_days,
   "longest_missing_whole_day_runs":runs[:4]})
 m,mref=get("meter")
 with m.open(newline="",encoding="utf-8-sig") as f:
  reader=csv.DictReader(f);cols_m=reader.fieldnames
  sample=[];rows=0;month_counts=Counter();date_counts=Counter();missing=Counter()
  timecol=next((c for c in cols_m if "measured_on" in c or "time" in c.lower()),cols_m[0])
  for row in reader:
   rows+=1
   if len(sample)<3:sample.append(str(row[timecol])[:35])
   try:t=datetime.fromisoformat(row[timecol])
   except:continue
   if t.year!=2025:continue
   month_counts[t.strftime("%Y-%m")]+=1
   date_counts[t.date().isoformat()]+=1
   for col in cols_m:
    if col==timecol:continue
    if row[col].strip()=="":missing[col]+=1
 meter_summary={"file_ref":mref,"total_rows_including_other_years":rows,
  "columns":cols_m,"timestamp_column":timecol,"time_examples":sample,
  "2025_rows_per_month":dict(sorted(month_counts.items())),
  "2025_nonempty_day_count":len(date_counts),
  "missing_per_channel_2025":dict(missing)}
 n_missing_days=[sum(d["days_with_any_midday_missing"] for d in perdev)]
 res={"gate":"REAL_GAP_SOURCE_INVENTORY_NO_INDEPENDENT_TARGET_TRUTH","source":eid,
  "n_midday_electrical_rows_2025":n,"midday_slots_per_day":48,"date_range":"2025-01-01..2025-12-31",
  "per_inverter":perdev,"meter":meter_summary,
  "claim_limit":"Missing power field is a telemetry absence, not established zero generation or device failure; site meter independence and survival under outage not established.",
  "no_raw_source_data_redistributed":True}
 (OUT/"R44_2025_ACTUAL_MISSINGNESS_AND_METER_INVENTORY.json").write_text(json.dumps(res,indent=2))
 print("R44_MISSINGNESS_SUMMARY",json.dumps({"n_devices":len(perdev),"total_missing_10_to_14_slots":sum(d["midday_missing_slots"] for d in perdev),
  "device_full_midday_day_gaps":sum(d["days_without_any_midday_record"] for d in perdev),
  "top_missing_devices":sorted(perdev,key=lambda z:-z["midday_missing_slots"])[:5]},sort_keys=True),flush=True)
 print("R44_METER_INVENTORY",json.dumps(meter_summary,sort_keys=True)[:14000],flush=True)
if __name__=="__main__":main()
