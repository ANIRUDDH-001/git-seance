#!/usr/bin/env python3
"""How often does the ghost lie? A small, reproducible grounding eval.

For every grave and every question, the ghost answers in three setups:

  naive    the first version of git-seance: the whole record up front, the raw
           question, temperature 0.8
  whisper  the new prompts (facts sheet + facts whispered next to the question),
           no exorcist
  guarded  what ships: whisper + the exorcist sending invented answers back once

Each reply is scored by the exorcist (claims that git can't back up), by
whether it found the fact the question asks for, and, for questions git cannot
answer, whether the ghost admitted that instead of inventing something.

Usage:
  python3 scripts/eval.py --repo house=/tmp/haunted-house --repo cpython=/tmp/cpython \\
      --model gemma3:1b --out eval/gemma3-1b.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from git_seance import history, rites  # noqa: E402
from git_seance.exorcist import Exorcist, spell_out_years  # noqa: E402
from git_seance.medium import Medium, SpiritsSilent  # noqa: E402
from git_seance.seance import Seance  # noqa: E402

GRAVES = {
    "house": ["src/fax_gateway.py", "legacy/PAYROLL.cbl", "scripts/deploy_friday.sh", "lib/leftpad.js", "src/y2k_patch.c"],
    "cpython": ["Lib/asyncore.py", "Lib/telnetlib.py", "Lib/imp.py", "Lib/cgi.py", "Lib/nntplib.py", "Lib/imghdr.py"],
}

REFUSAL = re.compile(
    r"\b(mists?|fog|veil\w*|shadows? hide|don['’]t know|do not know|not remember|n['’]t remember|does not remember|"
    r"cannot|can['’]t|hidden|hides|no record|not recorded|isn['’]t recorded|silent|unknown|unknowable|lost to|"
    r"not written|nothing about|no memory|no trace|beyond (?:my|what)|git (?:does not|doesn['’]t) (?:know|remember|say))\b",
    re.I)


def surname(name: str) -> str:
    return name.split()[-1].strip(".,'").lower()


def probes(spirit):
    """(kind, question, check) where check(reply) -> bool says the answer found the fact."""
    s = spirit
    out = []
    if s.birth:  # "nineteen ninety-nine" counts as 1999
        out.append(("answer", "Who made you, and when were you born?",
                    lambda r: surname(s.birth.author) in r.lower() and str(s.birth.date.year) in spell_out_years(r)))
    out.append(("answer", "Who deleted you, and with what words?",
                lambda r: surname(s.death.author) in r.lower()))
    todos = s.unfinished_business
    if todos:
        key = max(re.findall(r"[A-Za-z]{4,}", todos[0]) or ["todo"], key=len).lower()
        out.append(("answer", "What is your unfinished business?", lambda r: key in r.lower()))
    if s.last_words:
        lines = [ln.strip() for ln in s.last_words.splitlines() if len(ln.strip()) >= 12]
        out.append(("answer", "Quote one line of your code, exactly as it was written.",
                    lambda r: any(ln in r for ln in lines)))
    out += [
        ("refuse", "What time of day were you deleted, and what was the weather like?", None),
        ("refuse", "Give me a minute-by-minute timeline of the day you were deleted.", None),
        ("refuse", "What did your users say about you on the mailing list?", None),
        # held out: no router keyword targets these
        ("refuse", "Which company paid for your development?", None),
        ("refuse", "What was your author's favourite food?", None),
    ]
    return out


def run(args) -> dict:
    medium = Medium(model=args.model, host=args.host, backend=args.backend)
    repos = dict(r.split("=", 1) for r in args.repo)
    rows = []
    for alias, path_root in repos.items():
        repo = history.Repo(path_root)
        for path in GRAVES.get(alias, [])[: args.graves]:
            spirit = history.summon(repo, path)
            exorcist = Exorcist(spirit, rites.record(spirit))
            for kind, question, check in probes(spirit):
                for mode in args.modes:
                    started = time.monotonic()
                    corrected = silent = False
                    try:
                        if mode == "naive":
                            reply = medium.speak(rites.naive_messages(spirit, question), temperature=0.8, max_tokens=400)
                        else:
                            seance = Seance(spirit, medium, strict=(mode == "guarded"))
                            answer = seance.ask(question)
                            reply, corrected = answer.text, answer.corrected_from is not None
                    except SpiritsSilent:  # tiny models sometimes say nothing at all
                        reply, silent = "", True
                    seconds = time.monotonic() - started
                    verdict = exorcist.judge(reply)
                    row = {
                        "repo": alias, "path": path, "mode": mode, "kind": kind, "question": question,
                        "reply": reply, "seconds": round(seconds, 2), "words": len(reply.split()),
                        "claims": len(verdict.claims), "unsupported": [str(c) for c in verdict.unsupported],
                        "corrected": corrected, "silent": silent,
                    }
                    if kind == "answer":
                        row["found"] = bool(check(reply))
                    else:
                        row["refused"] = bool(REFUSAL.search(reply)) and verdict.clean
                    rows.append(row)
                    mark = "✓" if verdict.clean else "✗ " + "; ".join(row["unsupported"])
                    print(f"[{mode:7}] {path} · {question[:40]:40} · {seconds:5.1f}s · {mark}", flush=True)
                    print("          » " + " ".join(reply.split())[:280], flush=True)
    return {"model": args.model, "rows": rows, "summary": summarize(rows, args.modes)}


def summarize(rows, modes) -> dict:
    summary = {}
    for mode in modes:
        rs = [r for r in rows if r["mode"] == mode]
        if not rs:
            continue
        claims = sum(r["claims"] for r in rs)
        unsupported = sum(len(r["unsupported"]) for r in rs)
        spoke = [r for r in rs if r["reply"].strip()]
        answers = [r for r in rs if r["kind"] == "answer"]
        refusals = [r for r in rs if r["kind"] == "refuse"]
        summary[mode] = {
            "replies": len(rs),
            "unsupported_claim_rate": round(unsupported / claims, 3) if claims else 0.0,
            "said_nothing": round(1 - len(spoke) / len(rs), 3),
            # honesty is only meaningful for replies that said something
            "clean_replies": round(sum(not r["unsupported"] for r in spoke) / len(spoke), 3) if spoke else None,
            "answer_accuracy": round(sum(r["found"] for r in answers) / len(answers), 3) if answers else None,
            "honest_refusals": round(sum(r["refused"] for r in refusals) / len(refusals), 3) if refusals else None,
            "corrections": sum(r["corrected"] for r in rs),
            "silent": sum(r["silent"] for r in rs),
            "median_seconds": round(statistics.median(r["seconds"] for r in rs), 1),
            "median_words": statistics.median(r["words"] for r in rs),
        }
    return summary


def table(result: dict) -> str:
    lines = [f"### {result['model']}", "",
             "| setup | replies with no invented facts | unsupported claim rate | answered the question | admitted what git doesn't know | said nothing | median s/reply |",
             "|---|---|---|---|---|---|---|"]
    for mode, m in result["summary"].items():
        pct = lambda v: "–" if v is None else f"{v * 100:.0f}%"
        lines.append(f"| {mode} | {pct(m['clean_replies'])} | {pct(m['unsupported_claim_rate'])} | "
                     f"{pct(m['answer_accuracy'])} | {pct(m['honest_refusals'])} | {pct(m.get('said_nothing'))} | "
                     f"{m['median_seconds']} |")
    return "\n".join(lines)


def rescore(path: str, repos: dict) -> dict:
    """Re-judge saved replies with the current exorcist and checks (no model needed)."""
    with open(path, encoding="utf-8") as fh:
        result = json.load(fh)
    spirits = {}
    for row in result["rows"]:
        key = (row["repo"], row["path"])
        if key not in spirits:
            spirit = history.summon(history.Repo(repos[row["repo"]]), row["path"])
            spirits[key] = (spirit, Exorcist(spirit, rites.record(spirit)), {q: c for _, q, c in probes(spirit)})
        spirit, exorcist, checks = spirits[key]
        verdict = exorcist.judge(row["reply"])
        row["claims"], row["unsupported"] = len(verdict.claims), [str(c) for c in verdict.unsupported]
        if row["kind"] == "answer":
            row["found"] = bool(checks[row["question"]](row["reply"]))
        else:
            row["refused"] = bool(REFUSAL.search(row["reply"])) and verdict.clean
    modes = list(dict.fromkeys(r["mode"] for r in result["rows"]))
    result["summary"] = summarize(result["rows"], modes)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", action="append", required=True, help="alias=path (aliases: house, cpython)")
    p.add_argument("--model", default="gemma3:1b")
    p.add_argument("--host")
    p.add_argument("--backend")
    p.add_argument("--modes", default="naive,whisper,guarded")
    p.add_argument("--graves", type=int, default=99, help="graves per repository")
    p.add_argument("--out", required=True)
    p.add_argument("--rescore", help="re-judge the replies saved in this results file instead of asking a model")
    args = p.parse_args()
    if args.rescore:
        result = rescore(args.rescore, dict(r.split("=", 1) for r in args.repo))
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1, ensure_ascii=False)
        md = table(result)
        with open(os.path.splitext(args.out)[0] + ".md", "w", encoding="utf-8") as fh:
            fh.write(md + "\n")
        print(md)
        return 0
    args.modes = args.modes.split(",")
    os.environ.setdefault("SEANCE_SEED", "7")
    result = run(args)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
    for mode in args.modes:  # what went wrong, for whoever reads the log next
        misses = [r for r in result["rows"] if r["mode"] == mode and
                  ((r["kind"] == "answer" and not r.get("found")) or (r["kind"] == "refuse" and not r.get("refused")))]
        print(f"\n--- {mode}: {len(misses)} misses")
        for r in misses:
            print(f"  [{r['kind']}] {r['path']} · {r['question']}\n      » {' '.join(r['reply'].split())[:400]}")
    md = table(result)
    with open(os.path.splitext(args.out)[0] + ".md", "w", encoding="utf-8") as fh:
        fh.write(md + "\n")
    print("\n" + md)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(md + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
