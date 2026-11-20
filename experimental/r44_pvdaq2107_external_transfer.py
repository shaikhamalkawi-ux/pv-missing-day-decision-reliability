#!/usr/bin/env python3
"""R44 PVDAQ 2107 exact out-of-plant replication of frozen R43 margin triage.

Frozen R43: q=0.05; exactly 3 common calendar days; score=negative minimum
distance of retained normalized yields from the 0.95 shortlist boundary;
review flag when score >= -0.001077879123675074.
No training/tuning or outcome-dependent inclusion on PVDAQ.
Source 2024 is assessed only on all-hours complete months; source 2025
only on a predeclared local 10:00-14:00 common-sample window, never pooled
with 2024. No original electrical source data are redistributed.

This is a retrospective counterfactual stress test, not observed fault detection.
"""
import calendar, csv, datetime as dt, hashlib, json, math, re, urllib.request
from collections import defaultdict, Counter
from pathlib import Path
from bisect import bisect_left, bisect_right

ROOT="https://oedi-data-lake.s3.amazonaws.com/pvdaq/2023-solar-data-prize/2107_OEDI"
FILES={"metadata":("metadata/2107_system_metadata.json","17e4f7f448fcb2bec43f7610b40c1f7f4fc794ccc185e41dcde0514afba73ae5"),
 "2024":("data/2107_electrical_data_2024.csv","bb2e9f7495e471503daa2c4b4ae9aa053ca4c779d63665afb1c2270daaa243a5"),
 "2025":("data/2107_electrical_data_2025.csv","f1c93d2124b6d7e20a3b77206cb104b99586a8a3d1c70615cc0737e7f6100d1d")}
OUT=Path("R44_EXTERNAL_DERIVED_ONLY");OUT.mkdir(exist_ok=True)
CACHE=Path("source_cache");CACHE.mkdir(exist_ok=True)
Q=.05;GAP=3;R43_THRESHOLD=-0.001077879123675074
TIME_WINDOWS={"2024":"FULL_24H_288_NATIVE_CLOCK_SAMPLES",
              "2025":"FIXED_10_TO_14_LOCAL_48_SOURCE_SAMPLES"}
PRIMARY_CANDIDATES=tuple(range(24))
SENSITIVITY_CANDIDATES=tuple(range(14))  # predeclared first 14 channels, not selected based on performance
def download(key):
 path,refsha=FILES[key]
 target=CACHE/Path(path).name
 if not target.exists():
  u=ROOT+"/"+path
  with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"106Amen-source-replay"}),timeout=120) as r, target.open('wb') as f:
   for b in iter(lambda:r.read(2<<20),b""):f.write(b)
 h=hashlib.sha256()
 with target.open("rb") as f:
  for chunk in iter(lambda:f.read(4<<20),b""):h.update(chunk)
 assert h.hexdigest()==refsha,("source mutated",key,h.hexdigest())
 return target
def check_equipment(m):
 iv=list(m["Inverters"].values());modules=list(m["Modules"].values())
 assert len(iv)==len(modules)==24
 models={(z.get("manufacturer"),z.get("model"),str(z.get("quantity"))) for z in iv}
 panels={(z.get("manufacturer"),z.get("model"),str(z.get("quantity"))) for z in modules}
 names=[z.get("name") for z in iv];pnames=[z.get("name") for z in modules]
 assert names==[f"inv_fss_{i}" for i in range(1,25)]
 assert pnames==[f"mod_fss_{i}" for i in range(1,25)]
 print("R44_EQUIPMENT",json.dumps({"inverters":len(iv),"inverter_models":list(map(list,models)),
         "module_groups":len(modules),"panel_models_and_counts":list(map(list,panels)),
         "module_inverter_id_states":sorted({str(z.get("inverter_id")) for z in modules})},
         sort_keys=True),flush=True)
 assert len(models)==1, "Different inverter models; AC normalizer not comparable"
 assert len({(z.get("manufacturer"),z.get("model")) for z in modules})==1, "Different PV module types"
 counts=[int(z["quantity"]) for z in modules]
 assert len(counts)==24 and min(counts)>0
 # The metadata uses matching name suffixes, but "inverter_id" is string None.
 # This is a conditional nominal-module allocation, NOT verified wiring.
 site_kw=float(m["System"]["power(kW DC)"])
 derived_kw=sum(counts)*.310 # manufacturer's 310W module label; rounded site rating
 assert abs(derived_kw-site_kw)<2.0, ("STC count does not close to site nameplate",derived_kw,site_kw)
 return {"n_inverters":24,"inverter_model_and_count":list(map(list,models)),
 "n_module_groups":24,"module_model_and_count":list(map(list,panels)),
 "module_inverter_id_states":sorted({str(z.get("inverter_id")) for z in modules}),
 "module_counts_by_name_suffix":counts,
 "module_count_total":sum(counts), "nominal_site_DC_kW_from_310W_label":derived_kw,
 "metadata_site_power_DC_kW":site_kw,
 "equal_dc_normalizer_supported":False,
 "nominal_DC_normalizer_is_CONDITIONAL":True,
 "source_explicit_inverter_to_module_edge":"NOT_PROVIDED; labels mod_fss_i/inv_fss_i matched by suffix as assumption",
 "source_module_semantic_conflict":"PVDAQ meta labels mono-Si; manufacturer/CEC model HiS-M310TI lists polycrystalline; do not infer tech ranking",
 "justification":"Hypothesized one-to-one name-suffix matching plus 310W/model; analysis is conditional on actual wiring."}
