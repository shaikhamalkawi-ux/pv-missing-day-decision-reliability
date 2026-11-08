#!/usr/bin/env python3
"""R26I HKUST shared weather irradiance support at native 5-min device timestamps.
This is descriptive source validation, not same-plane POA calibration. No imputation.
"""
import csv,datetime as dt,collections,math,json,zipfile,hashlib,calendar
from pathlib import Path
out=Path("R26I_HKUST_WeatherAlignment");out.mkdir(exist_ok=True)
src=Path("source/dataset_original_Zenodo10909062.zip")
h=hashlib.sha256()
with src.open("rb") as f:
    for c in iter(lambda:f.read(2*1024*1024),b''):h.update(c)
assert h.hexdigest()=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
months=["2022-07","2022-08","2023-05","2023-07"]
targets=set()
for m in months:
    yy,mm=map(int,m.split('-'));n=calendar.monthrange(yy,mm)[1]
    for day in range(1,n+1):
        for h in range(6,18):
            for mi in range(0,60,5):
                targets.add(f"{yy:04d}-{mm:02d}-{day:02d} {h:02d}:{mi:02d}")
seen=collections.defaultdict(list)
with zipfile.ZipFile(src) as z:
    names=z.namelist()
    files=[x for x in names if x.endswith(("Irradiance_2022.csv","Irradiance_2023.csv")) and "/Irradiance/" in x]
    assert len(files)==2,files
    for name in files:
        with z.open(name) as raw:
            import io
            rdr=csv.DictReader(io.TextIOWrapper(raw,encoding="utf-8-sig",errors="replace"))
            assert "Time" in rdr.fieldnames and "Irradiance (W/m2)" in rdr.fieldnames
            for row in rdr:
                time=row["Time"]
                try:
                    dtm=dt.datetime.strptime(time,"%Y/%m/%d %H:%M")
                except ValueError:
                    continue
                t=dtm.strftime("%Y-%m-%d %H:%M")
                if t not in targets:continue
                try:
                    val=float(row["Irradiance (W/m2)"])
                except:val=float('nan')
                seen[t].append(val)
    records=[];monthly=collections.defaultdict(list)
    for m in months:
        yy,mm=map(int,m.split("-"))
        n=calendar.monthrange(yy,mm)[1]
        for d in range(1,n+1):
            day=f"{m}-{d:02d}"
            all_slots=[f"{day} {h:02d}:{mi:02d}" for h in range(6,18) for mi in range(0,60,5)]
            present=sum(bool(seen.get(t)) for t in all_slots)
            finite=sum(len(seen.get(t,[]))==1 and math.isfinite(seen[t][0]) for t in all_slots)
            duplicates=sum(len(seen.get(t,[]))>1 for t in all_slots)
            neg=sum(len(seen.get(t,[]))==1 and math.isfinite(seen[t][0]) and seen[t][0]<0 for t in all_slots)
            row=dict(month=m,date=day,expected_5min_slots=144,present_slots=present,
                     finite_unique_slots=finite,duplicates=duplicates,negative_irradiance=neg,
                     full_weather_support=int(finite==144 and duplicates==0),
                     is_site_level_not_plane_of_array=True)
            records.append(row);monthly[m].append(row)
    assert len(records)==sum(calendar.monthrange(*map(int,m.split("-")))[1] for m in months)
with (out/"WEATHER_DAY_FIVE_MIN_ALIGNMENT.csv").open("w",newline="",encoding="utf8") as f:
    wr=csv.DictWriter(f,fieldnames=list(records[0]));wr.writeheader();wr.writerows(records)
summaries=[]
for m,rs in monthly.items():
    summaries.append(dict(month=m,days=len(rs),days_full_weather_support=sum(r["full_weather_support"] for r in rs),
                          total_expected_slots=sum(r["expected_5min_slots"] for r in rs),
                          finite_unique_slots=sum(r["finite_unique_slots"] for r in rs),
                          days_with_duplicates=sum(r["duplicates"]>0 for r in rs),
                          days_negative_irradiance=sum(r["negative_irradiance"]>0 for r in rs)))
with (out/"WEATHER_MONTH_SUPPORT.csv").open("w",newline="",encoding="utf8") as f:
    wr=csv.DictWriter(f,fieldnames=list(summaries[0]));wr.writeheader();wr.writerows(summaries)
summary={
 "source":"HKUST 2024 original Zenodo 10909062",
 "source_sha256":h.hexdigest(),
 "comparison_months":months,
 "weather":"on-campus Irradiance(W/m2) at 1-minute source clock, checked at each 5-minute PV inverter stamp",
 "NOT_PLANE_OF_ARRAY":"Weather station is shared across campus; no inverter-specific POA or plane/tilt calibration",
 "months":summaries,
 "data_filling":False,
 "reference_R25_R22_unchanged":True}
(out/"WEATHER_ALIGNMENT_CERTIFICATE.json").write_text(json.dumps(summary,indent=2))
for s in summaries:print("WEATHER_MONTH",json.dumps(s),flush=True)
print("R26I_WEATHER_NATIVE_GATE_PASS",flush=True)
