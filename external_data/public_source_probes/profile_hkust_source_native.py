#!/usr/bin/env python3
"""R26H HKUST exact 06:00-17:55 native source clock admission only.

No q×L calculation, no results migration; report complete 144-slot observed
days/months per published 5-minute daytime source instead of forcing 24h/288 slots.
"""
from pathlib import Path
from collections import defaultdict,Counter
import datetime as dt,csv,io,zipfile,json,re,hashlib,math,calendar
out=Path("R26H_HKUST_144Slot_SourceGate");out.mkdir(exist_ok=True)
archive=Path("source/dataset_original_Zenodo10909062.zip")
assert archive.is_file()
h=hashlib.sha256()
with archive.open('rb') as f:
    for c in iter(lambda:f.read(2*1024*1024),b''): h.update(c)
assert h.hexdigest()=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
expected={f"{hh:02d}:{mm:02d}:00" for hh in range(6,18) for mm in range(0,60,5)}
assert len(expected)==144
records=[]; month_sets={}
with zipfile.ZipFile(archive) as z:
    data=[x for x in z.namelist() if '/PV generation dataset/' in x and '/Inverter level dataset/' in x and x.endswith('.csv')]
    for idx,name in enumerate(data):
        byday=defaultdict(lambda:{"seen":set(),"rows":0,"finite_power":0,"positive_power":0,"negative_power":0,"bad_ts":0})
        with z.open(name) as f:
            rd=csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig',errors='replace'))
            assert "Time" in rd.fieldnames and "totalActivePower(W)" in rd.fieldnames,(name,rd.fieldnames)
            for row in rd:
                t=row["Time"]
                try:
                    d,tod=t.split(' ')
                    date=dt.date.fromisoformat(d)
                except:
                    continue
                v=byday[date];v["rows"]+=1;v["seen"].add(tod)
                try:
                    p=float(row["totalActivePower(W)"])
                    if math.isfinite(p):
                        v["finite_power"]+=1
                        if p>0:v["positive_power"]+=1
                        if p<0:v["negative_power"]+=1
                except: pass
        days=sorted(byday)
        good={d for d,v in byday.items() if v["rows"]==144 and v["seen"]==expected and v["finite_power"]==144}
        months=defaultdict(list)
        for d in days: months[d.strftime('%Y-%m')].append(d)
        strict=[]
        for m,ds in months.items():
            year,month=map(int,m.split('-'))
            ndays=calendar.monthrange(year,month)[1]
            if len(ds)==ndays and all(d in good for d in ds):strict.append(m)
        file=Path(name).name
        group=re.sub(r'_Inverter(?:_\d+)?\.csv$','',file,flags=re.I)
        month_sets[file]=set(strict)
        row={
            "name":file,"station_group":group,"source_dates":len(byday),
            "full_native_144_slot_days":sum(v["rows"]==144 and v["seen"]==expected for v in byday.values()),
            "full_native_144_and_finite_power_days":len(good),
            "missing_power_observations":sum(v["rows"]-v["finite_power"] for v in byday.values()),
            "negative_power_observations":sum(v["negative_power"] for v in byday.values()),
            "months_strict_complete_144_and_finite":len(strict),
            "month_list":';'.join(sorted(strict)),
            "raw_max_date":str(max(byday)) if byday else None,
            "raw_min_date":str(min(byday)) if byday else None
        }
        records.append(row)
        print("NATIVE",idx+1,"/",len(data),file,"good days",len(good),"strict months",len(strict),flush=True)
groups=defaultdict(list)
for row in records:groups[row["station_group"]].append(row["name"])
group_rows=[]
for name,files in sorted(groups.items()):
    if len(files)<2:continue
    common=set.intersection(*(month_sets[f] for f in files))
    group_rows.append({"same_roof_group":name,"inverters":len(files),"files":';'.join(files),
                       "common_strict_months":len(common),"common_months":';'.join(sorted(common))})
with (out/"INVERTER_DAY_MONTH_SOURCE_GATE.csv").open('w',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=list(records[0].keys()));wr.writeheader();wr.writerows(records)
with (out/"COLOCATED_MULTIPLE_INVERTER_MONTH_GATE.csv").open('w',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=list(group_rows[0].keys()));wr.writeheader();wr.writerows(group_rows)
summary={
    "source":"Zenodo 10909062; April 2024 source only",
    "source_sha256":h.hexdigest(),
    "native_gate":"144 unique 5-min slots 06:00..17:55 per day, 144 finite observed powers, calendar-month all days",
    "files_tested":len(records),"same_roof_groups":len(group_rows),
    "files_with_one_or_more_strict_months":sum(r["months_strict_complete_144_and_finite"]>0 for r in records),
    "file_level_strict_months_not_independent":sum(r["months_strict_complete_144_and_finite"] for r in records),
    "same_roof_groups_with_common_strict_months":sum(r["common_strict_months"]>0 for r in group_rows),
    "source_claim":"SOURCE-CLOCK admission only; does not address DC STC or inverter AC rating comparison, interpolation provenance, or meteorological coverage",
    "scientific_state":"R25/R22 unchanged, R26H source-only"
}
(out/"NATIVE_SOURCE_GATE_SUMMARY.json").write_text(json.dumps(summary,indent=2))
print("FINAL_SUMMARY",json.dumps(summary),flush=True)
for x in group_rows:print("GROUP",json.dumps(x),flush=True)
