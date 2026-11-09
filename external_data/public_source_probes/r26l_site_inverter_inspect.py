#!/usr/bin/env python3
"""R26L pre-admission inventory: source-level station vs inverter measurement records.

No numerical score, no q x L results. Original Zenodo 10909062 bytes must match.
"""
import hashlib,zipfile,csv,io,json,collections
from pathlib import Path
root=Path("R26L_SourceRecordInspection");root.mkdir(exist_ok=True)
p=Path("source/dataset_original_Zenodo10909062.zip")
sha=hashlib.sha256()
with p.open("rb") as f:
    for b in iter(lambda:f.read(2*1024*1024),b''):sha.update(b)
EXPECTED="610500cfda8309bcba85c4562a1406592882094638132c7ee478cd53e37e96ec"
assert sha.hexdigest()==EXPECTED
files=[]
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    for info in z.infolist():
        if info.is_dir() or not info.filename.lower().endswith('.csv'):continue
        # inspect site data paths for candidate groups and overall site data directory
        if any(t in info.filename.lower() for t in ["library","sports hall","wong check","zone a2","zone d","site level","station level"]):
            with z.open(info) as fh:
                rd=csv.reader(io.TextIOWrapper(fh,encoding="utf-8-sig",errors="replace",newline=""))
                h=next(rd,[])
                sample=[next(rd,[]) for _ in range(3)]
            files.append(dict(path=info.filename,size=info.file_size,header=h,sample=sample))
        print("SRC_CSV_PATH",info.filename, info.file_size,flush=True)
(root/"CROSS_CHANNEL_FILE_PREVIEW.json").write_text(json.dumps(files,ensure_ascii=False,indent=2))
print("MEASUREMENT_CHANNEL_CANDIDATES",json.dumps(files,ensure_ascii=False),flush=True)
