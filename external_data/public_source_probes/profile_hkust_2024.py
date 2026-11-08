#!/usr/bin/env python3
"""R26H HKUST independent source admission screen. No q x L outcomes.

Uses exact publisher ZIP from prior pinned Zenodo 10909062 source-audit CI.
For each measured-power CSV, computes schema and complete source-clock days/months.
No resizing, interpolation, climate inference, or pooled counts. Qatar excluded.
"""
import collections,csv,datetime as dt,hashlib,io,json,re,zipfile
from pathlib import Path
root=Path("R26H_HKUST_FullSchemaGate");root.mkdir(exist_ok=True)
source=Path("hkust_source/dataset_original_Zenodo10909062.zip")
assert source.is_file(),f"missing source: {source}"
sha=hashlib.sha256()
with source.open('rb') as f:
    while True:
        b=f.read(2*1024*1024)
        if not b:break
        sha.update(b)
source_sha=sha.hexdigest()
assert source_sha=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec",source_sha
data={}
rows=[]
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    names=z.namelist()
    ttl=next(x for x in names if x.lower().endswith('.ttl'))
    with z.open(ttl) as f: t=f.read().decode('utf-8','replace')
    # Bounded source snippets, not wholesale raw TTL redistribution.
    filtered=[x.strip()[:260] for x in t.splitlines() if re.search(r'rated|capacity|kilowatt|watt|nominal|power|module|inverter',x,re.I)]
    (root/"RATED_POWER_METADATA_EXCERPTS.txt").write_text("\n".join(filtered[:200]),encoding='utf8')
    candidates=[x for x in names if '/PV generation dataset/' in x and x.lower().endswith('.csv') and 'Inverter' in x]
    print("CANDIDATE FILES",len(candidates),flush=True)
    for i,name in enumerate(candidates):
        with z.open(name) as f:
            rdr=csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace",newline=""))
            hdr=next(rdr)
            time_col=next((j for j,k in enumerate(hdr) if k.strip().lower()=="time"),None)
            ps=[j for j,k in enumerate(hdr) if re.search(r'(?:totalactivepower|activepower|power|energy)',k,re.I)]
            # Choose measured inverter totalActivePower, not monthly/optimizer metadata.
            power_col=next((j for j in ps if hdr[j].strip()=="totalActivePower(W)"),None)
            if power_col is None:
                power_col=next((j for j in ps if "total" in hdr[j].lower() and "power" in hdr[j].lower()),None)
            if time_col is None:continue
            byday=collections.Counter()
            bydayvalid=collections.Counter()
            timedups=0
            seen=set()
            negative=0;nonfinite=0;count=0;power_min=float('inf');power_max=float('-inf')
            all_ok=True
            for vals in rdr:
                if len(vals)<=time_col:continue
                ts=vals[time_col].strip()
                try:
                    # Handles YYYY/M/D H:MM and other standard source timestamp formats.
                    day=ts[:10].split(" ")[0]
                    day_obj=dt.date.fromisoformat(day.replace('/','-'))
                except Exception:
                    try: day_obj=dt.datetime.strptime(ts.split(' ')[0],'%Y/%m/%d').date()
                    except: continue
                count+=1
                byday[day_obj]+=1
                if ts in seen:timedups+=1
                else:seen.add(ts)
                if power_col is not None and len(vals)>power_col:
                    try:
                        p=float(vals[power_col].strip())
                        if p!=p or abs(p)==float('inf'):raise ValueError()
                        bydayvalid[day_obj]+=1
                        power_min=min(p,power_min);power_max=max(p,power_max)
                        if p<0:negative+=1
                    except:nonfinite+=1
            days=len(byday)
            permonth=collections.defaultdict(list)
            for day in sorted(byday):permonth[(day.year,day.month)].append(day)
            strict=[]
            for k, dates in permonth.items():
                ndays=(dt.date(k[0]+(k[1]==12),1 if k[1]==12 else k[1]+1,1)-dt.date(k[0],k[1],1)).days
                if len(dates)!=ndays:continue
                # Merely source-clock strict sample-count gate; 5-minute 24 h expected 288.
                if all(byday[d]==288 and bydayvalid[d]==288 for d in dates):
                    strict.append('%04d-%02d'%k)
            basename=Path(name).name
            stem=re.sub(r'_Inverter(?:_\d+)?\.csv$','',basename,flags=re.I)
            record={"path":name,"basename":basename,"group_stem":stem,
                    "source_rows":count,"distinct_source_days":days,
                    "first_day":str(min(byday)) if byday else None,
                    "last_day":str(max(byday)) if byday else None,
                    "time_duplicates":timedups,"headers":"|".join(hdr[:30]),
                    "power_col":hdr[power_col] if power_col is not None else "",
                    "missing_power_rows":nonfinite if power_col is not None else None,
                    "negative_power_rows":negative if power_col is not None else None,
                    "max_power_W":round(power_max,6) if power_col is not None and power_max!=float('-inf') else None,
                    "full_288row_days":sum(x==288 for x in byday.values()),
                    "strict_complete_calendar_months":len(strict),
                    "strict_months":";".join(strict)}
            rows.append(record)
            print(f"PROFILE {i+1}/{len(candidates)} {basename} n={count} fullDays={record['full_288row_days']} strictMonths={len(strict)}",flush=True)
    groups=collections.defaultdict(list)
    for r in rows:
        groups[r["group_stem"]].append(r["basename"])
    summary={"source_version":"Zenodo 10909062 original 2024, not later Dryad refresh",
             "source_sha256":source_sha,"files_in_zip":len(names),"candidate_inverter_files":len(rows),
             "inverter_groups":{k:v for k,v in groups.items() if len(v)>=2},
             "files_with_strict_complete_month":sum(r['strict_complete_calendar_months']>0 for r in rows),
             "total_file_level_strict_months_not_independent":sum(r['strict_complete_calendar_months'] for r in rows),
             "meanings":"strict sample-count checks only, not certification or q×L outcomes",
             "status":"HOLD source capacity crosswalk + UTC/local time + configuration + availability before empirical admission"}
    data=summary
with (root/"HKUST_SOURCE_FILE_PROFILES.csv").open("w",newline='',encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
(root/"HKUST_SOURCE_GATE_SUMMARY.json").write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print("SOURCE GATE SUMMARY",json.dumps(data,ensure_ascii=False),flush=True)