def read_year(key):
 source=download(key)
 byday=defaultdict(dict); seen=set();n=0
 with source.open(newline="",encoding="utf-8-sig") as f:
  dr=csv.DictReader(f);fields=dr.fieldnames
  times="measured_on";assert times in fields
  cols=[z for z in fields if re.fullmatch(r"inv_(\d\d)_ac_power_inv_\d+",z)]
  cols=sorted(cols,key=lambda z:int(re.search(r"inv_(\d\d)",z).group(1)))
  assert len(cols)==24 and [int(re.search(r"inv_(\d\d)",z).group(1)) for z in cols]==list(range(1,25))
  for rec in dr:
   n+=1
   clock=dt.datetime.fromisoformat(rec[times])
   if clock.year!=int(key):continue # don't combine overlapping 2024-02 onward copies from 2025 file
   stamp=clock.isoformat();assert stamp not in seen,("duplicate time",stamp,key)
   seen.add(stamp)
   vals=[]
   for c in cols:
    x=rec[c].strip()
    try:v=float(x) if x else float('nan')
    except ValueError:v=float('nan')
    vals.append(v)
   byday[clock.date().isoformat()][clock.strftime("%H:%M")]=tuple(vals)
 print("R44_YEAR",json.dumps({"year":key,"original_rows_including_other_year":n,
  "year_filtered_records":len(seen),"n_days":len(byday),
  "first_day":min(byday) if byday else None,"last_day":max(byday) if byday else None}),flush=True)
 return byday,cols
def qualified_months(year,byday,normalizers,allow_zero_device=False):
 valid={};reasons=Counter();qa=defaultdict(dict)
 for ym in sorted({day[:7] for day in byday}):
  y,m=map(int,ym.split('-'))
  months_days=[f"{ym}-{i:02d}" for i in range(1,calendar.monthrange(y,m)[1]+1)]
  daily=[];reason=None
  for day in months_days:
   rows=byday.get(day)
   if not rows:reason="MISSING_WHOLE_DAY";break
   if year=="2024":
    window=[f"{h:02d}:{mi:02d}" for h in range(24) for mi in range(0,60,5)]
    # source assumed minute aligned; no adding an absent midnight observation.
   else:
    window=[f"{h:02d}:{mi:02d}" for h in range(10,14) for mi in range(0,60,5)]
   if any(t not in rows for t in window):reason="MISSING_REQUIRED_CLOCK_SLOT";break
   values=[rows[t] for t in window]
   if not all(math.isfinite(v) and v>=0 for item in values for v in item):
    reason="MISSING_NONFINITE_OR_NEGATIVE_CHANNEL";break
   sums=tuple(sum(item[j] for item in values)/(12*normalizers[j]) for j in range(24)) # common daylight integration, conditional name-matched module count
   daily.append(sums)
  if reason is None:
   total=[sum(day[j] for day in daily) for j in range(24)]
   if max(total)<=0:reason="NONPOSITIVE_WHOLE_PLANT_ENERGY"
   elif not allow_zero_device and min(total)<=0:reason="NONPOSITIVE_DEVICE_MONTH_ENERGY"
  if reason is None:
   valid[ym]=daily;qa[ym]={"state":"ADMITTED","calendar_days":len(daily),"source_window":TIME_WINDOWS[year]}
  else:
   reasons[reason]+=1;qa[ym]={"state":"REJECTED","reason":reason}
 print("R44_MONTH_ADMISSION",json.dumps({"year":year,"admitted_months":list(valid),
       "total_candidate_months":len(qa),"rejected_summary":dict(reasons)},sort_keys=True),flush=True)
 return valid,qa
def sh(vals):
 best=max(vals)
 return tuple(i for i,v in enumerate(vals) if v>=(1-Q)*best-1e-10)
def auc_pairs(records):
 positive=[s for s,y in records if y];negative=sorted(s for s,y in records if not y)
 if not positive or not negative:return None
 n=sum(bisect_left(negative,x)+.5*(bisect_right(negative,x)-bisect_left(negative,x)) for x in positive)
 return n/(len(positive)*len(negative))
