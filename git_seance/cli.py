"""git seance: talk to the ghosts of your deleted code.

Installed as `git-seance`, so git picks it up as `git seance <rite>`.
(`git seance --help` is turned into `git help seance` by git itself; use -h.)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Optional

from . import __version__, history, rites
from .exorcist import describe
from .history import Repo, SeanceError
from .medium import Medium, SpiritsSilent
from .render import DIM, GHOST, MARIGOLD, RED, Painter, ledger, stones_row, terminal_width, use_color
from .seance import Seance


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # never die on a terminal that can't print "é"
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, OSError):
                pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "rite", None):
        parser.print_help()
        return 0
    paint = Painter(use_color() and not args.no_color)
    err = Painter(use_color(sys.stderr) and not args.no_color)
    try:
        return args.rite(args, paint, err)
    except SeanceError as e:
        print(err("☠  " + str(e), RED), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(err("\n🕯  The candle gutters out. The spirit returns to the dark.", DIM), file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="git seance",
        description="Summon the ghosts of deleted files from your git history, "
        "with an open-weight model running on your own machine.",
    )
    p.add_argument("--version", action="version", version=f"git-seance {__version__}")
    p.add_argument("-C", dest="repo", default=".", help="run as if started in this directory")
    p.add_argument("--no-color", action="store_true", help="disable colors (NO_COLOR also works)")
    sub = p.add_subparsers(title="rites", metavar="<rite>")
    # --no-color may also come after the rite, without clobbering an earlier one
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    def rite(name: str, help_text: str, func) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=help_text, description=help_text, parents=[common])
        sp.set_defaults(rite=func)
        return sp

    def ref_opt(sp):
        sp.add_argument("--ref", default="HEAD", help="look back from this commit (default: HEAD)")

    def medium_opts(sp):
        g = sp.add_argument_group("medium (the model)")
        g.add_argument("--model", help="model name (default: $SEANCE_MODEL, else gemma3:4b for séances, gemma3:1b otherwise)")
        g.add_argument("--host", help="model server URL (default: $SEANCE_HOST, $OLLAMA_HOST or localhost:11434)")
        g.add_argument("--backend", choices=["ollama", "openai"], help="API dialect (default: ollama)")

    g = rite("graveyard", "list every file that died and stayed dead", rite_graveyard)
    g.add_argument("pathspec", nargs="*", help="limit to these paths (git pathspec)")
    ref_opt(g)
    g.add_argument("-n", "--limit", type=_count, default=8, help="tombstones to raise (default: 8)")
    g.add_argument("--all", action="store_true", help="list every grave in the ledger")
    g.add_argument("--include-fragments", action="store_true", help="include changelog fragments (NEWS.d, changelog.d)")

    s = rite("summon", "hold a séance with a deleted file", rite_summon)
    s.add_argument("path", help="path of the deleted file")
    ref_opt(s)
    s.add_argument("-a", "--ask", action="append", help="ask a question and leave (repeatable)")
    s.add_argument("--unguarded", action="store_true", help="don't send the ghost back when it invents facts")
    medium_opts(s)

    r = rite("record", "show exactly what the ghost is told about itself", rite_record)
    r.add_argument("path")
    ref_opt(r)

    e = rite("epitaph", "carve a one-line epitaph", rite_epitaph)
    e.add_argument("path")
    ref_opt(e)
    e.add_argument("--plain", action="store_true", help="no model: carve the words it was born with")
    medium_opts(e)

    o = rite("obituary", "write an obituary for a deleted file", rite_obituary)
    o.add_argument("path")
    ref_opt(o)
    o.add_argument("--plain", action="store_true", help="no model: facts only")
    medium_opts(o)

    ob = rite("obituaries", "obituaries for every file a branch deletes, as markdown (for PR bots)", rite_obituaries)
    ob.add_argument("range", help="BASE..HEAD (or BASE...HEAD)")
    ob.add_argument("--max", type=_count, default=6, help="most obituaries to write (default: 6)")
    ob.add_argument("--format", choices=["markdown", "text"], default="markdown")
    ob.add_argument("--plain", action="store_true", help="no model: facts only")
    medium_opts(ob)

    of = rite("ofrenda", "build a Día de los Muertos ofrenda page for your departed files", rite_ofrenda)
    of.add_argument("pathspec", nargs="*", help="limit to these paths (git pathspec)")
    ref_opt(of)
    of.add_argument("-o", "--output", default="ofrenda.html", help="where to write the page (default: ofrenda.html)")
    of.add_argument("-n", "--limit", type=_count, default=12, help="files to honor (default: 12)")
    of.add_argument("--only", action="append", default=[], help="honor exactly these paths (repeatable)")
    of.add_argument("--title", help="title for the ofrenda (default: repository name)")
    of.add_argument("--plain", action="store_true", help="no model: carve the words each was born with")
    medium_opts(of)

    rs = rite("resurrect", "bring a deleted file back into your working tree", rite_resurrect)
    rs.add_argument("path")
    ref_opt(rs)
    rs.add_argument("--force", action="store_true", help="overwrite whatever lives there now")
    return p


def _count(value: str) -> int:
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError("must be zero or more")
    return n


# The eval (scripts/eval.py) chose these: gemma3:4b keeps its answers and
# refuses what git can't know; gemma3:1b is fast enough for CI, where code
# writes every fact and the model only adds flavor.
SEANCE_DEFAULT = "gemma3:4b"


def _medium(args, err: Painter, default: Optional[str] = None) -> Medium:
    model = args.model or os.environ.get("SEANCE_MODEL") or default
    medium = Medium(model=model, host=args.host, backend=args.backend)
    if not medium.is_local:
        _status(err, f"☁  Note: the medium is not on this machine ({medium.where}). "
                     "Each file's history and contents will be sent there.")
    return medium


def _status(err: Painter, text: str) -> None:
    print(err(text, DIM), file=sys.stderr, flush=True)


# --------------------------------------------------------------------------


def rite_graveyard(args, paint, err) -> int:
    repo = Repo(args.repo)
    graves = history.graveyard(repo, args.ref, args.pathspec, include_fragments=args.include_fragments)
    if repo.shallow_boundary:
        _status(err, "⚠  This is a shallow clone: older graves are out of sight. `git fetch --unshallow` to see them.")
    if not graves:
        print("The graveyard is empty. Nothing has died here... yet.")
        return 0
    shown = graves[: args.limit]
    listed = graves if args.all else graves[: max(args.limit, 25)]
    specs = {g.path: f"{g.death.sha}^:{g.path}" for g in listed}
    counts = repo.blob_line_counts(list(specs.values()))
    counts = {path: counts.get(spec) for path, spec in specs.items()}
    width = terminal_width()
    if shown:
        print()
        print(stones_row(shown, counts, paint, width))
    print(ledger(listed, counts, paint, width))
    hidden = len(graves) - len(listed)
    print()
    if hidden > 0:
        print(paint(f"  …and {hidden} more rest in unmarked graves (use --all).", DIM))
    example = _shell_quote(graves[0].path)
    print(paint(f"  {rites.plural(len(graves), 'soul')} departed. Summon one:  git seance summon {example}", DIM))
    return 0


def _shell_quote(path: str) -> str:
    return path if re.fullmatch(r"[\w./@+-]+", path) else "'" + path.replace("'", "'\\''") + "'"


def rite_record(args, paint, err) -> int:
    spirit = history.summon(Repo(args.repo), args.path, args.ref)
    print(rites.ghost_system(spirit))
    return 0


def rite_summon(args, paint, err) -> int:
    repo = Repo(args.repo)
    spirit = history.summon(repo, args.path, args.ref)
    medium = _medium(args, err, default=SEANCE_DEFAULT)
    seance = Seance(spirit, medium, strict=not args.unguarded)

    def channel(question: str) -> None:
        started = []

        def show(token: str) -> None:
            if not started:  # only once the spirit actually answers
                started.append(True)
                print(paint("👻 " + spirit.name + ": ", MARIGOLD), end="")
                token = token.lstrip()
            print(paint(token, GHOST), end="", flush=True)

        def scolded(verdict) -> None:
            print()
            print(paint(f"   🔮 the exorcist: git does not remember {describe(verdict.unsupported)}. "
                        "The spirit is sent back to answer again.", DIM))
            started.clear()

        reply = seance.ask(question, on_token=show, on_correction=scolded)
        print()
        if not reply.verdict.clean:
            print(paint(f"   🔮 the exorcist still doubts: {describe(reply.verdict.unsupported)}", DIM))
        print()

    gift = f" · born with the words “{rites.one_line(spirit.gift, 70)}”" if spirit.gift else ""
    _status(err, f"🕯  Lighting candles for {spirit.path} ({rites.years(spirit)}){gift}")
    _status(err, f"   medium: {medium.model} via {medium.backend} · the exorcist is listening")
    print()
    if args.ask:
        for q in args.ask:
            print(paint("you: ", DIM) + q)
            channel(q)
        return 0

    channel(rites.invocation(spirit))
    _status(err, "  Speak to the spirit. /epitaph /obituary /record /resurrect /bye")
    while True:
        try:
            question = input(paint("you: ", DIM)).strip()
        except EOFError:
            question = "/bye"
        if not question:
            continue
        try:
            if question in ("/bye", "/exit", "/quit"):
                channel("*The candles are burning low. The medium thanks you and asks for your parting words.*")
                return 0
            if question == "/record":
                print(rites.record(spirit) + "\n")
            elif question == "/epitaph":
                print(paint("  🪦 " + seance.epitaph(), MARIGOLD) + "\n")
            elif question == "/obituary":
                print(seance.obituary() + "\n")
            elif question == "/resurrect":
                where = history.resurrect(repo, spirit)
                print(paint(f"  ⚡ {spirit.path} walks again: {where}", MARIGOLD) + "\n")
            else:
                channel(question)
        except SeanceError as e:  # a hiccup shouldn't end the séance
            print(err("\n☠  " + str(e), RED), file=sys.stderr)


def rite_epitaph(args, paint, err) -> int:
    spirit = history.summon(Repo(args.repo), args.path, args.ref)
    print(Seance(spirit, None if args.plain else _medium(args, err)).epitaph())
    return 0


def rite_obituary(args, paint, err) -> int:
    spirit = history.summon(Repo(args.repo), args.path, args.ref)
    print(Seance(spirit, None if args.plain else _medium(args, err)).obituary())
    return 0


# --------------------------------------------------------------------------
# markdown for pull request comments: everything from git or the model is
# untrusted text (file names, commit messages, model output)

_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>!|~#])")


def md_text(text: str) -> str:
    text = _MD_SPECIAL.sub(r"\\\1", text)
    text = re.sub(r"https?://", lambda m: m.group(0).replace("://", ":​//"), text)
    return text.replace("@", "@​")


def md_code(text: str) -> str:
    text = text.replace("\n", " ").replace("@", "@​")
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    return f"{fence} {text} {fence}"


def rite_obituaries(args, paint, err) -> int:
    rng = args.range
    if "..." in rng:
        base, head = rng.split("...", 1)
    elif ".." in rng:
        base, head = rng.split("..", 1)
    else:
        raise SeanceError("Give a range like origin/main..HEAD")
    repo = Repo(args.repo)
    head = head or "HEAD"
    dead = history.deaths_in_range(repo, base or "HEAD", head)
    if not dead:
        return 0
    medium = None if args.plain else _medium(args, err)
    md = args.format == "markdown"
    entries: List[str] = []
    epitaphs: List[str] = []
    used_model = medium is not None
    for path in dead[: args.max]:
        try:
            spirit = history.summon(repo, path, head)
        except SeanceError as e:
            _status(err, f"   skipping {path}: {e}")
            continue
        _status(err, f"✍  writing the obituary of {path}")
        seance = Seance(spirit, medium)
        try:
            epitaph = seance.epitaph(epitaphs)
            obituary = seance.obituary()
        except SpiritsSilent as e:
            _status(err, f"   the medium is silent ({e}); writing from the facts alone")
            medium, used_model = None, False
            seance = Seance(spirit, None)
            epitaph, obituary = seance.epitaph(), seance.obituary()
        epitaphs.append(epitaph)
        if md:
            stats = (rites.plural(spirit.line_count, "line") + f" of {spirit.language}") if not spirit.is_binary else "binary"
            entries.append(
                f"### 🪦 {md_code(spirit.path)} · {rites.years(spirit)}\n\n"
                f"> _{md_text(epitaph)}_\n\n"
                f"{md_text(obituary)}\n\n"
                f"<sub>{md_text(stats)} · {rites.plural(len(spirit.life), 'commit')} · "
                f"lived {rites.lifespan(spirit.lifespan_days)} · speak with it: "
                f"{md_code('git seance summon ' + _shell_quote(spirit.path))}</sub>\n"
            )
        else:
            entries.append(f"{spirit.path} ({rites.years(spirit)})\n  “{epitaph}”\n\n{obituary}\n")
    rest = len(dead) - args.max
    out: List[str] = []
    if md:
        noun = rites.plural(len(dead), "file")
        if used_model and medium is not None and medium.is_local:
            how = (f"Epitaphs and character sketches by `{medium.model}`, an open-weight model running inside this job, "
                   "checked line by line against git history. No code left the runner.")
        elif used_model and medium is not None:
            how = f"Epitaphs and character sketches by `{medium.model}` at a remote medium, checked against git history."
        else:
            how = "No model was reachable, so these were written from git facts alone."
        out.append(f"## 🕯️ In Memoriam\n\n_This change lays {noun} to rest. {how}_\n")
    out += entries
    if rest > 0:
        out.append(f"_…and {rest} more rest in unmarked graves._\n")
    if md:
        out.append("<sub>Rites performed by [git-seance](https://github.com/ANIRUDDH-001/git-seance).</sub>")
    print("\n".join(out))
    return 0


def rite_ofrenda(args, paint, err) -> int:
    from .ofrenda import build_ofrenda

    repo = Repo(args.repo)
    if args.only:
        spirits = [history.summon(repo, p, args.ref) for p in args.only]
    else:
        graves = history.graveyard(repo, args.ref, args.pathspec)[: args.limit]
        spirits = [history.summon(repo, g.path, args.ref) for g in graves]
    if not spirits:
        print("No one to honor yet. The ofrenda stays bare.")
        return 0
    medium = None if args.plain else _medium(args, err)
    offerings, epitaphs = [], []
    for spirit in spirits:
        _status(err, f"🌼 placing {spirit.path} on the ofrenda")
        try:
            epitaph = Seance(spirit, medium).epitaph(epitaphs)
        except SpiritsSilent as e:
            _status(err, f"   the medium is silent ({e}); carving the words each was born with")
            medium, epitaph = None, rites.plain_epitaph(spirit)
        epitaphs.append(epitaph)
        offerings.append((spirit, epitaph))
    title = args.title or os.path.basename(repo.root)
    page = build_ofrenda(title, offerings, model=medium.model if medium else None,
                         local=medium.is_local if medium else True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(paint(f"🌼 The ofrenda for {title} is ready: {args.output}", MARIGOLD))
    return 0


def rite_resurrect(args, paint, err) -> int:
    repo = Repo(args.repo)
    spirit = history.summon(repo, args.path, args.ref)
    where = history.resurrect(repo, spirit, force=args.force)
    print(paint(f"⚡ {spirit.path} walks again, as it was before {spirit.death.short}.", MARIGOLD))
    print(paint(f"   {where}  (staged; commit it to make it permanent)", DIM))
    return 0
