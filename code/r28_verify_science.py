#!/usr/bin/env python3
"""R28 immutable source-to-manuscript bridge and stringent scientific-claim gate."""
import csv,collections,json,math,re,hashlib,statistics
from pathlib import Path
P=Path("r28_evidence")
MAIN=Path("paper/main.tex").read_text(encoding="utf8")
SUPP=Path("paper/supplement.tex").read_text(encoding="utf8")
def readcsv(folder,file):
    with (P/folder/file).open("r",encoding="utf8",newline="") as f:
        return list(csv.DictReader(f))
data=readcsv("R28_Primary","R28_CRITICAL_EPSILON_MONTHS.csv")
ind=json.loads((P/"R28_Independent"/"R28_INDEPENDENT_VERIFIER_CERTIFICATE.json").read_text())
assert len(data)==12
assert ind["status"]=="PASS_EXPLICIT_AND_TWO_DEVICE_ANALYTICAL"
assert ind["analytic_two_inverter_months"]==8
assert ind["three_inverter_explicit_witness_months"]==4
cert=json.loads((P/"R28_Primary"/"R28_CRITICAL_MARGIN_CERTIFICATE.json").read_text())
assert cert["month_checks"]==12 and cert["witnesses"]==9 and cert["LP_calls"]==9360
assert cert["source_sha256"]=="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
assert cert["q"]==.05 and cert["Lmax"]==3 and cert["preserve_r25"]
assert "\\documentclass[preprint,12pt]{elsarticle}" in MAIN
assert MAIN.count("\\begin{frontmatter}")==1 and MAIN.count("\\end{frontmatter}")==1
assert "\\label{eq:critical_gain}" in MAIN
assert "\\label{tab:hkustcritical}" in MAIN
assert "S4d. Baseline-preserving critical relative-gain radius" in SUPP
assert "Table S7." in SUPP
library=[x for x in data if x["group"]=="Library"]
assert {x["month"] for x in library}=={"2022-07","2023-05","2023-07"}
for r in library:
    a=float(r["relaxation_lower_bound"])*100
    b=float(r["certified_witness_epsilon"])*100
    assert 0<=a<=b
    assert b-a < .000005,(r["month"],a,b)
    for n in (f"{a:.6f}",f"{b:.6f}"):
        assert n in MAIN and n in SUPP,(r["month"],n)
    assert r["witness_gap_length"]=="3"
assert len([x for x in data if x["critical_status"]=="WITNESS_WITHIN_5PCT"])==9
assert len([x for x in data if x["critical_status"]=="NO_POSITIVE_WITNESS_UP_TO_5PCT"])==3
qL=readcsv("HKUST_R26H","R26H_HKUST_LIBRARY_SURFACE.csv")
assert len(qL)==35
assert all(int(r["fragile_month_count"])==(1 if float(r["q"])==.1 and int(r["L"])==7 else 0) for r in qL)
pairs=readcsv("HKUST_R26L","R26L_MATCHED_SOURCE_DAY_AUDIT.csv")
lib=[r for r in pairs if r["group"]=="Library" and r["source_cohort"]=="1"]
assert len(lib)==93 and all(r["crossmeter_admitted"]=="1" for r in lib)
errs=sorted(float(r["pct_abs_diff_station_power_vs_inverters"]) for r in lib)
med=statistics.median(errs)
p=(len(errs)-1)*.95;k=int(p);p95=errs[k]*(1-p%1)+errs[min(k+1,len(errs)-1)]*(p%1)
assert abs(med-.42757788815049586)<1e-8
assert abs(p95-.9935278571786557)<1e-8
assert "0.428" in MAIN and "0.994" in MAIN
R22=json.loads(Path("results/R22_RESULT_CERTIFICATE.json").read_text())
assert R22["datasets"]=={"PROPRE.MA":25,"EURAC":7,"MORE-EU":79}
assert R22["r21_q5_gap_le3_crosscheck_all_pass"] is True
for x in ("3/25","1/7","45/79"):
    assert x in MAIN and x in SUPP
assert MAIN.count("\\bibitem{")==15
keys=set(re.findall(r"\\bibitem\{([^}]+)\}",MAIN))
cited=set()
for group in re.findall(r"\\cite(?:\[[^\]]+\])?\{([^}]+)\}",MAIN):
    cited.update(x.strip() for x in group.split(","))
assert cited==keys,(keys-cited,cited-keys)
abstract=MAIN.split("\\begin{abstract}",1)[1].split("\\end{abstract}",1)[0]
wc=len(abstract.split())
assert wc<=250,("abstract too long",wc)
for text in ("source-month", "gain", "conditional", "retrospective"):
    assert text in MAIN.lower()
# These assertions intentionally distinguish post-freeze HKUST from locked R22.
assert "three originally" in MAIN.lower() or "three original" in MAIN.lower()
assert "retrospective" in MAIN.lower()
assert "Qatar" not in MAIN
report={"status":"PASS","R28_source_months":len(data),"R28_analytic_LPs":cert["LP_calls"],
        "source_gated_positive_witness_months":9,"independent_two_device":8,
        "independent_three_device_positive_witnesses":4,
        "HKUST_qL_cells":len(qL),"HKUST_Library_days":len(lib),
        "library_site_vs_inverter_median_pct":med,"library_p95_pct":p95,
        "abstract_words":wc,"bibliography_keys":len(keys),"cited_keys":len(cited),
        "R22_frozen_count_check":True,
        "not_a_measurement_uncertainty_interval":True,
        "retrospective_fourth_source":True,"Qatar_included":False}
Path("R28_SOURCE_TO_MANUSCRIPT_QA.json").write_text(json.dumps(report,indent=2))
print("R28_SOURCE_TO_MANUSCRIPT_PASS",json.dumps(report),flush=True)
