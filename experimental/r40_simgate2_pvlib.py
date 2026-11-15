#!/usr/bin/env python3
"""R40 SIM-GATE2: chronological HKUST weather-conditioned PV decision audit.

Only source-authenticated experimental sensitivity. The pyranometer's
"Irradiance" is NOT certified GHI or array POA; treating as horizontal
irradiance is an explicit modeling assumption. No point prediction or
historical residual envelope is a deterministic PV decision guarantee.
No raw source bytes written to output.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, io, json, math, os, platform, statistics, sys, zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
import pvlib

SOURCE = Path("source/dataset_original_Zenodo10909062.zip")
SHA = "610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
OUT = Path("R40_SIM_GATE2_PhysicsAudit"); OUT.mkdir(exist_ok=True)
ROOT = "Dataset/Time series dataset/"
MET = ROOT + "Meteorological dataset/"
INV = ROOT + "PV generation dataset/PV stations with panel level optimizer/Inverter level dataset/"
MONTHS=("2022-07","2023-05","2023-07")
YEARS={"2022":["2022-07"],"2023":["2023-05","2023-07"]}
NAMES=[f"Library_Inverter_{k}.csv" for k in (1,2,3)]
DC=np.array([57720.0,56240.0,56240.0])
CAP_W=50000.0 # Source RDF names SE50K, official AC nameplate; physical interpretation conditional
TZ="Asia/Hong_Kong"
SOURCE_LAT_LON=(22.3363,114.2634) # Paper campus site coordinates; weather station positional proxy
RDF_LIBRARY_LAT_LON=(22.28,114.17) # Source Brick RDF, unusual vs campus
SCENARIOS=[("tilt10_south",10,180,SOURCE_LAT_LON),
           ("tilt20_south",20,180,SOURCE_LAT_LON),
           ("tilt30_south",30,180,SOURCE_LAT_LON),
           ("tilt20_southeast",20,135,SOURCE_LAT_LON),
           ("tilt20_southwest",20,225,SOURCE_LAT_LON),
           ("tilt20_RDF_coord",20,180,RDF_LIBRARY_LAT_LON)]
Q_LIST=(.05,.10,.03643601088)
R_MULT=(1.0,1.5,2.0,3.0)
def hfile(path):
    sha=hashlib.sha256()
    with path.open("rb") as fd:
        for chunk in iter(lambda:fd.read(8*1024*1024),b""):sha.update(chunk)
    return sha.hexdigest()
def parse_time(s):
    return dt.datetime.strptime(s,"%Y/%m/%d %H:%M")
def finite_f(s):
    try:
        v=float(s)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError):
        return None
def parse_month(s):
    return s[:7].replace("/","-")
def source_series(z, path, key, wanted):
    d={}; duplicates=0; invalid=0
    with z.open(path) as fd:
        reader=csv.DictReader(io.TextIOWrapper(fd,encoding="utf-8-sig",errors="strict",newline=""))
        assert "Time" in reader.fieldnames and key in reader.fieldnames,(path,reader.fieldnames)
        for row in reader:
            t=row["Time"]
            try: tt=parse_time(t)
            except ValueError:continue
            ym=f"{tt.year:04d}-{tt.month:02d}"
            if ym not in wanted:continue
            if not (6<=tt.hour<18 and tt.minute%5==0): continue
            if tt in d: duplicates+=1; d[tt]=None;continue
            value=finite_f(row[key]); d[tt]=value
            if value is None:invalid+=1
    return d,{"path":path,"rows":len(d),"duplicates":duplicates,"invalid":invalid}
def shortlist(vec,q):
    m=max(vec)
    return tuple(k for k,v in enumerate(vec) if v>=m*(1-q)-1e-9)
def interval_decision(lo,hi,q):
    necessary=[];possible=[];c=1-q
    for i in range(3):
        n=all(lo[i]+1e-9>=c*hi[j] for j in range(3) if i!=j)
        p=all(hi[i]+1e-9>=c*lo[j] for j in range(3) if i!=j)
        if n:necessary.append(i)
        if p:possible.append(i)
    return tuple(necessary),tuple(possible)
def pair_decision(obs,preds,ris,q,L):
    # Pairwise residual support is conditional and not a deterministic bound.
    necessary=[];possible=[];c=1-q
    for i in range(3):
        tests=[]
        for j in range(3):
            if i==j:continue
            score=obs[i]-c*obs[j]+preds[i]-c*preds[j]
            delta=L*ris[i,j]
            tests.append((score-delta>=-1e-9,score+delta>=-1e-9))
        if all(x[0] for x in tests):necessary.append(i)
        if all(x[1] for x in tests):possible.append(i)
    return tuple(necessary),tuple(possible)

assert SOURCE.is_file()
sha=hfile(SOURCE)
assert sha==SHA,(sha,SHA)
readbacks=[]
weather={}
daily_actual={}
with zipfile.ZipFile(SOURCE) as z:
    for year in YEARS:
        for param,sub,key in [("ghi","Irradiance","Irradiance (W/m2)"),
                               ("temp_air","Temperature","Temp (Degree Celsius)"),
                               ("wind_speed","Wind","Wind Speed (m/s)")]:
            name=f"{MET}{sub}/{sub}_{year}.csv"
            d,summary=source_series(z,name,key,YEARS[year])
            readbacks.append(summary)
            weather[(year,param)]=d
    for idx,name in enumerate(NAMES):
        path=INV+name
        d,summary=source_series(z,path,"totalActivePower(W)",MONTHS)
        readbacks.append(summary)
        daily_actual[idx]=d
print("SOURCE_SHA256_PASS",sha, "source_size",SOURCE.stat().st_size,flush=True)
for x in readbacks:print("SOURCE_SCHEMA",json.dumps(x),flush=True)

# Compare native exact observed complete month aggregates to R30 locked derived records.
daykeys=defaultdict(list)
for month in MONTHS:
    year=month[:4]
    if year=="2022": daycount=31
    else: daycount=31
    for day in range(1,daycount+1):
        date=f"{month}-{day:02d}"
        ts=[dt.datetime.strptime(f"{date} {h:02d}:{m:02d}","%Y-%m-%d %H:%M")
            for h in range(6,18) for m in range(0,60,5)]
        daykeys[month].append((date,ts))
daily_obs={}
full={}
support={}
weather_input={}
for month,days in daykeys.items():
    totals=np.zeros(3)
    ws=[]
    for date,ts in days:
        for j in range(3):
            values=[daily_actual[j].get(t,None) for t in ts]
            assert all(v is not None for v in values),("power_month_not_complete",month,date,j)
            assert all(v>=0 for v in values),("negative_power",month,date,j)
            value=sum(values)/DC[j]
            daily_obs[(date,j)]=value
            totals[j]+=value
        year=month[:4]
        record={}
        for key in ("ghi","temp_air","wind_speed"):
            vals=[weather[(year,key)].get(t,None) for t in ts]
            record[key]=vals
        valid=all(all(v is not None for v in record[key]) for key in record)
        if valid:
            for m,t in enumerate(ts):
                ws.append((t,record["ghi"][m],record["temp_air"][m],record["wind_speed"][m],date))
        support[date]=bool(valid)
    full[month]=totals
    weather_input[month]=ws
replay={"2022-07":[1163.758524,1590.833339,1534.450622],
        "2023-05":[1059.051906,1051.080868,937.457752],
        "2023-07":[1573.469577,1564.780903,1433.447635]}
for month in MONTHS:
    for j in range(3):
        assert abs(full[month][j]-replay[month][j])<0.000004,(
            "raw_R30_replay_mismatch",month,j,full[month][j],replay[month][j])
print("R30_MONTHLY_REPLAY_PASS",json.dumps({m:[round(float(v),6) for v in full[m]] for m in MONTHS}),flush=True)
print("WEATHER_SUPPORT",json.dumps({m:{"complete_days":sum(support[d] for d,_ in daykeys[m]),
                                              "days":len(daykeys[m]),
                                              "failed_dates":[d for d,_ in daykeys[m] if not support[d]]} for m in MONTHS}),flush=True)

def simulate(scenario):
    _,tilt,azimuth,(latitude,longitude)=scenario
    samples=[r for month in MONTHS for r in weather_input[month]]
    idx=pd.DatetimeIndex([r[0] for r in samples]).tz_localize(TZ)
    ghi=pd.Series([r[1] for r in samples],index=idx,dtype=float).clip(lower=0)
    tair=pd.Series([r[2] for r in samples],index=idx,dtype=float)
    wind=pd.Series([max(0,r[3]) for r in samples],index=idx,dtype=float)
    loc=pvlib.location.Location(latitude,longitude,tz=TZ)
    sp=loc.get_solarposition(idx)
    trans=pvlib.irradiance.erbs(ghi,sp["zenith"],idx)
    poa=pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,surface_azimuth=azimuth,
        solar_zenith=sp["zenith"],solar_azimuth=sp["azimuth"],
        dni=trans["dni"],dhi=trans["dhi"],ghi=ghi,model="isotropic"
    )["poa_global"].clip(lower=0).fillna(0)
    temp=pvlib.temperature.sapm_cell(poa,tair,wind,a=-3.56,b=-0.075,deltaT=3)
    daily={j:defaultdict(float) for j in range(3)}
    for j in range(3):
        dc=pvlib.pvsystem.pvwatts_dc(
            effective_irradiance=poa,temp_cell=temp,pdc0=float(DC[j]),gamma_pdc=-0.0035
        )
        ac=pvlib.inverter.pvwatts(dc,pdc0=CAP_W/.96,eta_inv_nom=.96)
        for date,v in zip([r[4] for r in samples],np.asarray(ac)):
            assert math.isfinite(float(v)),("bad_pvlib",scenario,j,date,v)
            daily[j][date]+=max(0.0,float(v))/DC[j]
    return daily

def report_scenario(scenario):
    name=scenario[0]
    sim=simulate(scenario)
    train_dates=[d for d,_ in daykeys["2022-07"] if support[d]]
    holdout_dates=[d for m in ("2023-05","2023-07") for d,_ in daykeys[m] if support[d]]
    scales=[]
    for j in range(3):
        x=np.array([sim[j][d] for d in train_dates])
        y=np.array([daily_obs[(d,j)] for d in train_dates])
        scale=float(np.dot(x,y)/np.dot(x,x))
        assert math.isfinite(scale) and 0<scale<8,("bad_scale",name,j,scale)
        scales.append(scale)
    pred={j:{d:sim[j][d]*scales[j] for d in train_dates+holdout_dates} for j in range(3)}
    residual={j:{d:daily_obs[(d,j)]-pred[j][d] for d in train_dates+holdout_dates} for j in range(3)}
    rdev=np.array([max(abs(residual[j][d]) for d in train_dates) for j in range(3)])
    evaluation={}
    for j in range(3):
        test=np.array([residual[j][d] for d in holdout_dates])
        y=np.array([daily_obs[(d,j)] for d in holdout_dates])
        evaluation[j+1]={"mean_abs_error_normalized_day":float(np.mean(abs(test))),
                         "mean_absolute_percentage_day":float(np.mean(abs(test)/np.maximum(y,1e-9))*100),
                         "holdout_days":len(test),
                         "holdout_fraction_outside_train_maxabs":float(np.mean(abs(test)>rdev[j]+1e-9)),
                         "training_maxabs":float(rdev[j]),
                         "calibration_scale":float(scales[j])}
    counter=[]
    for q in Q_LIST:
      for rmult in R_MULT:
        # Single-device missing, other two complete. Compare empirical-weather
        # interval vs exact conservative device hardware cap.
        n=0;cert=0;wrong=0;badbound=0;naive_wrong=0;baseline_cert=0;improved=0;outside_on_cert=0
        # All three inverters missing. Pairwise residual envelopes share weather.
        nall=0;certall=0;wrongall=0;badpair=0;naiveall=0;badpair_on_cert=0
        pair_train=np.zeros((3,3))
        c=1-q
        for j in range(3):
          for k in range(3):
            if j!=k:
              pair_train[j,k]=max(abs(residual[j][d]-c*residual[k][d]) for d in train_dates)*rmult
        for month in ("2023-05","2023-07"):
            true=shortlist(full[month],q)
            days=[d for d,_ in daykeys[month]]
            for L in range(1,8):
                for start in range(0,len(days)-L+1):
                    missing=days[start:start+L]
                    if not all(support[d] for d in missing):continue
                    pred_gap=np.array([sum(pred[j][d] for d in missing) for j in range(3)])
                    actual_gap=np.array([sum(daily_obs[(d,j)] for d in missing) for j in range(3)])
                    known=full[month]-actual_gap
                    nall+=1
                    baseline=shortlist(known,q)
                    if baseline!=true:naiveall+=1
                    pnec,ppos=pair_decision(known,pred_gap,pair_train,q,L)
                    all_cert=pnec==ppos
                    true_pair_max=0.0
                    for j in range(3):
                       for k in range(3):
                           if j!=k:
                               v=abs((actual_gap[j]-c*actual_gap[k])-(pred_gap[j]-c*pred_gap[k]))
                               true_pair_max=max(true_pair_max,v/(L*pair_train[j,k]+1e-12))
                    pair_valid=true_pair_max<=1+1e-10
                    if not pair_valid:badpair+=1
                    if all_cert:
                        certall+=1
                        if pnec!=true:wrongall+=1
                        if not pair_valid:badpair_on_cert+=1
                    for lost in range(3):
                        n+=1
                        known_single=np.array(full[month]);known_single[lost]-=actual_gap[lost]
                        baseline_single=shortlist(known_single,q)
                        if baseline_single!=true:naive_wrong+=1
                        lo=known_single.copy()
                        hi=known_single.copy()
                        upper=float(CAP_W*144*L/DC[lost])
                        env_lo=max(0.0,pred_gap[lost]-L*rdev[lost]*rmult)
                        env_hi=min(upper,pred_gap[lost]+L*rdev[lost]*rmult)
                        # Empty intersection is itself a model support violation.
                        if env_lo>env_hi:
                            env_lo,env_hi=0.0,upper
                        lo[lost]+=env_lo;hi[lost]+=env_hi
                        enec,epos=interval_decision(lo,hi,q)
                        iscert=enec==epos
                        valid=(env_lo-1e-9 <= actual_gap[lost] <= env_hi+1e-9)
                        if not valid:badbound+=1
                        h_lo=known_single.copy();h_hi=known_single.copy()
                        h_hi[lost]+=upper
                        hnec,hpos=interval_decision(h_lo,h_hi,q)
                        hc=hnec==hpos
                        if hc:baseline_cert+=1
                        if iscert:
                            cert+=1
                            if enec!=true:wrong+=1
                            if not valid:outside_on_cert+=1
                            if not hc:improved+=1
        counter.append({"q_pct":100*q,"envelope_multiplier":rmult,
              "single_total":n,"single_weather_cert":cert,"single_weather_wrong":wrong,
              "single_weather_bound_violations":badbound,
              "single_weather_bound_violations_among_certs":outside_on_cert,
              "single_physical_cert":baseline_cert,
              "single_weather_cert_beyond_physical":improved,
              "single_naive_wrong":naive_wrong,
              "all_total":nall,"all_weather_cert":certall,"all_weather_wrong":wrongall,
              "all_pair_window_violations":badpair,"all_pair_window_violations_among_certs":badpair_on_cert,
              "all_naive_wrong":naiveall})
    return {"scenario":name,"pvlib_model":"PVWatts DC and inverter, ERBS GHI assumed, isotropic POA, SAPM temp conditional",
            "geometry":{"tilt_deg":scenario[1],"azimuth_deg":scenario[2],"lat":scenario[3][0],"lon":scenario[3][1]},
            "model_parameters_assumptions":{"gamma_pdc_per_C":-0.0035,
                          "sapm_temp_a":-3.56,"sapm_temp_b":-.075,"sapm_deltaT":3,
                          "inverter_pac_limit_W":50000.0,
                          "irradiance_as_GHI":"UNVERIFIED_ASSUMPTION",
                          "clock_timezone":"Asia/Hong_Kong_UNVERIFIED"},
            "evaluation":evaluation,"counts":counter}

all_results=[]
for scenario in SCENARIOS:
    print("RUNNING_PHYSICAL_SCENARIO",scenario[0],flush=True)
    report=report_scenario(scenario)
    all_results.append(report)
    print("SCENARIO_STATUS",report["scenario"],
          "dev1_MAE",round(report["evaluation"][1]["mean_abs_error_normalized_day"],5),
          "out_of_sample_day_fraction",round(report["evaluation"][1]["holdout_fraction_outside_train_maxabs"],4),
          flush=True)
    for p in report["counts"]:
       if p["q_pct"] in (5.0,10.0) and p["envelope_multiplier"] in (1.0,2.0,3.0):
          print("RESULT_JSON",json.dumps({"scenario":report["scenario"],**p},sort_keys=True),flush=True)
result={"status":"EXPLORATORY_ONLY_NOT_CERTIFIED",
        "source_sha256":sha,"source_original_bytes":SOURCE.stat().st_size,
        "source_generation_integrity":"R30_MONTHLY_REPLAY_PASS",
        "source_slots_and_weather":{m:{"days":len(daykeys[m]),
               "weather_complete":sum(support[d] for d,_ in daykeys[m]),
               "weather_incomplete_dates":[d for d,_ in daykeys[m] if not support[d]]} for m in MONTHS},
        "train":"2022-07","test":["2023-05","2023-07"],
        "cohort_dependency":"daily/window overlap; counts NOT independent",
        "certification_warning":"Historic maximum residuals do not guarantee future support. Counts are retrospective conditional screens.",
        "R40_status":"LOCKED_NO_CHANGE","R41_status":"HOLD", 
        "environment":{"python":sys.version,"pvlib":pvlib.__version__,"numpy":np.__version__,"pandas":pd.__version__},
        "scenarios":all_results}
(OUT/"RESULTS.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
print("R40_SIM_GATE2_WEATHER_PVLIB_FINISHED",json.dumps({
 "scenario_count":len(all_results),"source_sha":sha,
 "training":"2022-07","test":"2023-05 and 2023-07",
 "weather_july30_excluded": True,
 "no_deterministic_certificate_claim":True}),flush=True)
