#!/usr/bin/env python3
"""R44 anti-leak gate: 2025 revenue-meter vs inverter-output sources at aligned time.

All raw records remain in a GitHub Actions transient source cache, never archived.
This is numerical source-lineage and availability QA, not calibration or a proven
independent acquisition/failure-survival test.
"""
import csv,hashlib,json,math,statistics,urllib.request
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
ROOT="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/2107_OEDI"
E=("data/2107_electrical_data_2025.csv","f1c93d2124b6d7e20a3b77206cb104b99586a8a3d1c70615cc0737e7f6100d1d")
M=("data/2107_meter_15m_data_2025.csv","20fe6e7124bcd65715e69df0d8f5776019632c776cbe39fecb0d65908d9b14ff")
META=("metadata/2107_system_metadata.json","17e4f7f448fcb2bec43f7610b40c1f7f4fc794ccc185e41dcde0514afba73ae5")
RAW=Path("R44_TEMP_RAW_PRIVATE");RAW.mkdir(exist_ok=True)
OUT=Path("R44_METER_LINEAGE_DERIVED_ONLY");OUT.mkdir(exist_ok=True)
def get(key):
 path,sha=key
 f=RAW/Path(path).name
 if not f.exists():
  with urllib.request.urlopen(ROOT+"/"+path,timeout=120) as r,f.open("wb") as w:
   for b in iter(lambda:r.read(1<<20),b""):w.write(b)
 h=hashlib.sha256()
 with f.open("rb") as r:
  for b in iter(lambda:r.read(1<<20),b""):h.update(b)
 assert h.hexdigest()==sha,(path,h.hexdigest())
 return f
def pct(arr,p):
 a=sorted(arr)
 if not a:return None
 x=(len(a)-1)*p;i=int(x)
 return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def main():
 meta=json.loads(get(META).read_text())
 metric={k:v for k,v in meta["Metrics"].items() if "meter_revenue_grade_ac_output" in k}
 print("R44_REVENUE_METRIC",json.dumps(metric,default=str),flush=True)
 inv={}
 with get(E).open(newline="",encoding="utf-8-sig") as f:
  rr=csv.DictReader(f);cols=sorted([x for x in rr.fieldnames if "_ac_power_inv_" in x],
    key=lambda v:int(v.split("_")[1]))
  assert len(cols)==24
  for row in rr:
   d=datetime.fromisoformat(row["measured_on"])
   if d.year!=2025 or d.hour<9 or d.hour>=15:continue
   vals=[]
   for c in cols:
    try:
     v=float(row[c].strip()) if row[c].strip() else float('nan')
    except ValueError:v=float('nan')
    vals.append(v if math.isfinite(v) else None)
   inv[d]=vals
 meter=[]
 with get(M).open(newline="",encoding="utf-8-sig") as f:
  rr=csv.DictReader(f);ch=[x for x in rr.fieldnames if x!="measured_on"]
  assert ch==["meter_revenue_grade_ac_output_meter_149578"],ch
  for row in rr:
   d=datetime.fromisoformat(row["measured_on"])
   if d.year!=2025 or d.hour<10 or d.hour>=14:continue
   try:v=float(row[ch[0]])
   except (TypeError,ValueError):continue
   if math.isfinite(v):meter.append((d,v))
 assert len(meter)>=5000
 modes={"left":(0,5,10),"right":(-10,-5,0)}
 stats={}
 for mode,shifts in modes.items():
  matched=[];residuals=[];residpct=[];count=Counter();n1=0;n2=0;examples=[]
  for t,v in meter:
   timestamps=[t+timedelta(minutes=k) for k in shifts]
   rows=[inv.get(tt) for tt in timestamps]
   if any(row is None for row in rows):continue
   valid=[all(row[j] is not None and row[j]>=0 for row in rows) for j in range(24)]
   missing=24-sum(valid)
   count[missing]+=1
   if missing==0:
    p=sum(sum(row) for row in rows)/3
    matched.append((v,p));delta=v-p;residuals.append(delta)
    if min(v,p)>0:residpct.append(100*abs(delta)/min(v,p))
   elif missing==1:
    n1+=1
    if len(examples)<4:
     missingj=valid.index(False)+1
     others=sum(sum(row[j] for row in rows)/3 for j in range(24) if valid[j])
     examples.append({"date":str(t.date()),"device":missingj,
       "meter_positive":v>0,"peer_sum_positive":others>0,
       "residual_sign":"positive" if v>others else "nonpositive"})
   else:n2+=1
  stats[mode]={"meter_15min_points_examined":len(meter),
   "time_aligned_power_points_all24":len(matched),
   "points_exactly_one_inverter_missing":n1,
   "points_multiple_inverters_missing":n2,
   "missing_device_count_distribution":dict(sorted(count.items())),
   "signed_residual_median_kW":statistics.median(residuals) if residuals else None,
   "signed_residual_mean_kW":statistics.mean(residuals) if residuals else None,
   "signed_residual_min_kW":min(residuals) if residuals else None,
   "signed_residual_max_kW":max(residuals) if residuals else None,
   "median_abs_residual_kW":statistics.median(map(abs,residuals)) if residuals else None,
   "p95_abs_residual_kW":pct([abs(z) for z in residuals],.95) if residuals else None,
   "median_abs_pct":statistics.median(residpct) if residpct else None,
   "p95_abs_pct":pct(residpct,.95) if residpct else None,
   "within_0p001kW_fraction":(sum(abs(z)<=.001 for z in residuals)/len(residuals)) if residuals else None,
   "missing_single_device_examples_presence_only":examples}
  print("R44_METER_ALIGNMENT",mode,json.dumps({k:v for k,v in stats[mode].items() if k!="missing_device_count_distribution"},sort_keys=True),flush=True)
 res={"gate":"R44_METER_INVERTER_TIMEBASE_AND_SHARED_LINEAGE",
 "source_electrical_sha256":E[1],"source_meter_sha256":M[1],"metadata_sha256":META[1],
 "metadata_meter_metric":metric,"metric_unit":"read from metric fields, do not assume",
 "time_support":"2025 10:00-14:00 local, 15m meter vs 5m three-point inverter average",
 "declared_primary_mode":"left because both meter and inverter metadata say L; right is diagnostic only",
 "data":stats,
 "interpretation":"Residuals test numerical relationship, not physical independent-meter calibration, energy-balance validity, or future outage-survival.",
 "no_raw_redistributed":True}
 (OUT/"R44_PVDAQ2107_METER_INVERTER_ALIGNMENT.json").write_text(json.dumps(res,indent=2,default=str))
 print("R44_METER_LINEAGE_GATE_DONE",json.dumps({"modes":list(stats),"strict_no_operational_certificate":True}),flush=True)
if __name__=="__main__":main()
