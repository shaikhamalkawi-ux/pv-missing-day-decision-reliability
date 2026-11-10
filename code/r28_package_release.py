#!/usr/bin/env python3
"""Assemble the source-linked R28 author-review bundle after CI science verification."""
import hashlib, json, re, subprocess, zipfile
from pathlib import Path
from docx import Document

R=Path.cwd(); O=R/"R28_DELIVERY"; O.mkdir(exist_ok=True)
MAIN="106Amen_R28_SolarEnergy_Main_AUTHOR_REVIEW.pdf"
SUPP="106Amen_R28_SolarEnergy_Supplement.pdf"
BOTH="106Amen_R28_SolarEnergy_Main_PLUS_Supplement.pdf"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pages(p):
    assert Path(p).is_file() and Path(p).stat().st_size>10000
    fonts=subprocess.check_output(["pdffonts",p],text=True)
    assert "Type 3" not in fonts and "Type3" not in fonts
    info=subprocess.check_output(["pdfinfo",p],text=True)
    return int(re.search(r"^Pages:\s*(\d+)",info,re.M).group(1))
def all_files(d):
    return sorted(str(p.relative_to(R)) for p in (R/d).rglob("*") if p.is_file())
def archive(path,entries,extras={}):
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for name in sorted(set(entries)):
            assert (R/name).is_file(),name
            z.write(R/name,name)
        for name,content in sorted(extras.items()): z.writestr(name,content)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))
qa=json.loads(Path("R28_SOURCE_TO_MANUSCRIPT_QA.json").read_text())
assert qa["status"]=="PASS" and qa["R28_analytic_LPs"]==9360
assert qa["R28_source_months"]==12 and qa["HKUST_Library_days"]==93
assert qa["R22_frozen_count_check"] and not qa["Qatar_included"]
mp,sp,bp=pages(MAIN),pages(SUPP),pages(BOTH)
assert mp>=17 and sp>=7 and bp==mp+sp
for log in ("build/main.log","build/supplement.log"):
    s=Path(log).read_text(errors="replace")
    assert "Overfull \\hbox" not in s,log
    assert "Undefined control sequence" not in s,log
text=subprocess.check_output(["pdftotext",MAIN,"-"],text=True)
assert all(x in text for x in ("0.468733","2.025261","1.826766","3/25","1/7","45/79"))
highlights=[x.strip().lstrip("-").strip() for x in Path("paper/R28_SolarEnergy_Highlights.txt").read_text().splitlines() if x.strip()]
assert len(highlights)==5 and all(0<len(x)<=85 for x in highlights)
doc=Document();doc.add_heading("Highlights",1)
for item in highlights: doc.add_paragraph(item,style="List Bullet")
doc.core_properties.author=""
doc.save(O/"106Amen_R28_Highlights.docx")
(O/"106Amen_R28_Highlights.txt").write_text("\n".join("- "+x for x in highlights)+"\n")
figs=all_files("figures")
assert any("R27_HKUST_LIBRARY_SITE_VS_INVERTER" in p for p in figs)
source=["paper/main.tex","paper/supplement.tex"]+figs
archive(O/"106Amen_R28_Overleaf_Editable_Source.zip",source,
    {"OVERLEAF_README.md":"R28 source: select paper/main.tex for main PDF; paper/supplement.tex for supplement. Compile with pdfLaTeX. Keep figures directory. Author review only.\n"})
dirs=["r28_evidence/R28_Primary","r28_evidence/R28_Independent","r28_evidence/HKUST_R26H","r28_evidence/HKUST_R26L"]
evidence=sum((all_files(p) for p in dirs),[])
repro=all_files("code")+all_files("results")+all_files("metadata")+evidence+source+[
    "requirements.txt","README.md","DATA_AVAILABILITY.md","LICENSE.md",
    "LICENSE_CODE_MIT.txt","R28_SOURCE_TO_MANUSCRIPT_QA.json",
    "R28_SCIENTIFIC_REVISION_REPORT.md","R28_SCIENTIFIC_CHANGELOG_AR.md"]
