#!/usr/bin/env python3
"""Independent R44 source audit: use cumulative-day subtraction, not retained direct sums.

Rebuild 2024 strict and zero-inclusive results from original NREL PVDAQ source,
without sharing original rows. Frozen q=.05, three common missing days,
unchanged MORE-EU R43 score threshold. Distinct calculation path from R44 primary.
"""
import csv, calendar, hashlib, math, json, urllib.request
from collections import defaultdict
from datetime import datetime
from bisect import bisect_left,bisect_right
from pathlib import Path
BASE="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/2107_OEDI"
SRC=BASE+"/data/2107_electrical_data_2024.csv"
MET=BASE+"/metadata/2107_system_metadata.json"
SHA_SRC="bb2e9f7495e471503daa2c4b4ae9aa053ca4c779d63665afb1c2270daaa243a5"
SHA_MET="17e4f7f448fcb2bec43f7610b40c1f7f4fc794ccc185e41dcde0514afba73ae5"
THRESH=-0.001077879123675074
OUT=Path("R44_INDEPENDENT_DERIVED_ONLY");OUT.mkdir(exist_ok=True)
SOURCE_CACHE=Path("R44_INDEPENDENT_SOURCE_CACHE");SOURCE_CACHE.mkdir(exist_ok=True)
def get(url,expected):
 target=SOURCE_CACHE/Path(url).name
 if not target.exists():
  with urllib.request.urlopen(url,timeout=120) as s,target.open("wb") as d:
   for b in iter(lambda:s.read(1<<20),b""):d.write(b)
 h=hashlib.sha256()
 with target.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 assert h.hexdigest()==expected
 return target
def arr_and_daily():
 m=json.loads(get(MET,SHA_MET).read_text())
 z=sorted(m["Modules"].values(),key=lambda o:int(o["name"].rsplit("_",1)[1]))
 assert len(z)==24 and [o["name"] for o in z]==[f"mod_fss_{i}" for i in range(1,25)]
 qty=[int(o["quantity"]) for o in z];assert min(qty)>0
 data=defaultdict(dict)
 with get(SRC,SHA_SRC).open(newline="",encoding="utf-8-sig") as f:
  d=csv.DictReader(f)
  chan=sorted([c for c in d.fieldnames if c.endswith(tuple(str(x) for x in range(10))) and "_ac_power_inv_" in c],
     key=lambda c:int(c.split("_")[1]))
  assert len(chan)==24
  for row in d:
   t=datetime.fromisoformat(row["measured_on"])
   key=t.date().isoformat();clock=t.strftime("%H:%M")
   assert clock not in data[key]
   data[key][clock]=[float(row[c]) if row[c].strip() else float('nan') for c in chan]
 months=defaultdict(list)
 for date,series in data.items():months[date[:7]].append((date,series))
 valid={}
 for month,days in sorted(months.items()):
  y,mo=map(int,month.split("-"))
  if len(days)!=calendar.monthrange(y,mo)[1]:continue
  days.sort();all_daily=[];ok=True
  for date,d in days:
   clocks=[f"{h:02d}:{mn:02d}" for h in range(24) for mn in range(0,60,5)]
   if set(d)!=set(clocks):ok=False;break
   if not all(math.isfinite(v) and v>=0 for cl in clocks for v in d[cl]):ok=False;break
   row=tuple(sum(d[c][j] for c in clocks)/(12*qty[j]) for j in range(24))
   all_daily.append(row)
  if ok and max(sum(r[j] for r in all_daily) for j in range(24))>0:
   valid[month]=all_daily
 return valid,qty
def auc_pairs(pos,neg):
 if not pos or not neg:return None
 ng=sorted(neg)
 return sum(bisect_left(ng,s)+.5*(bisect_right(ng,s)-bisect_left(ng,s)) for s in pos)/(len(pos)*len(neg))
def evaluate(valid,strict):
 count=[0,0,0,0]; scores_pos=[];scores_neg=[];per=[]
 for month,days in sorted(valid.items()):
  full=[sum(row[k] for row in days) for k in range(24)]
  if strict and min(full)<=0:continue
  fullbest=max(full)
  full_set=tuple(i for i,x in enumerate(full) if x>=.95*fullbest-1e-10)
  n=len(days);window_n=0;changed=0
  for st in range(n-2):
   remove=[sum(days[dd][k] for dd in range(st,st+3)) for k in range(24)]
   # Independent cumulative subtraction vs direct retained sum in R44 primary
   remain=[full[k]-remove[k] for k in range(24)]
   peak=max(remain)
   got=tuple(i for i,v in enumerate(remain) if v>=.95*peak-1e-10)
   flag=(-min(abs(v/peak-.95) for v in remain)>=THRESH)
   wrong=(got!=full_set)
   if wrong:scores_pos.append(-min(abs(v/peak-.95) for v in remain))
   else:scores_neg.append(-min(abs(v/peak-.95) for v in remain))
   if flag and wrong:count[0]+=1
   elif flag:count[1]+=1
   elif wrong:count[2]+=1
   else:count[3]+=1
   window_n+=1;changed+=wrong
  per.append({"month":month,"windows":window_n,"changed":changed})
 nsum=sum(count);res={"scope":"strict" if strict else "zero_inclusive","months":len(per),
  "windows":nsum,"TP":count[0],"FP":count[1],"FN":count[2],"TN":count[3],
  "auc":auc_pairs(scores_pos,scores_neg),"month_counts":per}
 return res
if __name__=="__main__":
 data,counts=arr_and_daily()
 results=[evaluate(data,True),evaluate(data,False)]
 a,b=results
 assert (a["months"],a["windows"],a["TP"],a["FP"],a["FN"],a["TN"])==(6,169,0,0,14,155),a
 assert (b["months"],b["windows"],b["TP"],b["FP"],b["FN"],b["TN"])==(8,227,0,0,14,213),b
 assert abs(a["auc"]-0.9976958525345622)<1e-9 and abs(b["auc"]-0.9983232729711603)<1e-9
 doc={"state":"INDEPENDENT_REPLAY_PASS_2024",
  "source_sha256":SHA_SRC,"meta_sha256":SHA_MET,
  "module_counts_by_matching_suffix":counts,
  "module_to_inverter_explicit_link":"ABSENT; inferred suffix relation conditional",
  "transfer_threshold":THRESH,
  "method":"distinct original CSV reader and direct month-minus-gap arithmetic",
  "original_records_redistributed":False,
  "results":results}
 (OUT/"R44_INDEPENDENT_REPLAY_REPORT.json").write_text(json.dumps(doc,indent=2))
 print("R44_INDEPENDENT_PASS",json.dumps({k:v for k,v in doc.items() if k not in ("results","module_counts_by_matching_suffix")},sort_keys=True),flush=True)
 for r in results:print("R44_REPLAY_SCOPE",json.dumps({k:v for k,v in r.items() if k!="month_counts"}),flush=True)
