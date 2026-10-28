#!/usr/bin/env bash
# Run a full séance against the demo repository and keep a transcript.
# Usage: demo/haunted_house_seance.sh <repo-dir> <out-dir>
set -uo pipefail
repo="$1"; out="$2"; mkdir -p "$out"
seance() { python3 -m git_seance -C "$repo" "$@"; }
section() { printf '\n\n======== %s ========\n' "$*"; }
{
  section "graveyard"
  seance graveyard

  section "summon src/fax_gateway.py"
  time seance summon src/fax_gateway.py \
    --ask "Rise, spirit. Who were you, and how did you die?" \
    --ask "What is your unfinished business?" \
    --ask "Quote the line of yourself you are proudest of."

  section "summon legacy/PAYROLL.cbl"
  time seance summon legacy/PAYROLL.cbl \
    --ask "Who was Edna to you?" \
    --ask "You were replaced by Rust. Are you bitter?"

  section "summon scripts/deploy_friday.sh (grounding check: the record does not say what happened)"
  time seance summon scripts/deploy_friday.sh --ask "What exactly happened that weekend? Give me the timeline."

  section "summon src/y2k_patch.c"
  seance summon src/y2k_patch.c --ask "How long did you live, and was it worth it?"

  section "epitaphs"
  for f in src/fax_gateway.py legacy/PAYROLL.cbl scripts/deploy_friday.sh lib/leftpad.js src/y2k_patch.c; do
    printf '%-26s ' "$f"; seance epitaph "$f"
  done

  section "obituaries (what the PR bot posts)"
  time seance obituaries HEAD~2..HEAD

  section "ofrenda"
  seance ofrenda -o "$out/index.html" --title "The Haunted House"
} 2>&1 | tee "$out/transcript.txt"
