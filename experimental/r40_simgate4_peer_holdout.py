#!/usr/bin/env python3
"""SIM-GATE4: prospective-time peer-telemetry bounds for PV shortlists.

Experiment is strictly RETROSPECTIVE and counterfactual: one inverter loses
a contiguous 1--7 day feed, two inverter feeds survive, and the reporting
time is AFTER the entire month (so the missing device's remaining dates are
known). No site aggregate: SIM-GATE3 proved that it contains upstream
inverter information. No weather/pvlib assumptions.

2022-07 = training; 2023-05 = validation only; 2023-07 = final untouched
test of envelopes frozen from prior months. Monthly out-of-gap reference
is calculated from nonmissing samples only, as a report available at end
of month. A learned envelope is NOT a deterministic future certificate.
Output is small aggregate evidence only: no source raw or day-level power.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, io, json, math, zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np

SRC=Path("source/dataset_original_Zenodo10909062.zip")
OUT=Path("R40_SIM_GATE4_PeerHoldout"); OUT.mkdir(parents=True,exist_ok=True)
SHA="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
P="Dataset/Time series dataset/PV generation dataset/PV stations with panel level optimizer/"
FILES=[P+f"Inverter level dataset/Library_Inverter_{i}.csv" for i in range(1,4)]
DC=np.array([57720.,56240.,56240.]); CAP=50000.
MONTHS=("2022-07","2023-05","2023-07")
QV=(.05,.10)
expected={"2022-07":[1163.758524,1590.833339,1534.450622],
          "2023-05":[1059.051906,1051.080868,937.457752],
          "2023-07":[1573.469577,1564.780903,1433.447635]}

def check_sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(8<<20),b""): h.update(c)
 assert h.hexdigest()==SHA, ("bad_original_SHA256",h.hexdigest())
 return h.hexdigest()
check_sha(SRC)

def load(z,path):
 out={}
 with z.open(path) as f:
  reader=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
  assert "Time" in reader.fieldnames and "totalActivePower(W)" in reader.fieldnames
  for r in reader:
   ts=r["Time"]
   if ts[:7] not in MONTHS: continue
   t=dt.datetime.strptime(ts,"%Y-%m-%d %H:%M:%S")
   if not(6<=t.hour<18 and t.minute%5==0): continue
   assert ts not in out,("duplicate",path,ts)
   v=float(r["totalActivePower(W)"])
   assert math.isfinite(v) and v>=0,("invalid",path,ts,v)
   out[ts]=v
 return out

with zipfile.ZipFile(SRC) as z:
 assert z.testzip() is None
 iv=[load(z,path) for path in FILES]

Y={}
for month in MONTHS:
 obs=np.zeros((31,3),dtype=float)
 for day in range(1,32):
  times=[f"{month}-{day:02d} {h:02d}:{mi:02d}:00" for h in range(6,18) for mi in range(0,60,5)]
  assert len(times)==144
  for j,ch in enumerate(iv):
   assert all(t in ch for t in times),("missing_daily",j,month,day)
   obs[day-1,j]=sum(ch[t] for t in times)/12./DC[j]
 assert all(abs(12*a-b)<.000004 for a,b in zip(obs.sum(axis=0),expected[month])),("R30_totals_fail",month,obs.sum(axis=0))
 Y[month]=obs
print("R30_INVERTER_ONLY_REPLAY_PASS",SHA,flush=True)

def allwindows(arr):
 for lost in range(3):
  peers=[j for j in range(3) if j!=lost]
  predictor=arr[:,peers].mean(axis=1)
  assert np.all(predictor>0),("nonpositive_peer_support",lost)
  for L in range(1,8):
   for st in range(32-L):
    mask=np.ones(31,dtype=bool); mask[st:st+L]=False
    pg=predictor[~mask].sum(); pr=predictor[mask].sum()
    xr=arr[mask,lost].sum()
    xg=arr[~mask,lost].sum()
    assert pg>0 and pr>0 and xr>0
    ratio_ref=xr/pr; ratio_gap=xg/pg
    yield {"lost":lost,"L":L,"st":st,"xgap":xg,"peer_gap":pg,
           "reference_ratio":ratio_ref,"gap_ratio":ratio_gap,
           "local_relative_error":ratio_gap/ratio_ref-1.0}
def get_calibration(months):
 delta=np.zeros(3); globe_min=np.full(3,float("inf")); globe_max=np.zeros(3)
 for m in months:
  arr=Y[m]
  for j in range(3):
   peers=[k for k in range(3) if k!=j]
   ratio=arr[:,j]/arr[:,peers].mean(axis=1)
   globe_min[j]=min(globe_min[j],float(ratio.min()))
   globe_max[j]=max(globe_max[j],float(ratio.max()))
  for w in allwindows(arr):
   j=w["lost"];delta[j]=max(delta[j],abs(w["local_relative_error"]))
 assert np.all(delta>0) and np.all(globe_min>0)
 return {"local_delta":delta, "global_lo":globe_min,"global_hi":globe_max}

cal_train=get_calibration(["2022-07"])
cal_train_val=get_calibration(["2022-07","2023-05"])
def shortlist(y,q):
 mx=max(y)
 return tuple(j for j,v in enumerate(y) if v>=mx*(1-q)-1e-10)
def membership_bounds(low,high,q):
 t=1-q
 nec=tuple(j for j in range(3) if all(low[j]+1e-10>=t*high[k] for k in range(3) if j!=k))
 pos=tuple(j for j in range(3) if all(high[j]+1e-10>=t*low[k] for k in range(3) if j!=k))
 return nec,pos
def interval(arr,win,cal,mode):
 j=win["lost"]; L=win["L"]; peer=win["peer_gap"]
 if mode=="physical":lo,hi=0.,CAP*12*L/DC[j]
 elif mode=="local":
  r=win["reference_ratio"]; delta=cal["local_delta"][j]
  lo,hi=peer*r*max(0.,1-delta),peer*r*(1+delta)
 elif mode=="global":lo,hi=peer*cal["global_lo"][j],peer*cal["global_hi"][j]
 else:raise ValueError(mode)
 cap=CAP*12*L/DC[j]
 lo=max(0.,float(lo));hi=min(float(hi),float(cap))
 empty=lo>hi+1e-9
 if empty:lo,hi=0.,float(cap)
 return lo,hi,empty

def evaluate(month,cal,stage):
 arr=Y[month];monthly=arr.sum(axis=0)
 allw=list(allwindows(arr)); assert len(allw)==588
 rows=[]
 for q in QV:
  actual_set=shortlist(monthly,q)
  for mode in ("physical","global","local"):
   records=[]; worst=[]
   for w in allw:
    lost=w["lost"]; actual=w["xgap"]
    observed=monthly.copy();observed[lost]-=actual
    lv,uv,empty=interval(arr,w,cal,mode)
    low=observed.copy();high=observed.copy()
    low[lost]+=lv;high[lost]+=uv
    nec,pos=membership_bounds(low,high,q)
    cert=(nec==pos)
    valid=(lv-1e-9<=actual<=uv+1e-9)
    wrong=bool(cert and nec!=actual_set)
    naive_wrong=bool(shortlist(observed,q)!=actual_set)
    records.append({"lost":lost+1,"L":w["L"],"st":w["st"]+1,
      "cert":cert,"wrong":wrong,"valid":valid,"empty":empty,
      "naive_wrong":naive_wrong,"corrected":bool(cert and not wrong and naive_wrong)})
   for lost in range(1,4):
    sub=[r for r in records if r["lost"]==lost]
    worst.append({"lost":lost,
       "n":len(sub),
       "cert":sum(r["cert"] for r in sub),
       "violations":sum(not r["valid"] for r in sub),
       "wrong_cert":sum(r["wrong"] for r in sub),
       "naive_wrong":sum(r["naive_wrong"] for r in sub),
       "corrected":sum(r["corrected"] for r in sub)})
   summary={"stage":stage,"month":month,"q_pct":100*q,"method":mode,
     "windows":len(records),"cert":sum(r["cert"] for r in records),
     "wrong_cert":sum(r["wrong"] for r in records),
     "bound_violations":sum(not r["valid"] for r in records),
     "bound_violations_among_cert":sum(r["cert"] and not r["valid"] for r in records),
     "naive_wrong":sum(r["naive_wrong"] for r in records),
     "corrected_naive_wrong":sum(r["corrected"] for r in records),
     "empty_interval_count":sum(r["empty"] for r in records),
     "devices":worst}
   rows.append(summary)
   print("SIM_GATE4_RESULT",json.dumps({k:v for k,v in summary.items() if k!="devices"},sort_keys=True),flush=True)
 return rows

evals=evaluate("2022-07",cal_train,"development_replay_not_holdout")
evals+=evaluate("2023-05",cal_train,"temporal_validation_no_tuning")
evals+=evaluate("2023-07",cal_train_val,"final_temporal_holdout_preceding_months_only")
# Invariants: physical results must not depend on calibration.
assert len(evals)==18 and all(r["windows"]==588 for r in evals)
assert all(r["naive_wrong"]==next(a["naive_wrong"] for a in evals
   if a["month"]==r["month"] and a["q_pct"]==r["q_pct"]) for r in evals)
# Strict outcome gate: lower than 100% peer coverage is not CERTIFY.
hold=[r for r in evals if r["stage"].startswith("final")]
peer_success=[r for r in hold if r["method"] in ("local","global") and
  r["bound_violations"]==0 and r["wrong_cert"]==0 and
  r["corrected_naive_wrong"]>0]
status={"gate":"SIM_GATE4_PEER_HOLDOUT","source_sha":SHA,
 "source_target":"HKUST Library one-inverter missing; end-of-month report",
 "data_roles":{"2022-07":"training","2023-05":"temporal validation",
               "2023-07":"final untouched holdout"},
 "calendar_gap_1_to_7":True,"n_windows_per_month_and_q":588,
 "calibration_train_delta":cal_train["local_delta"].tolist(),
 "calibration_train_val_delta":cal_train_val["local_delta"].tolist(),
 "calibration_train_global_lo":cal_train["global_lo"].tolist(),
 "calibration_train_global_hi":cal_train["global_hi"].tolist(),
 "calibration_train_val_global_lo":cal_train_val["global_lo"].tolist(),
 "calibration_train_val_global_hi":cal_train_val["global_hi"].tolist(),
 "no_site_channel":True,"no_weather":True,
 "operational_independence":"other inverter channel survival is a scenario, not verified separate acquisition path",
 "learned_envelopes":"historical extrema are not deterministic future guarantees even if an untouched holdout has no violations",
 "outcome":"EXPLORATORY_PASS_ZERO_VIOLATION_ON_FINITE_HOLDOUT" if peer_success else "HOLD_NO_ADMISSIBLE_OPERATIONAL_CERTIFICATE",
 "R40":"LOCKED_UNCHANGED","R41":"HOLD","results":evals}
(OUT/"SIM_GATE4_PREDECLARED_SPLIT_AND_RESULTS.json").write_text(json.dumps(status,indent=2),encoding="utf8")
with (OUT/"SIM_GATE4_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
 head=["stage","month","q_pct","method","windows","cert","wrong_cert",
       "bound_violations","bound_violations_among_cert","naive_wrong",
       "corrected_naive_wrong","empty_interval_count"]
 w=csv.DictWriter(f,fieldnames=head);w.writeheader()
 for r in evals:w.writerow({k:r[k] for k in head})
(OUT/"README_LIMITS.md").write_text("""# SIM-GATE4 (development, not journal results)
- Source SHA and R30 monthly source totals asserted before comparisons.
- All results use recorded inverter power only. Site-level power is omitted
  because it is derived from these channels (SIM-GATE3).
- Scenarios simulate only ONE inverter feed missing, and assume the other
  two device feeds continue, which is NOT confirmed under a field fault.
- Target ratio outside a test gap is available after month end only;
  these are retrospective reporting-time decisions, not live fault recovery.
- Development Jul 2022 -> validation May 2023 -> July 2023 final holdout.
- Local method: within-month retained-day peer ratio and a bounded relative
  departure learned from past months, all gaps enumerated.
- Global method: min/max daily target-to-peer ratio from past months.
- Physical comparator: conditional 50kW AC upper bound x 12 daylight hours.
- Both learned envelopes are empirical, NOT hard deterministic future bounds.
- Gap windows overlap strongly. Report counts, not independent trial rates.
- A finite zero-violation holdout is never sufficient to call CERTIFY.
- Do not modify R40 scientific claims without separate review.
""",encoding="utf8")
print("SIM_GATE4_SUMMARY",json.dumps({k:v for k,v in status.items() if k!="results"},sort_keys=True),flush=True)
