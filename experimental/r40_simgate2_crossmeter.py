#!/usr/bin/env python3
"""SIM-GATE2: source power-feed redundancy for a missing single inverter.

Scenario: one inverter telemetry stream is missing but site-level *power(W)*
and other two inverter streams remain available. This is conditional missing
feed design, NOT a demonstrated outage or independently calibrated meter.
All comparisons are performed on the measured-inverter shortlist target.
No imputation. Raw source is not republished.
"""
from __future__ import annotations
import csv,datetime as dt,hashlib,io,json,math,statistics,zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np

SRC=Path("source/dataset_original_Zenodo10909062.zip")
OUT=Path("R40_SIM_GATE2_CrossMeter");OUT.mkdir(exist_ok=True)
SHA="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
P="Dataset/Time series dataset/PV generation dataset/PV stations with panel level optimizer/"
FILES=[P+f"Inverter level dataset/Library_Inverter_{i}.csv" for i in range(1,4)]
SITE=P+"Site level dataset/Library.csv"
CAP=50000.
DC=[57720.,56240.,56240.]
MONTHS=["2022-07","2023-05","2023-07"]
Q_VALUES=[.05,.10,.03643601088]
TAUS=[.005,.01,.02,.05]
def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024),b""):h.update(block)
    return h.hexdigest()
assert sha256(SRC)==SHA
def timeparse(t):
    return dt.datetime.strptime(t,"%Y-%m-%d %H:%M:%S")
def valid_f(t):
    try:
        v=float(t)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError):
        return None
def records(z,path,column):
    d={};duplicate=0
    with z.open(path) as f:
        rdr=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
        assert "Time" in rdr.fieldnames and column in rdr.fieldnames,(path,rdr.fieldnames)
        for row in rdr:
            tt=row["Time"]
            if not any(tt.startswith(m) for m in MONTHS):continue
            try:t=timeparse(tt)
            except ValueError:continue
            if not (6<=t.hour<18 and t.minute%5==0):continue
            if t in d:
                duplicate+=1
                d[t]=None
            else:d[t]=valid_f(row[column])
    return d,{"name":path,"retained_timestamps":len(d),"duplicates":duplicate}
with zipfile.ZipFile(SRC) as z:
    stream=[];file_schema=[]
    with z.open(SITE) as sf:
        reader=csv.DictReader(io.TextIOWrapper(sf,encoding="utf-8-sig",newline=""))
        first=[];recent=[];monthly_stats=defaultdict(int)
        for src_row in reader:
            raw=src_row["Time"]
            if len(first)<3:first.append(raw)
            if raw.startswith("2022-07") or raw.startswith("2023"):
                if len(recent)<15:recent.append(raw)
            monthly_stats[raw[:7]]+=1
        print("SITE_NATIVE_TIMESTAMP_AUDIT",json.dumps({"first":first,"selected":recent,"month_prefix":dict(monthly_stats)},sort_keys=True),flush=True)
    for f in FILES:
        data,report=records(z,f,"totalActivePower(W)")
        stream.append(data);file_schema.append(report)
    site,report=records(z,SITE,"power(W)");file_schema.append(report)
print("SOURCE_SHA_PASS",SHA,"CHANNELS",json.dumps(file_schema),flush=True)
source_days={}
for month in MONTHS:
    for day in range(1,32):
        name=f"{month}-{day:02d}"
        stamps=[dt.datetime.strptime(f"{name} {h:02d}:{min_:02d}","%Y-%m-%d %H:%M")
                for h in range(6,18) for min_ in range(0,60,5)]
        vals=[]
        for ch,d in enumerate([*stream,site]):
            # Original HKUST publication: SITE 15-minute; INVERTER 5-minute.
            # Convert 15-min site rectangle integral to 5-min sample-equivalents.
            native_stamps=stamps if ch<3 else stamps[::3]
            vv=[d.get(t) for t in native_stamps]
            assert all(v is not None for v in vv),("incomplete_native_channel",month,day,ch)
            assert all(v>=0 for v in vv),("negative_source_P",month,day,ch)
            vals.append(float(sum(vv))*(1.0 if ch<3 else 3.0))
        source_days[name]={"p_inverters":np.array(vals[:3]),"p_site":vals[3]}
