#!/usr/bin/env python3
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_SUFFIX = {'.aux', '.log', '.fls', '.fdb_latexmk', '.out', '.toc'}
lines = []
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.name == 'SHA256SUMS.txt' or p.suffix in EXCLUDE_SUFFIX:
        continue
    if '.git' in p.parts:
        continue
    rel = p.relative_to(ROOT).as_posix()
    lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
(ROOT / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'wrote {len(lines)} checksums')
