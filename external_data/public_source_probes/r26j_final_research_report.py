#!/usr/bin/env python3
"""Finalize R26J research-only source gate with reproducible certificates and cautious interpretation."""
from pathlib import Path
import csv,json,hashlib,zipfile,os
ROOT=Path("R26J_FinalResearchGate");ROOT.mkdir(exist_ok=True)
LP=Path("calibration");INDEP=Path("verification");SOURCE=Path("prior")
def read(name,folder):
    with (folder/name).open("r",newline="",encoding="utf8") as f:
        return list(csv.DictReader(f))
q=read("SOURCE_GROUP_CALIBRATION_SENSITIVITY.csv",LP)
monthly=read("PER_MONTH_CALIBRATION_AND_DELETION_GATES.csv",LP)
check=read("INDEPENDENT_MATH_CROSSCHECK.csv",INDEP)
rawcert=json.loads((LP/"R26J_CALIBRATION_GAP_CERTIFICATE.json").read_text())
indcert=json.loads((INDEP/"INDEPENDENT_R26J_REPRODUCIBILITY.json").read_text())
assert len(q)==15 and len(monthly)==12 and len(check)==12
assert indcert["results"]=="PASS"
assert all(x["status"]=="PASS" for x in check)
assert indcert["independent_checks"]==12
assert indcert["two_inverter_exact_ratio_count"]==8
assert indcert["three_inverter_source_witness_direct_checks"]==4
assert rawcert["no_qatar_data"] and rawcert["original_R22_R25_locked_unchanged"]
assert all(float(x["q"])==.05 for x in q)
# Each group has the same numerator at L<=1,3,7 in bounded independent calibration.
groups=sorted(set(x["group"] for x in q))
assert len(groups)==5
cols=[]
for g in groups:
    row=next(x for x in q if x["group"]==g and int(x["L"])==3)
    cols.append((g,row))
assert sum(int(x["point_fragile"]) for _,x in cols)==1
assert sum(int(x["exists_fixed_independent_calibration_flip"]) for _,x in cols)==9
assert sum(int(x["baseline_unidentified"]) for _,x in cols)==9
try: 
    assert len(read("DAILY_OBSERVED_INVERTER_SAMPLE_SUMS.csv",SOURCE))>400
except Exception as ex:
    raise RuntimeError("Missing prior source-gated daily data; cannot make reproducibility archive") from ex

intro=[
"# R26J — Distinguishing missing-day decision stability from instrument-calibration identifiability",
"",
"**Scientific research gate — 8 November 2026. DO NOT replace the locked R25-SE1 journal manuscript.**",
"",
"## Audit design and source trace",
"",
"Original measured-energy source: Hong Kong University of Science and Technology, 60 rooftop PV station data, original Zenodo record [10909062](https://zenodo.org/records/10909062). Frozen original publisher ZIP SHA256: ",
"610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec.",
"",
"Data descriptor: Lin et al. (2025), [Scientific Data 12:63, DOI 10.1038/s41597-025-04397-y](https://doi.org/10.1038/s41597-025-04397-y). The source reports ±2.5% accuracy for directly measured electrical variables and ±5% for calculated generation power and energy.",
"",
"To **stress** relative calibration sensitivity, introduce one multiplicative gain factor eta_j per inverter, held constant over the whole source month and over each identical observed-month deletion counterfactual:",
"",
"    Observed period yield under analytic gain eta:  Y_j(D;eta) = eta_j Y_j(D)",
"    0.95 <= eta_j <= 1.05; gains may differ between inverters in this *assumed* envelope.",
"",
"The original frozen R22 q=5% shortlist and contiguous whole-day gap length L=1..7, minimum ten retained days, no imputation, remain unchanged. For each month, a gap is *possible under calibration* if **there exists the same fixed eta vector for the reference and the deleted-day subset** that changes the shortlist. The instrument factors are NOT random draws, and the calculation is not a confidence interval, failure probability, or provider-validated dependence model.",
"",
"Point-only missing-day fragility is a special case eta_j=1 for all j. If all inverters share one common positive factor eta_j=c, it cancels in the relative shortlist inequality, so the point-only fragility result is exactly invariant. Thus the new stress examines possible *relative* calibration differences, not common gain.",
"",
"## Source-conditional result at q=5%, deletion no longer than 3 days",
"",
"| One-roof inverter group | Source grade | Month count | Original recorded-value fragility | Possible with independent fixed gains ±5% | Full-month baseline shortlist unidentified under gains |",
"|---|---|---:|---:|---:|---:|"
]
for group,row in cols:
    intro.append(f'| {group} | {row["tier"]} | {row["months"]} | {row["point_fragile"]}/{row["months"]} | {row["exists_fixed_independent_calibration_flip"]}/{row["months"]} | {row["baseline_unidentified"]}/{row["months"]} |')
