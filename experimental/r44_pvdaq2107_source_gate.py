#!/usr/bin/env python3
"""106Amen R44 source gate: inventory OEDI PVDAQ 2107 before outcome testing.
No raw electrical rows redistributed. No calibration, ranking, or scientific results.
Official source URL + SHA256 are recorded. Do not infer inverter DC-STC mappings.
"""
import csv, datetime, hashlib, json, math, re, statistics, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/2107_OEDI"
FILES={
 "metadata":ROOT+"/metadata/2107_system_metadata.json",
 "electrical_2024":ROOT+"/data/2107_electrical_data_2024.csv",
 "electrical_2025":ROOT+"/data/2107_electrical_data_2025.csv",
}
OUT=Path("R44_PVDAQ2107_SOURCE_GATE"); OUT.mkdir(exist_ok=True)
RAW=Path("source_cache"); RAW.mkdir(exist_ok=True)
def get(key,url):
 target=RAW/(key+(".json" if key=="metadata" else ".csv"))
 h=hashlib.sha256();size=0
 with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"106Amen-R44-science-audit/1.0"}),timeout=120) as response:
  with target.open("wb") as f:
   for buf in iter(lambda:response.read(2<<20),b""):
    f.write(buf); h.update(buf);size+=len(buf)
 return target,{"url":url,"sha256":h.hexdigest(),"bytes":size}
def sample_objects(obj,maxitems=5):
 if isinstance(obj,list):return [x for x in obj[:maxitems]]
 if isinstance(obj,dict):return [{"key":k,**(v if isinstance(v,dict) else {"value":v})} for k,v in list(obj.items())[:maxitems]]
 return [{"type":str(type(obj)),"value":str(obj)[:200]}]
def compact(obj):
 if isinstance(obj,dict):
  return {k:(v[:300] if isinstance(v,str) else v) for k,v in obj.items() if isinstance(v,(str,int,float,bool,type(None)))}
 return {"item":str(obj)[:400]}
def meta_probe(m):
 print("META_TOP_LEVEL_KEYS",list(m),flush=True)
 groups={}
 for k,v in m.items():
  low=k.lower()
  if any(z in low for z in ("system","site","inverter","module","metric","mount","sensor","meter")):
   smp=sample_objects(v,4)
   groups[k]={"container_type":type(v).__name__,
     "n_items":len(v) if hasattr(v,"__len__") else None,
     "examples":[compact(x) for x in smp]}
   print("META_GROUP",k,json.dumps(groups[k],default=str)[:8500],flush=True)
 return groups
def parse_time(t):
 t=str(t).strip()
 # provider timestamps may be ISO or plain local time
 v=t.replace("Z","+00:00")
 try:return datetime.datetime.fromisoformat(v)
 except ValueError:
  for fmt in ("%m/%d/%Y %H:%M:%S","%m/%d/%Y %H:%M","%Y/%m/%d %H:%M:%S"):
   try:return datetime.datetime.strptime(t,fmt)
   except ValueError:pass
 raise ValueError("timestamp parse unsuccessful: "+t[:80])
