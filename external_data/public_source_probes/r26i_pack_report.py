#!/usr/bin/env python3
"""Assemble immutable R26I source-evidence package from separately finished CI outputs.
No raw HKUST archive, no Qatar inputs, no paper R25 modifications.
"""
from pathlib import Path
import json,hashlib,shutil,zipfile,os
root=Path("R26I_PUBLISHABLE_SOURCE_AUDIT_PACKAGE")
root.mkdir(exist_ok=True)
groups={
  "01_Primary_R26I_Calculation_and_IndependentReplay":Path("evidence"),
  "02_Independent_Weather_Aligned_SourceGate":Path("weather"),
  "03_Integrated_Admission_Policy_Sensitivity":Path("integrated"),
}
for dest,source in groups.items():
    assert source.is_dir(),source
    assert list(source.iterdir()),source
    target=root/dest
    target.mkdir(exist_ok=True)
    for x in source.iterdir():
        if x.is_file(): shutil.copy2(x,target/x.name)
scripts=[
"r26i_hkust_group_extension.py","r26i_independent_qL_verifier.py",
"r26i_source_tier_qa.py","r26i_hkust_weather_alignment.py",
"r26i_weather_cohort_sensitivity.py"]
src_dir=Path("external_data/public_source_probes")
dst=root/"04_Reproducibility_Scripts"
dst.mkdir(exist_ok=True)
for name in scripts:
    src=src_dir/name
    assert src.is_file(),src
    shutil.copy2(src,dst/name)
shutil.copy2(src_dir/"R26I_FINAL_AUDIT.md",root/"R26I_FINAL_AUDIT.md")
readme="""# 106Amen R26I development evidence
Official manuscript baseline: R25-SE1, R22 scientific values locked and unchanged.
Source: HKUST Zenodo 10909062 (April 2024 source version).
Original archived source SHA256:
610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec
Original third-party raw archive is NOT repackaged here; obtain from:
https://zenodo.org/records/10909062
This package contains source-identifiable, derived evidence and independent
replay scripts only. Weather irradiance = shared campus measurement, NOT
rooftop plane-of-array. No measured uncertainty propagation, causal inference,
technology-family superiority, or independent population risk is admitted.
Qatar / QEERI files are entirely absent.
To reproduce, use original publisher file in source/ and earlier frozen
144-slot source gate in gate/, then run scripts in dependency order.
Source-run record: https://github.com/shaikhamalkawi-ux/pv-missing-day-decision-reliability/actions/runs/42503693629
R26I review report: 04_Reproducibility_Scripts/../R26I_FINAL_AUDIT.md.
"""
(root/"README_FIRST.md").write_text(readme,encoding="utf8")
allfiles=sorted(x for x in root.rglob("*") if x.is_file())
lines=[f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(root).as_posix()}" for f in allfiles]
(root/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="utf8")
zipname="R26I_HKUST_Independent_SourceAndWeatherAudit_Package.zip"
with zipfile.ZipFile(zipname,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(x for x in root.rglob("*") if x.is_file()):
        z.write(f,arcname=f.relative_to(root))
with zipfile.ZipFile(zipname) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(allfiles)+1
h=hashlib.sha256(Path(zipname).read_bytes()).hexdigest()
print(json.dumps(dict(status="PASS",zip=zipname,bytes=os.path.getsize(zipname),
                      sha256=h,internal_files=len(allfiles)+1,
                      source_ref="Zenodo 10909062",r25_science_unchanged=True,
                      qatar_data_used=False),indent=2),flush=True)
