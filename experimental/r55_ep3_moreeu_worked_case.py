#!/usr/bin/env python3
"""R55-EP3 editorial evidence: one source-verified MORE-EU equal-gap worked case.

Reads the pinned original source without republishing it. Outputs only derived
candidate memberships for a pre-existing R42 sample month. No new estimand.
"""
import csv, hashlib, json, io, calendar
from pathlib import Path
from collections import Counter, defaultdict

SOURCE_BLOB = "5611277efdd581bb839ec380239846a43ebe0ba7"
MONTH = "2016-05"
Q = 0.05
L = 3

def run(path):
    raw = Path(path).read_bytes()
    got = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    assert got == SOURCE_BLOB, ("UNPINNED_SOURCE", got)
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    header = next(reader)
    assert header[0] == "Timestamp" and len(header) == 15, header
    candidates = header[1:]
    days = calendar.monthrange(2016, 5)[1]
    sums = {d: [0.] * 14 for d in range(1, days + 1)}
    slots = defaultdict(set)
    counts = Counter()
    total_rows = 0
    for cells in reader:
        total_rows += 1
        ds, clock = cells[0].split()
        dd, mm, yy = [int(x) for x in ds.split("/")]
        if (2000 + yy, mm) != (2016, 5):
            continue
        assert len(cells) == 15 and 1 <= dd <= days
        assert clock not in slots[dd], ("DUPLICATE_CLOCK", dd, clock)
        slots[dd].add(clock)
        counts[dd] += 1
        for j, item in enumerate(cells[1:]):
            sums[dd][j] += float(item)
    assert total_rows == 280512, total_rows
    assert all(counts[d] == 96 and len(slots[d]) == 96 for d in range(1,days+1))
    full = [sum(sums[d][j] for d in range(1,days+1)) for j in range(14)]
    def selection(arr):
        largest=max(arr)
        assert largest > 0
        return [candidates[j] for j,v in enumerate(arr) if v >= .95*largest-1e-10]
    base=selection(full)
    scenarios=[]
    for start in range(1,days-L+2):
        remain=[full[j]-sum(sums[d][j] for d in range(start,start+L)) for j in range(14)]
        chosen=selection(remain)
        scenarios.append({"start_day":start,
                          "deleted_days":f"2016-05-{start:02d} to 2016-05-{start+L-1:02d}",
                          "same_missing_fraction":f"{L}/{days}",
                          "retained":chosen,
                          "changed":set(chosen)!=set(base),
                          "added":sorted(set(chosen)-set(base)),
                          "removed":sorted(set(base)-set(chosen))})
    assert len(scenarios)==29
    assert sum(s["changed"] for s in scenarios)==2
    assert not scenarios[0]["changed"]
    assert scenarios[17]["changed"]
    result={"source":"MORE-EU/OpenData original Array Power.csv",
            "source_git_blob":SOURCE_BLOB,
            "month":MONTH,"q":Q,"deleted_days":L,
            "candidate_names":candidates,
            "full_shortlist":base,
            "total_three_day_positions":len(scenarios),
            "changed_positions":sum(s["changed"] for s in scenarios),
            "worked_cases":[scenarios[0],scenarios[17]],
            "scope":"source-verified retrospective comparisons; not field outages",
            "original_rows_redistributed":False}
    target=Path("R55_EP3_DERIVED_CASE")
    target.mkdir(parents=True,exist_ok=True)
    (target/"MORE_EU_2016_MAY_EQUAL_GAP.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("R55_EP3_MORE_EU_WORKED_CASE_PASS",json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--source",required=True)
    run(p.parse_args().source)
