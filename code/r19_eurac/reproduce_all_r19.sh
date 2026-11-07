#!/usr/bin/env bash
set -euo pipefail
RAR=${1:?EURAC.rar path}; WORK=${2:?work dir}; OUT=${3:?output dir}
mkdir -p "$WORK" "$OUT"
python "$(dirname "$0")/00_extract_eurac_libarchive.py" "$RAR" "$WORK"
python "$(dirname "$0")/01_r19_primary.py" "$WORK" "$OUT" "$RAR"
python "$(dirname "$0")/02_r19_independent_verify.py" "$WORK" "$OUT" "$OUT"