archive(O/"106Amen_R28_SourceLinked_Reproducibility.zip",repro,
    {"REPRO_README.md":"Derived R28 source-linked evidence and code, including HKUST original Zenodo 10909062 attribution and locked R22 certificates. Whole original HKUST and PROPRE.MA raw source archives are not included. Scientific thresholds are conditional, not measured calibration errors. Run python code/r28_verify_science.py from root. SciPy 1.16.3 used for solver.\n"})
handoff=f"""# Project 106Amen / Solar Energy / R28 handoff
Latest state: R28 author-review scientific candidate, not submitted.
Repository: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability
Research branch: r28-critical-relative-gain-margin.
Immutable R25 commit: 0a3562db8d7812a3f2760d786432752f0a951b8f; do not edit.
Main {mp} pages, supplement {sp} pages, combined {bp} pages.
Original q=5 percent, L<=3: PROPRE.MA 3/25, EURAC 1/7, MORE-EU 45/79.
Retrospective HKUST Library 0/3; 93 complete days; median meter difference
0.427578 percent; p95 0.993528 percent.
Critical hypothetical relative-gain witness bounds: 0.468733 percent (July
2022), 2.025261 percent (May 2023), 1.826766 percent (July 2023).
9360 LP checks, independent 2-device ratios for 8 months, independent
3-device positive-witness replays for 4 months.
No measured instrument-gain errors, probability estimates, or covariance;
no independent impossibility certificate for all three-device no-witness cases.
Other roof groups remain secondary; Zone D on HOLD. Source original
Zenodo 10909062 pinned SHA256 610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec.
No Qatar/QEERI information; do not pool source-specific months.
Do not assert ready to submit without author fields/declarations and portal QA.
"""
(O/"R28_HANDOFF_NEW_CHAT.md").write_text(handoff)
(O/"R28_AUTHOR_SUBMISSION_GATES.md").write_text(
    "# Solar Energy R28: author-controlled hold\n\n"
    "Complete author names/order/affiliations/ORCIDs/correspondence, "
    "CRediT, funding and APC, acknowledgements, competing interests, "
    "generative-AI declaration, anonymization decision, repository "
    "release/archival DOI, and final journal-portal checks. This is NOT a "
    "submitted manuscript or an engineering calibration certificate.\n")
for p in ("R28_SCIENTIFIC_REVISION_REPORT.md","R28_SCIENTIFIC_CHANGELOG_AR.md","R28_SOURCE_TO_MANUSCRIPT_QA.json",MAIN,SUPP,BOTH):
    (O/Path(p).name).write_bytes(Path(p).read_bytes())
for p in ("r28_evidence/R28_Primary/R28_CRITICAL_EPSILON_MONTHS.csv",
          "r28_evidence/R28_Primary/R28_CRITICAL_MARGIN_CERTIFICATE.json",
          "r28_evidence/R28_Independent/R28_INDEPENDENT_VERIFIER_CERTIFICATE.json"):
    (O/Path(p).name).write_bytes(Path(p).read_bytes())
manifest={p.name:{"sha256":sha(p),"bytes":p.stat().st_size}
          for p in sorted(O.iterdir()) if p.is_file()}
(O/"SHA256_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
assert all(sha(O/k)==v["sha256"] for k,v in manifest.items())
report={"status":"AUTHOR_REVIEW_PACKAGE_PASS","main_pages":mp,
        "supplement_pages":sp,"combined_pages":bp,
        "highlights_lengths":[len(x) for x in highlights],
        "figure_count":len(figs),"manifest_files":len(manifest),
        "source_qa":qa,"submission_ready":False}
(O/"R28_DELIVERY_QA.json").write_text(json.dumps(report,indent=2)+"\n")
base=[str(p.relative_to(R)) for p in O.iterdir() if p.is_file()]
archive(O/"106Amen_R28_AuthorReview_COMPLETE.zip",base)
transfer=["R28_HANDOFF_NEW_CHAT.md","R28_AUTHOR_SUBMISSION_GATES.md",
          "R28_DELIVERY_QA.json","R28_SOURCE_TO_MANUSCRIPT_QA.json",
          "R28_SCIENTIFIC_REVISION_REPORT.md","SHA256_MANIFEST.json"]
archive(O/"106Amen_R28_NewChat_Transfer.zip",
        ["R28_DELIVERY/"+p for p in transfer])
print("R28_AUTHOR_PACKAGE_PASS",json.dumps(report),flush=True)