intro += [
"",
"**Interpretation:** In the Library cohort (three months, one roof), all three recorded-data shortlists survive seven-day deletions at q=5%, yet each has a one-day omission capable of changing the shortlist under *some* fixed inverter-specific gains in the assumed ±5% box. This does not mean any actual logger is miscalibrated, does not assign a likelihood to the witness, and does not warrant treating q=5% as a measurement-error or certainty margin.",
"",
"Do **not** pool rows into a single PV outage probability. Device identities, months, installation/maintenance histories, and source geography are shared. The numerical gate deliberately retains source grade C (Zone D) for methodological transparency but it remains HOLD for engineering interpretation because of abnormal reported power samples.",
"",
"## Check structure",
"",
"The source-informed first computation enumerates all contiguous deletion locations and lengths. For each device j, the membership condition under the *same eta* is a family of linear inequalities eta_j*Y_j >= (1-q)*eta_k*Y_k for every competing k. A change of membership is a disjunction of one inclusion-system and one strict exclusion inequality. Each feasible direction is tested with bounded linear programming, with a positive normalized exclusion slack. Directly recomputed full/gap shortlists validate every claimed witness.",
"",
"An independent implementation without the linear-programming library checks all ratio partitions for two-inverter groups, using exact q-thresholds at 1-q and 1/(1-q), and recomputes the recorded optimizer factors and resulting shortlist for the three-inverter groups. All 12 source-month cases pass, and the point-only R26I q=5% L=1..7 results are reproduced exactly.",
"",
"### Independent verification certificate",
"",
f'- Independent source-month checks: {indcert["independent_checks"]}/12 PASS.',
f'- Exact two-inverter relative-gain ratio verifications: {indcert["two_inverter_exact_ratio_count"]}/8 PASS.',
f'- Direct three-inverter source-witness recomputations: {indcert["three_inverter_source_witness_direct_checks"]}/4 PASS.',
"- Source-specific q-L month-level point rows from locked R26I: exact match for all 12 × 7 q=5% cells.",
"- Original source ZIP SHA256 and R26I daily-data inputs are retained with their source registry. No Qatar/QEERI data used.",
"",
"## Claim boundaries and research disposition",
"",
"1. **No generic novelty claim:** this is an empirical evidence gate using standard linear feasibility, not a new uncertainty theorem.",
"2. The ±5% interval is an explicitly bounded and independent *analytical* stress; it is not a claim that inverter calibrations are independent, stable over the month, or distributed uniformly within the box.",
"3. Passing a no-deletion measurement set-identifiability check is different from passing a missing-day resilience check, and both differ from engineering metrology certification. The two axes should remain distinct.",
"4. The official R25-SE1 manuscript should not include these uncalibrated findings as an admitted fourth dataset. A defensible supplementary comparison could be considered only after independent source- and instrumentation-validity review.",
"5. Future quantitative measurement claims would require actual cross-inverter calibration checks, instrument tolerance covariance, and site configuration/operational evidence. Do not invent these from a descriptive dataset.",
"",
"## Reproduction",
"",
"R26J research-only GitHub branch: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/tree/r26j-hkust-calibration-gap-audit .",
"Primary bounded-LP run: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42508843473 .",
"Independent exact two-device / explicit-witness readback: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42509160909 .",
"",
"Run the primary script from the research branch with its pinned scipy version on the attached R26I derived daily-source archive. Re-execute the independent verifier using that archive and primary output. Archive contents are keyed to source dates, same-roof names, and the publisher's frozen original hash. No contributor field raw was redistributed in the GitHub code branch.",
"",
"**Project version lock:** R25-SE1 remains the latest journal-facing author-review version; R26I and R26J are private/experimental scientific admission gates, not manuscript revisions."
]
report="\n".join(intro)+"\n"
(ROOT/"R26J_FOCUSED_SCIENTIFIC_AUDIT.md").write_text(report,encoding="utf8")
(ROOT/"R26J_PRIMARY_CERTIFICATE.json").write_text(json.dumps(rawcert,indent=2))
(ROOT/"R26J_INDEPENDENT_CERTIFICATE.json").write_text(json.dumps(indcert,indent=2))
with (ROOT/"R26J_SOURCE_MONTH_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(monthly[0]));w.writeheader();w.writerows(monthly)
with (ROOT/"R26J_GROUP_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(q[0]));w.writeheader();w.writerows(q)
readme="R26J standalone derived-evidence package. Version: research-only, not R25 science. Source DOI 10.1038/s41597-025-04397-y; source ZIP Zenodo 10909062. See R26J_FOCUSED_SCIENTIFIC_AUDIT.md for claim boundaries, and companion R26I source archive for daily values."
(ROOT/"README.txt").write_text(readme+"\n")
manifest=[]
for f in sorted(ROOT.iterdir()):
    if f.is_file() and f.name!="SHA256SUMS.txt":manifest.append((f.name,hashlib.sha256(f.read_bytes()).hexdigest()))
(ROOT/"SHA256SUMS.txt").write_text("".join(f"{h}  {n}\n" for n,h in manifest))
print("R26J_FINAL_REVIEW_GATE_PASS",json.dumps({"files":len(manifest)+1,"months":len(monthly),
      "groups":len(cols),"independent_checked":indcert["independent_checks"],
      "point_fragile_q5L3_sum_not_pooling":sum(int(x["point_fragile"]) for _,x in cols),
      "exists_calibration_q5L3_sum_not_pooling":sum(int(x["exists_fixed_independent_calibration_flip"]) for _,x in cols),
      "no_qatar":True,"R25_locked":True}),flush=True)
