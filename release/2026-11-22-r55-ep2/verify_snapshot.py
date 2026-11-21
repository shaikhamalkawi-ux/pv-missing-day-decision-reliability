#!/usr/bin/env python3
"""Offline integrity verifier for the public R55-EP2 release snapshot.

This verifies bytes and the presence of a source-restriction notice. It does NOT
validate raw-data provenance, scientific numerical outcomes or field performance.
"""
from pathlib import Path
import hashlib
import json
import sys

root=Path(__file__).resolve().parent
records=json.loads((root/'FILE_SHA256.json').read_text())['files']
errors=[]
for rel,want in records.items():
    p=root/rel
    if not p.is_file():
        errors.append(f'MISSING {rel}')
        continue
    got=hashlib.sha256(p.read_bytes()).hexdigest()
    if got!=want:
        errors.append(f'HASH MISMATCH {rel}: {got} != {want}')
for needle in ('restricted','not redistributed','provider'):
    if needle not in (root/'README_RELEASE.md').read_text().lower():
        errors.append(f'Missing rights caveat: {needle}')
if errors:
    print('\n'.join(errors),file=sys.stderr)
    raise SystemExit(1)
print(f'PUBLIC SNAPSHOT INTEGRITY: PASS {len(records)}/{len(records)} files; no raw-data validation claimed')
