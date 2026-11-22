#!/usr/bin/env python3
"""Derived-only magnitude of retrospective shortlist membership changes.

Read the original pinned MORE-EU 14-array source. This does not infer financial
cost, real outages, PV faults or independent-trial probabilities.
"""
import csv, io, json, hashlib, calendar, math
from collections import defaultdict, Counter
from pathlib import Path

EXPECTED_BLOB="5611277efdd581bb839ec380239846a43ebe0ba7"
def run(source, out):
    raw=Path(source).read_bytes()
    got=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    assert got==EXPECTED_BLOB,(got,EXPECTED_BLOB)
    src=csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    head=next(src)
    assert len(head)==15 and head[0]=="Timestamp"
    byday={}
    nrows=0
    for row in src:
        nrows+=1
        assert len(row)==15
        datestr,clock=row[0].split()
        d,m,y=map(int,datestr.split("/"))
        date=f"{2000+y:04d}-{m:02d}-{d:02d}"
        rec=byday.setdefault(date,{"clocks":set(),"sum":[0.0]*14,"count":0,"duplicate":False})
        if clock in rec["clocks"]:rec["duplicate"]=True
        rec["clocks"].add(clock)
        rec["count"]+=1
        for j,z in enumerate(row[1:]):
            v=float(z);assert math.isfinite(v)
            rec["sum"][j]+=v
    assert nrows==280512,nrows
    allmonths=defaultdict(list)
    for day,rec in byday.items():allmonths[day[:7]].append((day,rec))
    months=[]
    for month,records in sorted(allmonths.items()):
        year,mo=map(int,month.split("-"))
        days=calendar.monthrange(year,mo)[1]
        if len(records)!=days or any(r["count"]!=96 or len(r["clocks"])!=96 or r["duplicate"] for _,r in records):
            continue
        months.append((month,sorted(records)))
    assert len(months)==79,len(months)
    q=.05
    count=Counter()
    samples=[]
    months_mixed=0
    months_with_flip=0
    led=[]
    for month,dayrecs in months:
        n=len(dayrecs)
        values=[r["sum"] for _,r in dayrecs]
        full=[sum(v[j] for v in values) for j in range(14)]
        assert max(full)>0
        def shortlist(v):
            mx=max(v);return {j+1 for j,x in enumerate(v) if x >= .95*mx-1e-10}
        base=shortlist(full)
        mchanged=0
        for s in range(n-2):
            omit=values[s:s+3]
            retain=[full[j]-sum(v[j] for v in omit) for j in range(14)]
            result=shortlist(retain)
            added=sorted(result-base)
            removed=sorted(base-result)
            delta=len(added)+len(removed)
            changed=int(delta>0)
            count["all_windows"]+=1
            count["changed_windows"]+=changed
            count["added_memberships"]+=len(added)
            count["removed_memberships"]+=len(removed)
            count["changed_1_member"]+=int(delta==1)
            count["changed_2_members"]+=int(delta==2)
            count["changed_3plus_members"]+=int(delta>=3)
            count["only_added"]+=int(changed and not removed)
            count["only_removed"]+=int(changed and not added)
            count["both_added_removed"]+=int(bool(added and removed))
            count["base_size_sum_changed"]+=len(base) if changed else 0
            count["retained_size_sum_changed"]+=len(result) if changed else 0
            count["symdiff_sum"]+=delta
            mchanged+=changed
            if changed and len(samples)<10:
                samples.append({"month":month,"start_day":s+1,"full_size":len(base),"retained_size":len(result),"added":added,"removed":removed})
            if month=="2016-05" and s+1 in (1,18):
                led.append({"month":month,"start_day":s+1,"before":sorted(base),"after":sorted(result),"added":added,"removed":removed})
        months_mixed+=int(0<mchanged<n-2)
        months_with_flip+=int(mchanged>0)
    assert count["all_windows"]==2237,count
    assert count["changed_windows"]==430,count
    assert months_mixed==43,months_mixed
    assert months_with_flip==45,months_with_flip
    assert len(led)==2 and led[0]["start_day"]==1 and led[1]["start_day"]==18 and led[0]["added"]==[] and led[1]["added"]==[8],led
    result={"source": "MORE-EU/OpenData original fourteen-array archive",
        "source_blob_sha1":EXPECTED_BLOB,"admitted_months":len(months),
        "scope":"one plant, overlapping three-day artificial deletions, no operational utility",
        "q":.05,"gap_days":3,"counts":dict(count),
        "mixed_months":months_mixed,"fragile_months":months_with_flip,
        "example":led,"first_changed_examples":samples,
        "original_telemetry_redistributed":False}
    Path(out).mkdir(parents=True,exist_ok=True)
    (Path(out)/"MEMBERSHIP_CHANGE_MAGNITUDE_DERIVED_ONLY.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    print("R55_EP4_MAGNITUDE_SOURCE_VERIFIED_PASS",json.dumps(result,sort_keys=True),flush=True)
if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--source",required=True);ap.add_argument("--out",default="R55_EP4_DERIVED_ONLY")
    a=ap.parse_args();run(a.source,a.out)