# Explicitly test whether each 15-minute site power sample can be
# reconstructed from 3 native 5-minute inverter samples. Numerical identity
# makes this source channel NOT independent evidence of missing-inverter power.
lineage_report={}
for month in MONTHS:
    direct=[];forward=[];backward=[];sumsite=[];suminv=[]
    for day in range(1,32):
        label=f"{month}-{day:02d}"
        for hour in range(6,18):
            for minute in range(0,60,15):
                t=dt.datetime.strptime(f"{label} {hour:02d}:{minute:02d}","%Y-%m-%d %H:%M")
                site_val=site[t]
                at_t=sum(v[t] for v in stream)
                mean_forward=sum(sum(v[t+dt.timedelta(minutes=k)] for v in stream) for k in (0,5,10))/3.0
                direct.append(site_val-at_t)
                forward.append(site_val-mean_forward)
                sumsite.append(site_val)
                suminv.append(mean_forward)
                if hour>6 or minute>=10:
                    prev=t-dt.timedelta(minutes=10)
                    mean_back=sum(sum(v[prev+dt.timedelta(minutes=k)] for v in stream) for k in (0,5,10))/3.0
                    backward.append(site_val-mean_back)
    lineage_report[month]={
       "n_15min":len(forward),
       "site_minus_same_inverter_instant_MAE_W":float(np.mean(np.abs(direct))),
       "site_minus_forward_three_sample_mean_MAE_W":float(np.mean(np.abs(forward))),
       "site_minus_forward_three_sample_mean_maxabs_W":float(np.max(np.abs(forward))),
       "forward_within_0p01W":int(sum(abs(x)<=0.01 for x in forward)),
       "forward_within_0p1W":int(sum(abs(x)<=0.1 for x in forward)),
       "forward_within_1W":int(sum(abs(x)<=1 for x in forward)),
       "site_minus_backward_three_sample_mean_MAE_W":float(np.mean(np.abs(backward))),
       "integrated_15min_site_vs_5min_inverter_rel_pct":float(100*(sum(sumsite)-sum(suminv))/max(1,sum(suminv))),
    }
print("SITE_FEED_LINEAGE",json.dumps(lineage_report,sort_keys=True),flush=True)
for month in MONTHS:
    sums=[sum(source_days[f"{month}-{d:02d}"]["p_inverters"][i]/DC[i] for d in range(1,32)) for i in range(3)]
    expect={"2022-07":[1163.758524,1590.833339,1534.450622],
            "2023-05":[1059.051906,1051.080868,937.457752],
            "2023-07":[1573.469577,1564.780903,1433.447635]}[month]
    assert all(abs(a-b)<.000004 for a,b in zip(sums,expect)),(month,sums,expect)
print("R30_ORIGINAL_MONTHLY_REPLAY_PASS",flush=True)
def shortlist(y,q):
    mx=max(y)
    return tuple(j for j,v in enumerate(y) if v>=mx*(1-q)-1e-10)
def bounds(lo,hi,q):
    nec=[];pos=[];c=1-q
    for j in range(3):
        if all(lo[j]+1e-10>=c*hi[k] for k in range(3) if j!=k):nec.append(j)
        if all(hi[j]+1e-10>=c*lo[k] for k in range(3) if j!=k):pos.append(j)
    return tuple(nec),tuple(pos)
month_eval={}
for month in MONTHS:
    names=[f"{month}-{d:02d}" for d in range(1,32)]
    deltas=[]
    for name in names:
        rec=source_days[name]
        diff=rec["p_site"]-float(sum(rec["p_inverters"]))
        deltas.append(diff/max(1e-9,rec["p_site"]))
    month_eval[month]={
        "days":len(deltas),
        "median_absolute_site_power_vs_sum_pct":float(100*np.median(abs(np.array(deltas)))),
        "max_absolute_site_power_vs_sum_pct":float(100*np.max(abs(np.array(deltas)))),
        "above_1pct_days":int(sum(abs(d)>.01 for d in deltas)),
        "above_2pct_days":int(sum(abs(d)>.02 for d in deltas)),
        "above_5pct_days":int(sum(abs(d)>.05 for d in deltas))}
train_max=max(abs(source_days[f"2022-07-{d:02d}"]["p_site"]-float(sum(source_days[f"2022-07-{d:02d}"]["p_inverters"])))/max(1.,source_days[f"2022-07-{d:02d}"]["p_site"]) for d in range(1,32))
print("SOURCE_SITE_POWER_AGREEMENT",json.dumps({"monthly":month_eval,"site_lineage":lineage_report,"training_maxabs_ratio":train_max}),flush=True)

