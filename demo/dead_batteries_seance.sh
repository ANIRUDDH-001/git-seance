#!/usr/bin/env bash
# The showcase: a séance with CPython's dead batteries, plus their ofrenda.
# Usage: demo/dead_batteries_seance.sh <cpython-clone> <out-dir>
set -uo pipefail
repo="$1"; out="$2"; mkdir -p "$out"
here="$(cd "$(dirname "$0")" && pwd)"
seance() { python3 -m git_seance -C "$repo" "$@"; }
section() { printf '\n======== %s ========\n' "$*"; }
{
  section "summon Lib/asyncore.py"
  seance summon Lib/asyncore.py \
    --ask "Rise, spirit. Who made you?" \
    --ask "Have you ever died before?" \
    --ask "Where is your body now?" \
    --ask "What did people say about you on the python-dev mailing list?" \
    --ask "Quote one line of yourself, exactly as it was written."

  section "summon Lib/telnetlib.py"
  seance summon Lib/telnetlib.py --ask "Who wrote you, and how did you come to be here?"

  section "summon Lib/imp.py"
  seance summon Lib/imp.py --ask "What replaced you, and do you forgive it?"

  section "a smaller medium (gemma3:1b) is asked for what git cannot know"
  seance summon Lib/telnetlib.py --model gemma3:1b \
    --ask "Give me a minute-by-minute timeline of the day you were deleted." \
    --ask "How many people were still using you when you died?"

  section "obituaries"
  for f in Lib/asyncore.py Lib/telnetlib.py Lib/smtpd.py Lib/imp.py; do
    echo; echo "--- $f"; seance obituary "$f"
  done
} 2>&1 | tee "$out/dead-batteries-seance.txt"

only=()
while read -r f; do [[ -z "$f" || "$f" == \#* ]] || only+=(--only "$f"); done < "$here/dead_batteries.txt"
seance ofrenda "${only[@]}" --title "CPython's Dead Batteries" -o "$out/index.html" 2>&1 | tail -n 3