def evaluate(year,months,indices,claim):
 outputs=[];permonth=[]
 for month,daily in sorted(months.items()):
  days=len(daily)
  full=[sum(row[j] for row in daily) for j in indices]
  truth=sh(full)
  rr=[];change=0
  for start in range(days-GAP+1):
   # calculate retained sample directly, with none of the removed observations available
   retained=[sum(daily[d][j] for d in range(days) if not start<=d<start+GAP) for j in indices]
   if max(retained)<=0:raise RuntimeError("nonpositive retained max")
   ratio=[v/max(retained) for v in retained]
   score=-min(abs(x-(1-Q)) for x in ratio)
   flipped=sh(retained)!=truth
   flagged=score>=R43_THRESHOLD
   outputs.append((month,score,bool(flipped),bool(flagged)))
   rr.append((score,bool(flipped)))
   change+=bool(flipped)
  permonth.append({"month":month,"windows":len(rr),"n_shortlist_changes":change,
    "auc_in_month":auc_pairs(rr)})
 if not outputs:return {"scope":claim,"n_months":0,"status":"NO_ADMITTED_MONTHS","month_results":permonth}
 labels=[y for _,_,y,_ in outputs];flags=[f for *_,f in outputs]
 tp=sum(y and f for y,f in zip(labels,flags))
 fp=sum(not y and f for y,f in zip(labels,flags))
 fn=sum(y and not f for y,f in zip(labels,flags))
 tn=sum(not y and not f for y,f in zip(labels,flags))
 return {"scope":claim,"year":year,"n_candidate_devices":len(indices),
  "source_window":TIME_WINDOWS[year],
  "n_months":len(months),"n_windows":len(outputs),
  "n_changes":sum(labels),"n_flags":sum(flags),"TP":tp,"FP":fp,"FN":fn,"TN":tn,
  "auc":auc_pairs([(s,y) for _,s,y,_ in outputs]),
  "review_share":sum(flags)/len(flags),
  "recall":tp/(tp+fn) if tp+fn else None,
  "precision":tp/(tp+fp) if tp+fp else None,
  "n_mixed_months":sum(0<z["n_shortlist_changes"]<z["windows"] for z in permonth),
  "month_results":permonth,
  "evidence_limit":"Counterfactual full-record reference, overlapping windows, not real failures or cross-instrument independent validation"}
def main():
 md=json.loads(download("metadata").read_text())
 equipment=check_equipment(md)
 allres={}
 for year in ("2024","2025"):
  byday,columns=read_year(year)
  module_counts=equipment["module_counts_by_name_suffix"]
  months,qa=qualified_months(year,byday,module_counts)
  ac_months,acqa=qualified_months(year,byday,[1]*24)
  zero_months,zero_qa=qualified_months(year,byday,module_counts,allow_zero_device=True)
  assert list(months)==list(ac_months) and qa==acqa
  allres[year]={"clock_gate":qa,"zero_inclusive_clock_gate":zero_qa,
       "zero_inclusive_secondary":evaluate(year,zero_months,PRIMARY_CANDIDATES,f"{year}_ALL24_POST_SOURCE_AUDIT_ZERO_INCLUSIVE"),
       "primary":evaluate(year,months,PRIMARY_CANDIDATES,f"{year}_all24_CONDITIONAL_NAME_MATCHED_DC_R43"),
       "sensitivity":evaluate(year,months,SENSITIVITY_CANDIDATES,f"{year}_first14_PREDECLARED_CONDITIONAL_DC"),
       "ac_nameplate_negative_control":evaluate(year,ac_months,PRIMARY_CANDIDATES,f"{year}_all24_EQUAL_AC_INVERTER_RATING_DISTINCT_ESTIMAND")}
  for k in ("primary","sensitivity","ac_nameplate_negative_control","zero_inclusive_secondary"):
   r=allres[year][k]
   print("R44_EXTERNAL_RESULT",json.dumps({z:v for z,v in r.items() if z!="month_results"},sort_keys=True),flush=True)
 result={"gate":"R44_EXTERNAL_SITE_RETROSPECTIVE_QA","source":"NREL-OEDI PVDAQ 2107",
  "pinned_sha256":{k:z[1] for k,z in FILES.items()},
  "equipment":equipment,"q":Q,"missing_days_exact":GAP,
  "frozen_MOREEU_R43_threshold":R43_THRESHOLD,
  "zero_external_training":True,
  "no_source_rows_redistributed":True,
  "years":allres,
  "review_state":"SOURCE_LIMITED_RETROSPECTIVE; name-match conditional; zero-inclusive check explicitly post initial source gate; DO NOT CLAIM FIELD VALIDATION"}
 (OUT/"R44_PVDAQ2107_EXTERNAL_REPLICATION.json").write_text(json.dumps(result,indent=2,sort_keys=True))
 print("R44_EXTERNAL_GATE_COMPLETE",json.dumps({"years":{k:{s:z[s]["n_months"] for s in ("primary","sensitivity")} for k,z in allres.items()},"frozen_threshold":R43_THRESHOLD},sort_keys=True),flush=True)
if __name__=="__main__":main()
