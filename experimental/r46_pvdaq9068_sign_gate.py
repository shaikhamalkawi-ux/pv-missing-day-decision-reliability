#!/usr/bin/env python3
"""R46 sign and system-boundary falsification for PVDAQ 9068.

Retain declared units, compare measured meter export/import against both sign
conventions at exact 5min timestamps. Diagnostic only: regression is never used
as a calibrator or to create ground-truth missing power. No raw rows redistributed.
"""
import csv,hashlib,math,re,json,statistics,urllib.request
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime

ROOT="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/9068_OEDI/data/"
SRC={
 "ac":("9068_ac_power_data_20240101_20250430.csv","16cac9d3ec61027e6f176eea276dafd1ad6d46461336edb29a3772ad34b5efc2"),
 "meter":("9068_meter_data_20240101_20250430.csv","be6662913e7ceb0888b24e6ad16c2b76eba264e2c7c0ba69d36d6e85772157b6")}
TEMP=Path("R46_PRIVATE_ORIGINAL_DATA");TEMP.mkdir(exist_ok=True)
OUT=Path("R46_PVDAQ9068_SIGN_GATE");OUT.mkdir(exist_ok=True)
def download(k):
 name,sha=SRC[k];dest=TEMP/name
 if not dest.exists():
  with urllib.request.urlopen(ROOT+name,timeout=100) as r,dest.open("wb") as f:
   for b in iter(lambda:r.read(2<<20),b""):f.write(b)
 h=hashlib.sha256()
 with dest.open("rb") as f:
  for b in iter(lambda:f.read(2<<20),b""):h.update(b)
 assert h.hexdigest()==sha,("original hash changed",k)
 return dest
def num(s):
 try:
  f=float(s)
  return f if math.isfinite(f) else None
 except (TypeError,ValueError):return None
def pct(vals,q):
 if not vals:return None
 v=sorted(vals);z=(len(v)-1)*q;lo=int(z)
 return v[lo]+(v[min(lo+1,len(v)-1)]-v[lo])*(z-lo)
def stats(vec):
 return {"n":len(vec),"p05":pct(vec,.05),"median":pct(vec,.5),"p95":pct(vec,.95),
         "mean":sum(vec)/len(vec) if vec else None}
def corr(vals):
 n=len(vals)
 if not n:return None
 sx=sum(x for x,y in vals); sy=sum(y for x,y in vals)
 mx=sx/n;my=sy/n
 sxx=sum((x-mx)**2 for x,y in vals);syy=sum((y-my)**2 for x,y in vals)
 return sum((x-mx)*(y-my) for x,y in vals)/((sxx*syy)**.5) if sxx>0 and syy>0 else None
def get_ac():
 result={}
 with download("ac").open(newline="",encoding="utf-8-sig") as f:
  rr=csv.DictReader(f);cols=rr.fieldnames
  p1=next(z for z in cols if re.search(r"^inverter_1_ac_power_",z))
  p2=next(z for z in cols if re.search(r"^inverter_2_ac_power_",z))
  mod1=sorted([z for z in cols if z.startswith("inverter_module_1.") and "_ac_power" in z])
  mod2=sorted([z for z in cols if z.startswith("inverter_module_2.") and "_ac_power" in z])
  assert len(mod1)==len(mod2)==4
  for row in rr:
   t=row["measured_on"]
   v=[num(row[x]) for x in [p1,p2]+mod1+mod2]
   result[t]=v
 return result
def get_meter():
 out={}
 with download("meter").open(newline="",encoding="utf-8-sig") as f:
  rr=csv.DictReader(f)
  col=next(z for z in rr.fieldnames if z.startswith("meter_ac_power_(kw)"))
  for row in rr:
   out[row["measured_on"]]=num(row[col])
 return out

def main():
 inv=get_ac();meter=get_meter()
 joined=sorted(set(inv)&set(meter))
 pts=[];mod1res=[];mod2res=[];filtered=Counter()
 months=defaultdict(list)
 single_missing=Counter()
 for t in joined:
  arr=inv[t];m=meter[t]
  if m is None:filtered["meter_missing"]+=1;continue
  if arr[0] is None or arr[1] is None:
   if (arr[0] is None)!=(arr[1] is None):
    single_missing[t[:7]]+=1
   filtered["inverter_total_missing"]+=1
   continue
  a,b=arr[:2];s=a+b
  if any(z is not None and z<0 for z in [a,b]):filtered["negative_inv"]+=1
  if all(x is not None for x in arr[2:6]):mod1res.append(abs(a-sum(arr[2:6])))
  if all(x is not None for x in arr[6:10]):mod2res.append(abs(b-sum(arr[6:10])))
  if s>100 and 10<=int(t[11:13])<14:
   pts.append((s,m))
   months[t[:7]].append((s,m))
 assert len(pts)>1000
 sum_m=[x for x,y in pts];meas_m=[y for x,y in pts]
 pos=[abs(y-x) for x,y in pts];neg=[abs(y+x) for x,y in pts]
 dat={
 "source_sha256":{key:sha for key,(name,sha) in SRC.items()},
 "n_aligned_all_hours":len(joined),
 "n_daytime_valid_generation_gt_100kw":len(pts),
 "meter_when_inverter_generation_positive":stats(meas_m),
 "sum_of_two_inverter_totals":stats(sum_m),
 "meter_negative_share_at_positive_generation":sum(y<0 for y in meas_m)/len(pts),
 "pair_correlation_meter_vs_sum":corr(pts),
 "absolute_meter_minus_sum":stats(pos),
 "absolute_meter_plus_sum":stats(neg),
 "share_abs_meter_plus_sum_below_1kw":sum(e<=1 for e in neg)/len(neg),
 "share_abs_meter_minus_sum_below_1kw":sum(e<=1 for e in pos)/len(pos),
 "inverter_1_vs_four_modules_residual_kw":stats(mod1res),
 "inverter_2_vs_four_modules_residual_kw":stats(mod2res),
 "times_one_inverter_total_missing_but_meter_recorded":sum(single_missing.values()),
 "single_inverter_missing_by_month":dict(sorted(single_missing.items())),
 "permonth":{}
 }
 for month,vals in sorted(months.items()):
  dat["permonth"][month]={"n":len(vals),"corr":corr(vals),
   "median_meter_kw":statistics.median(y for x,y in vals),
   "median_abs_forward":statistics.median(abs(y-x) for x,y in vals),
   "median_abs_negative_sign":statistics.median(abs(y+x) for x,y in vals)}
 print("R46_SIGN_GATE_SUMMARY",json.dumps({k:v for k,v in dat.items() if k!="permonth"},sort_keys=True),flush=True)
 (OUT/"R46_PVDAQ9068_SIGN_AND_MODULE_LINEAGE.json").write_text(json.dumps(dat,sort_keys=True,indent=2))
if __name__=="__main__":main()