def csv_gate(path,rec):
 time_samples=[];mn=None;mx=None;month_rows=Counter();day_rows=Counter()
 deltas=Counter();prev=None;total=0;duplicate_times=0;observed_times=set()
 stats={}
 with path.open(newline="",encoding="utf-8-sig") as f:
  rr=csv.reader(f);headers=next(rr)
  ti=next((i for i,h in enumerate(headers) if re.search(r"(timestamp|date.?time|^time$)",h,re.I)),None)
  if ti is None:ti=0
  ac=[(i,h) for i,h in enumerate(headers) if re.search(r"ac.?power|active.?power",h,re.I) and not re.search(r"total|meter|plant",h,re.I)]
  for i,name in ac:stats[name]={"valid":0,"blank":0,"nonfinite":0,"negative":0,"zero":0,"min":None,"max":None,"sum":0.0}
  for row in rr:
   if not row:continue
   total+=1
   if len(row)!=len(headers):raise ValueError(f"row width mismatch at {total}: {len(row)} vs {len(headers)}")
   t=parse_time(row[ti]); key=str(t)
   if key in observed_times:duplicate_times+=1
   observed_times.add(key)
   mn=t if mn is None or t<mn else mn
   mx=t if mx is None or t>mx else mx
   if len(time_samples)<3:time_samples.append(key)
   month_rows[t.strftime("%Y-%m")]+=1;day_rows[t.strftime("%Y-%m-%d")]+=1
   if prev is not None:
    sec=(t-prev).total_seconds()
    if len(deltas)<30 or sec in deltas:deltas[sec]+=1
   prev=t
   for i,name in ac:
    v=row[i].strip();s=stats[name]
    if not v:s["blank"]+=1;continue
    try:num=float(v)
    except ValueError:s["nonfinite"]+=1;continue
    if not math.isfinite(num):s["nonfinite"]+=1;continue
    s["valid"]+=1;s["sum"]+=num;s["min"]=num if s["min"] is None else min(s["min"],num)
    s["max"]=num if s["max"] is None else max(s["max"],num)
    if num<0:s["negative"]+=1
    if num==0:s["zero"]+=1
  out={"original_file":rec,"n_rows":total,"n_columns":len(headers),"headers":headers,
   "clock_header":headers[ti],"time_examples":time_samples,"min_timestamp":str(mn),"max_timestamp":str(mx),
   "n_duplicate_times":duplicate_times,"month_rows":dict(sorted(month_rows.items())),
   "day_rows_96_count":sum(n==96 for n in day_rows.values()),
   "day_rows_288_count":sum(n==288 for n in day_rows.values()),
   "top_cadences_seconds":sorted([{"seconds":v,"count":n} for v,n in deltas.items()],key=lambda z:-z["count"])[:8],
   "inverter_ac_power_channels":len(ac),"ac_power_summary":stats}
  print("ELECTRICAL_GATE",json.dumps({k:out[k] for k in out if k not in ("headers","ac_power_summary","month_rows")},default=str)[:6000],flush=True)
  print("ELECTRICAL_COLUMNS",json.dumps(headers),flush=True)
  print("ELECTRICAL_AC_CHANNELS",json.dumps({"count":len(ac),"channels":list(stats)},default=str),flush=True)
  return out
def main():
 summaries={};paths={}
 for key,url in FILES.items():
  try:
   p,rec=get(key,url);paths[key]=p;summaries[key]={"status":"FETCH_PASS",**rec}
   print("SOURCE_FETCH",key,json.dumps(summaries[key]),flush=True)
  except Exception as e:
   summaries[key]={"status":"FETCH_FAIL","url":url,"error":type(e).__name__+": "+str(e)[:350]}
   print("SOURCE_FETCH_FAIL",key,repr(e),flush=True)
 if "metadata" not in paths or "electrical_2024" not in paths:
  raise RuntimeError("Mandatory original metadata or 2024 source absent")
 meta=json.loads(paths["metadata"].read_text())
 probe=meta_probe(meta)
 output={"stage":"R44_SOURCE_GATE_NOT_SCIENTIFIC_REPLICATION",
  "raw_bytes_redistributed":False,"source_inventory":summaries,
  "metadata_probe":probe,"electrical":{},"eligibility":"PENDING_INVERTER_DC_RATING_TRACE"}
 for y in (2024,2025):
  key="electrical_"+str(y)
  if key in paths:output["electrical"][key]=csv_gate(paths[key],summaries[key])
 (OUT/"R44_PVDAQ2107_SOURCE_INVENTORY.json").write_text(json.dumps(output,indent=2,default=str))
 print("R44_SOURCE_GATE_SUMMARY",json.dumps({"files":list(summaries),
  "source_statuses":{k:v["status"] for k,v in summaries.items()},
  "power_columns":{y:z["inverter_ac_power_channels"] for y,z in output["electrical"].items()},
  "source_months":{y:len(z["month_rows"]) for y,z in output["electrical"].items()},
  "no_scientific_conclusion":True},sort_keys=True),flush=True)
if __name__=="__main__":main()
