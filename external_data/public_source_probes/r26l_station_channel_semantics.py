#!/usr/bin/env python3
"""Inspect HKUST original site-level vs inverter-level daily energy semantics before admission."""
import zipfile,csv,io,collections,json,hashlib,statistics,math
from pathlib import Path
p=Path("source/dataset_original_Zenodo10909062.zip")
out=Path("R26L_Library_ChannelSemantics");out.mkdir(exist_ok=True)
h=hashlib.sha256()
with p.open("rb") as f:
    for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
assert h.hexdigest()=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
groups=["Library","S H Ho Sports Hall","Wong Check She Research Centre","Zone A2","Zone D"]
months=["2022-07","2022-08","2023-05","2023-07"]
response=[]
with zipfile.ZipFile(p) as z:
    names=z.namelist()
    for group in groups:
        station_matches=[x for x in names if x.endswith(f"/Site level dataset/{group}.csv")]
        inverter_matches=[x for x in names if "/Inverter level dataset/" in x and x.endswith(".csv") and x.split("/")[-1].startswith(group+"_Inverter")]
        assert len(station_matches)==1 and len(inverter_matches)>=2,(group,station_matches,inverter_matches)
        target=station_matches[0]
        station_rows=collections.defaultdict(list)
        with z.open(target) as f:
            dr=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace",newline=""))
            print("STATION_HEADERS",group,dr.fieldnames,flush=True)
            for row in dr:
                if row["Time"][:7] not in months: continue
                station_rows[row["Time"][:10]].append(row)
        subset=[];sample=[]
        for date,rs in station_rows.items():
            if date.endswith("-01"):
                sample=rs[20:72:6] # 05:00 to 18:00 preview
                break
        for date,rs in sorted(station_rows.items()):
            values=[]
            for row in rs:
                try:
                    if math.isfinite(float(row["power(W)"])):
                        values.append(float(row["power(W)"]))
                except:continue
            subset.append(dict(date=date,rows=len(rs),finite_power=len(values),
                              energy_from_power_rect_kWh=(sum(values)*.25/1000 if len(values)==len(rs) else None),
                              generation_examples=[r["generation(kWh)"] for r in rs[:5]]))
        print("STATION_SRC",group,"n_days",len(subset),
              "first",subset[:2],"sample",[{"Time":r["Time"],"generation(kWh)":r["generation(kWh)"],"power(W)":r["power(W)"]} for r in sample[:9]],
              flush=True)
        response.append({"group":group,"station_name":target,"inverter_names":inverter_matches,
                         "station_days":len(subset),"first_day":subset[:2],
                         "midday_sample":sample[:15]})
(out/"STATION_INVERTER_CHANNEL_SOURCE_PREVIEW.json").write_text(json.dumps(response,indent=2,ensure_ascii=False))
print("SOURCE_META_PREVIEW_PASS")
