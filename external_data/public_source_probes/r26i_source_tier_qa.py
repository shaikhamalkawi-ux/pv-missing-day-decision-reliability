#!/usr/bin/env python3
"""Independent source-based quality-tier audit for R26I, not outcome-selected."""
from pathlib import Path
import csv,json,math,hashlib
P=Path("R26I_HKUST_SourceConditional")
def read(name):
    return list(csv.DictReader((P/name).open(encoding="utf8",newline="")))
metadata=json.loads((P/"RDF_DEVICE_CAPACITY_TRACE.json").read_text())
cohorts=read("CONDITIONAL_GROUP_COHORTS.csv")
surfaces=read("CONDITIONAL_GROUP_SURFACES.csv")
certificate=json.loads((P/"CALCULATION_CERTIFICATE.json").read_text())
tiers=[]
for src in metadata:
    group=src["group"]
    cohort=next(x for x in cohorts if x["group"]==group)
    ratio=src["station_to_dc_ratio"]
    over=int(cohort["power_over_120pct_dc_samples"])
    negative=int(cohort["negative_power_values"])
    if over or negative:
        tier="C_SOURCE_OPERATION_HOLD"
        reason="Unusual source electrical samples; 120% threshold is a diagnostic alarm, not a proof of fault."
    elif ratio is not None and math.isclose(ratio,1.0,abs_tol=1e-12,rel_tol=0):
        tier="A_EXACT_RATING_IDENTITY"
        reason="Published site rating equals sum of the identified DC module STC numbers; not metrology certification."
    else:
        tier="B_DC_STC_TRACEABLE_BUT_STATION_RATING_BASIS_OPEN"
        reason="All device/module STC sourced, but station rating may use different AC/DC semantics."
    tiers.append(dict(group=group,quality_tier=tier,source_months=int(cohort["months"]),
                      inverters=int(cohort["inverters"]),site_to_module_dc_ratio=ratio,
                      negative_source_power_samples=negative,over_120pct_module_stc_samples=over,
                      reason=reason))
with (P/"SOURCE_BASED_TIER_REGISTER.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(tiers[0]));w.writeheader();w.writerows(tiers)
profiles=[]
for t in tiers:
    for q in (0,.025,.05,.075,.10):
        cells=sorted((int(r["L"]),int(r["fragile_count"]),int(r["source_months"]))
                     for r in surfaces if r["group"]==t["group"] and float(r["q"])==q)
        assert len(cells)==7
        counts=[n for L,n,m in cells]
        assert counts==sorted(counts)
        assert all(m==t["source_months"] for L,n,m in cells)
        for L,n,m in cells:
            profiles.append(dict(group=t["group"],tier=t["quality_tier"],q=q,L=L,changed=n,
                                 months=m,descriptive_fraction=n/m))
assert len(profiles)==175
with (P/"TIER_ANNOTATED_SOURCE_SURFACES.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(profiles[0]));w.writeheader();w.writerows(profiles)
lines=[
"# R26I HKUST conditional source-denominator and eligibility audit",
"",
"STATUS: Development only. No change to frozen R25-SE1 / R22 results.",
"",
"Source https://zenodo.org/records/10909062, original archive SHA256 "+certificate["sha256"]+".",
"Author paper https://www.nature.com/articles/s41597-025-04397-y .",
"",
"| Same-roof group | Months | Station-nameplate / module DC STC | >120% module STC samples | Tier | q5, L<=3 |",
"|---|---:|---:|---:|---|---:|"
]
for t in tiers:
    q5=next(x for x in profiles if x["group"]==t["group"] and x["q"]==.05 and x["L"]==3)
    lines.append(f'| {t["group"]} | {t["source_months"]} | {t["site_to_module_dc_ratio"]:.4f} | {t["over_120pct_module_stc_samples"]} | {t["quality_tier"]} | {q5["changed"]}/{q5["months"]} |')
lines += ["",
"Tier A: exact identity of the two source representations, not independent measurement certification.",
"Tier B: all module denominators are traceable but station-rated power may be AC while module STC is DC; do not call discrepancy a source error.",
"Tier C: unusual power values or mapping problems require review; do not infer real inverter failure or measurement fraud.",
"",
"The data were source-time resampled to five-minute intervals by the publisher and missing values were NOT filled. A full-month cohort requires all native 144 samples from 06:00 to 17:55 for every calendar day, finite observed power, and all participating inverters on the same fixed roof.",
"Fixed R22 q=0,2.5,5,7.5,10 percent and contiguous deletion support L=1..7 with at least ten retained days. No imputation. Independently verified 420 month-q-L results and 175 group-q-L cells; L monotonicity passed.",
"Do not pool dependent roof-month observations into an outage probability. The source paper quotes about plus/minus 5 percent accuracy for derived generation power/energy; decision margin q=5 percent is NOT a metrological confidence interval.",
"",
"Admission remains HOLD for R25-SE1. Source-specific development results do not establish equipment superiority, causal climate effects, universal fragility risk, or field outage probabilities.",
"All R26I work was kept on a separate experimental GitHub branch; Qatar and QEERI files were not used."]
(P/"R26I_SOURCE_GATE_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf8")
manifest=[]
for file in sorted(P.iterdir()):
    if file.is_file() and file.name!="R26I_DERIVED_SHA256.txt":
        manifest.append((file.name,hashlib.sha256(file.read_bytes()).hexdigest()))
(P/"R26I_DERIVED_SHA256.txt").write_text("".join(f"{h}  {n}\n" for n,h in manifest))
print("R26I_SOURCE_TIER_REGISTER",json.dumps(tiers),flush=True)
print("R26I_TIER_AUDIT_PASS",len(tiers),"groups",len(profiles),"profile cells",flush=True)