rows=[]
for q in Q_VALUES:
  for tol in sorted(set([*TAUS,train_max])):
    data=[]
    for month in MONTHS:
      keys=[f"{month}-{d:02d}" for d in range(1,32)]
      full=np.array([sum(source_days[k]["p_inverters"][j]/DC[j] for k in keys) for j in range(3)])
      fullset=shortlist(full,q)
      for lost in range(3):
       for L in range(1,8):
        for st in range(0,len(keys)-L+1):
          gap=keys[st:st+L]
          missing_actual=sum(source_days[d]["p_inverters"][lost] for d in gap)/DC[lost]
          others=sum(source_days[d]["p_inverters"].sum()-source_days[d]["p_inverters"][lost] for d in gap)
          sitep=sum(source_days[d]["p_site"] for d in gap)
          inferred=(sitep-others)/DC[lost]
          fuzz=tol*sitep/DC[lost]
          cap=50000*144*L/DC[lost]
          lo_v=max(0.,inferred-fuzz)
          hi_v=min(cap,inferred+fuzz)
          no_support=bool(lo_v>hi_v)
          if no_support:lo_v,hi_v=0.,cap
          observed=full.copy();observed[lost]-=missing_actual
          lo=observed.copy();hi=observed.copy()
          lo[lost]+=lo_v;hi[lost]+=hi_v
          nec,pos=bounds(lo,hi,q)
          cert=(nec==pos)
          actual_support=lo_v-1e-9<=missing_actual<=hi_v+1e-9
          physical_lo=observed.copy();physical_hi=observed.copy()
          physical_hi[lost]+=cap
          bnec,bpos=bounds(physical_lo,physical_hi,q)
          physical_cert=bnec==bpos
          baseline=shortlist(observed,q)
          data.append({"q_pct":q*100,"month":month,"tol":tol,
             "lost":lost+1,"L":L,"st":st,"cert":cert,
             "wrong":bool(cert and nec!=fullset),
             "bound_valid":actual_support,"no_support":no_support,
             "naive_wrong":baseline!=fullset,"physical_cert":physical_cert,
             "cert_corrects_naive":bool(cert and nec==fullset and baseline!=fullset),
             "cert_adds_to_physical":bool(cert and not physical_cert),
             "signed_total_diff_pct":float(100*(sitep-sum(source_days[d]["p_inverters"].sum() for d in gap))/max(sitep,1e-9))})
    for subset in ["train_2022_07","holdout_2023","all_3_months"]:
        if subset=="train_2022_07":rr=[r for r in data if r["month"]=="2022-07"]
        elif subset=="holdout_2023":rr=[r for r in data if r["month"]!="2022-07"]
        else:rr=data
        if not rr:continue
        rec={"q_pct":q*100,"tolerance_pct":100*tol,"subset":subset,
           "n":len(rr),
           "cert":sum(r["cert"] for r in rr),
           "wrong":sum(r["wrong"] for r in rr),
           "bound_violations":sum(not r["bound_valid"] for r in rr),
           "bound_violations_among_cert":sum(r["cert"] and not r["bound_valid"] for r in rr),
           "empty_bound_support":sum(r["no_support"] for r in rr),
           "baseline_naive_wrong":sum(r["naive_wrong"] for r in rr),
           "physical_cert":sum(r["physical_cert"] for r in rr),
           "extra_cert_over_physical":sum(r["cert_adds_to_physical"] for r in rr),
           "corrected_naive_errors_by_cert":sum(r["cert_corrects_naive"] for r in rr)}
        rows.append(rec)
        if (abs(tol-.01)<1e-9 or abs(tol-.02)<1e-9 or abs(tol-.05)<1e-9 or abs(tol-train_max)<1e-9):
            print("CROSSMETER_RESULT",json.dumps(rec,sort_keys=True),flush=True)
status={"source_sha256":SHA,"no_imputation":True,
  "site_telemetry_independence":"NOT ESTABLISHED; conditional site feed survival",
  "instrument_5pct_is_not_deterministic_crossmeter_tolerance":True,
  "comparison":"site power(W) sum vs three measured inverter totalActivePower(W); site generation(kWh) NOT used",
  "fundamental_boundary":"The 2022 empirical maximum or a site percent tolerance is not a guaranteed future bound.",
  "R40_locked":True,"R41_status":"HOLD","monthly":month_eval,
  "train_max_site_fraction":train_max,
  "results":rows}
(OUT/"CROSSMETER_RESULTS.json").write_text(json.dumps(status,indent=2),encoding="utf-8")
with (OUT/"CROSSMETER_SUMMARY.csv").open("w",newline="") as f:
    keys=list(rows[0].keys());w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
print("R40_SIM_GATE2_CROSSMETER_DONE",json.dumps({"source":SHA,"train_max_pct":100*train_max,
   "q5_holdout_2pct":next((z for z in rows if z["q_pct"]==5.0 and
    abs(z["tolerance_pct"]-2.)<1e-9 and z["subset"]=="holdout_2023"),{}),
   "n_runs":len(rows)}),flush=True)
