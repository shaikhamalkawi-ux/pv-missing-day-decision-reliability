#!/usr/bin/env python3
"""R30 manuscript source/locked results/source-conditioned gap audit gates."""
import json,re
from pathlib import Path
R=Path(__file__).resolve().parent.parent
main=(R/"paper/main.tex").read_text();sup=(R/"paper/supplement.tex").read_text()
base=json.loads((R/"results/R22_RESULT_CERTIFICATE.json").read_text())
graph=json.loads((R/"results/R29_GRAPH_CERTIFICATE.json").read_text())
same=json.loads((R/"results/R30_HKUST_SAME_RATE_GAP_POSITION_CERTIFICATE.json").read_text())
assert base["datasets"]=={"PROPRE.MA":25,"EURAC":7,"MORE-EU":79}
assert base["r21_q5_gap_le3_crosscheck_all_pass"]
assert graph["status"]=="PASS_INDEPENDENT_GRAPH_CERTIFICATE"
assert graph["graphs"]==4680 and graph["original_strict_relaxed_LP_calls"]==9360
assert graph["max_abs_epsilon_graph_minus_LP"]<1e-11
assert same["status"]=="PASS" and same["window_count"]==25
assert same["changed_window_count"]==3 and same["unchanged_window_count"]==22
assert same["deleted_days"]==7 and same["q"]==.1 and not same["qatar_qeeri"]
assert [x["first_day"] for x in same["changed_windows"]]==["2023-07-05","2023-07-07","2023-07-08"]
for term in ("3 of 25","22 placements","same 7 of 31","counterfactual"):
    assert term in main,term
for term in ("Table S8.","22/25","25-window","7/31"):
    assert term in sup,term
assert "not a dataset of observed field outages" in main
intro=main.split("\\begin{thebibliography}{99}")[0]
order=[]
for block in re.findall(r"\\cite(?:\[[^\]]+\])?\{([^}]+)\}",intro):
    for k in block.split(","):
        k=k.strip()
        if k not in order:order.append(k)
bib=re.findall(r"\\bibitem\{([^}]+)\}",main)
assert len(order)==len(bib)==15 and order==bib,(order,bib)
for j in range(1,9):assert "\\caption*{Table S"+str(j)+"." in sup
assert "Qatar" not in main and "QEERI" not in main
abstract=main.split("\\begin{abstract}")[1].split("\\end{abstract}")[0]
assert len(abstract.split())<=250
report={"status":"PASS","first_citation_order":bib,"reference_count":15,
        "abstract_words":len(abstract.split()),"R22_source_counts_locked":base["datasets"],
        "LP_calls":9360,"graph_cases":4680,"same_rate_windows":25,
        "same_rate_change":3,"same_rate_unchanged":22,"supp_tables":8,
        "counterfactual_gap_disclosure":True,"Qatar_QEERI":False}
(R/"R30_SCIENCE_AND_EDITORIAL_QA.json").write_text(json.dumps(report,indent=2)+"\n")
print("R30_SCIENCE_EDITORIAL_PASS",json.dumps({k:v for k,v in report.items() if k!="first_citation_order"}))
