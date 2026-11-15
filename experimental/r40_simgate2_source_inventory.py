#!/usr/bin/env python3
"""R40 SIM-GATE2 source inventory only; requires byte-locked HKUST archive.
No imputation, no scientific conclusions, no raw data redistribution.
"""
import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path("R40_SIM_GATE2_SourceInventory")
ROOT.mkdir(exist_ok=True)
SOURCE = Path("source/dataset_original_Zenodo10909062.zip")
EXPECTED = "610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"

def hashes(path):
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8*1024*1024), b""):
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), md5.hexdigest()

if not SOURCE.is_file():
    raise FileNotFoundError(f"Missing source artifact: {SOURCE}")
sha, md5 = hashes(SOURCE)
assert sha == EXPECTED, f"SHA mismatch {sha}"
selected = []
metadata = []
context = []
with zipfile.ZipFile(SOURCE) as archive:
    for member in archive.infolist():
        nm = member.filename
        if member.is_dir():
            continue
        low = nm.lower()
        if (nm.endswith(".ttl") or "library" in low or "irradiance" in low
           or "temperature" in low or "wind" in low or "humidity" in low):
            entry = {"name": nm, "size": member.file_size,
                     "compressed_size": member.compress_size,
                     "source_crc32": "%08x" % member.CRC}
            if low.endswith(".csv"):
                with archive.open(member) as src:
                    stream = io.TextIOWrapper(src, encoding="utf-8-sig", errors="replace", newline="")
                    reader = csv.reader(stream)
                    entry["header"] = next(reader, [])
                    entry["sample_rows"] = [next(reader, []) for _ in range(2)]
            selected.append(entry)
        if low.endswith(".ttl"):
            with archive.open(member) as fh:
                txt = fh.read().decode("utf-8-sig", "replace")
            metadata.append({"name": nm, "length": len(txt)})
            for term in ("library", "se50k", "solaredge", "tilt", "azimuth",
                         "orientation", "angle", "inverter", "irradiance"):
                all_matches = list(re.finditer(re.escape(term), txt, flags=re.I))
                for match in all_matches[:5]:
                    start = max(0, match.start() - 160)
                    end = min(len(txt), match.end() + 220)
                    context.append({"file": nm, "term": term,
                                    "hit_count": len(all_matches),
                                    "context": txt[start:end]})
    totals = {"members": len(archive.infolist()),
              "selected_files": len(selected),
              "ttl_files": len(metadata)}
    # Restrict CRC to source bytes actually used; full CRC is done in the
    # externally archived provenance and not claimed by this run.
    certificate = {"status": "SOURCE_SHA_PASS_SCHEMA_INVENTORY_ONLY",
                   "source_size_bytes": SOURCE.stat().st_size,
                   "sha256": sha, "md5": md5,
                   "archive": str(SOURCE), "counts": totals,
                   "scientific_admission": "HOLD",
                   "pvlib_simulation_executed": False}
(ROOT/"SOURCE_INVENTORY.json").write_text(json.dumps(
    {"certificate": certificate, "members": selected, "ttl": metadata,
     "ttl_context": context}, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT/"SOURCE_INTEGRITY.json").write_text(
    json.dumps(certificate, indent=2), encoding="utf-8")
print("R40_SIM_GATE2_SOURCE_SHA_PASS", sha, "MD5", md5, "selected", len(selected))
for item in selected:
    print("SCHEMA", item["name"], "bytes", item["size"],
          "header", json.dumps(item.get("header", [])))
print("OUTPUT", ROOT/"SOURCE_INVENTORY.json")

for record in context:
    if record["term"] in ("library","se50k","solaredge","tilt","azimuth","orientation","angle"):
        print("TTL_CONTEXT", json.dumps(record, ensure_ascii=False))
