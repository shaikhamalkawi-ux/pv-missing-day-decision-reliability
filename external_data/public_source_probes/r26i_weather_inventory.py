#!/usr/bin/env python3
"""HKUST frozen original meteorological source inventory, research-only."""
from pathlib import Path
import csv,io,hashlib,zipfile,json
root=Path("R26I_HKUST_WeatherGate");root.mkdir(exist_ok=True)
p=Path("source/dataset_original_Zenodo10909062.zip")
h=hashlib.sha256()
with p.open("rb") as f:
    for c in iter(lambda:f.read(2*1024*1024),b""):h.update(c)
assert h.hexdigest()=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
rows=[]
with zipfile.ZipFile(p) as z:
    allcsv=[x for x in z.namelist() if x.lower().endswith(".csv")]
    for name in allcsv:
        if "/Weather" not in name and "/weather" not in name and "meteorolog" not in name.lower() and "solar irradiance" not in name.lower():
            continue
        with z.open(name) as src:
            rd=csv.reader(io.TextIOWrapper(src,encoding="utf-8-sig",errors="replace",newline=""))
            head=next(rd,[])
            samples=[next(rd,[]) for _ in range(3)]
        row=dict(name=name,header=head,samples=samples,size=z.getinfo(name).file_size)
        rows.append(row)
        print("WEATHER_SOURCE",json.dumps(row),flush=True)
    if not rows:
        print("WEATHER NAMING DIFFERENT; full candidate folder list:")
        for name in allcsv:
            if "PV generation" not in name: print("NONPV",name)
(root/"HKUST_SOURCE_WEATHER_INVENTORY.json").write_text(json.dumps(rows,indent=2,ensure_ascii=False))
print("WEATHER_CANDIDATE_FILES",len(rows))
