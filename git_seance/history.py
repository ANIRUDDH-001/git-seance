"""Excavate the dead from git history.

Everything here is plain git plumbing: no network, no model. A *grave* is a
path whose most recent change in history is a deletion. A *spirit* is the full
record we can reconstruct for one grave: birth, life, death, last words.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

# Field and record separators that cannot appear in commit metadata we print.
_FS = "\x1f"
_RS = "\x1e"
_FORMAT = _RS + _FS.join(["%H", "%an", "%ae", "%aI", "%s"])


class SeanceError(Exception):
    """Something a user should see, without a traceback."""


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    email: str
    date: datetime
    subject: str

    @property
    def short(self) -> str:
        return self.sha[:7]


@dataclass
class Grave:
    path: str
    death: Commit
    birth: Optional[Commit] = None

    @property
    def name(self) -> str:
        return os.path.basename(self.path)


@dataclass
class Spirit:
    path: str
    death: Commit
    death_message: str
    birth: Optional[Commit]
    life: List[Commit]                      # oldest first, excludes the death
    past_names: List[str]
    last_words: Optional[str]               # None for binary files
    size_bytes: int
    successors: List[str] = field(default_factory=list)
    died_alongside: List[str] = field(default_factory=list)
    died_alongside_count: int = 0
    moves: List[Tuple[str, str, Commit]] = field(default_factory=list)  # (from, to, commit), oldest first
    birth_message: str = ""
    repo_name: str = ""
    afterlife: Optional[str] = None      # where its body went, if the name died in a rename
    afterlife_alive: bool = False        # ...and whether the body still lives there

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def is_binary(self) -> bool:
        return self.last_words is None

    @property
    def line_count(self) -> int:
        if not self.last_words:
            return 0
        return self.last_words.count("\n") + (0 if self.last_words.endswith("\n") else 1)

    @property
    def language(self) -> str:
        return language_of(self.path)

    @property
    def family(self) -> List[Tuple[str, int]]:
        """Authors who touched the file in life, most devoted first."""
        return Counter(c.author for c in self.life).most_common()

    @property
    def lifespan_days(self) -> Optional[int]:
        if not self.birth:
            return None
        return max(0, (self.death.date - self.birth.date).days)

    @property
    def brushes_with_death(self) -> List[Commit]:
        """Commits in life that moved, deprecated or tried to delete this file."""
        stems = {os.path.splitext(os.path.basename(p))[0] for p in [self.path, *self.past_names]}
        stems = {re.escape(st) for st in stems if len(st) >= 3}
        if not stems:
            return []
        stem = "(?:" + "|".join(sorted(stems)) + ")"
        # "imp.get_suffixes()" is one function's brush, not the module's
        named = re.compile(r"\b" + stem + r"\b(?!\.\w)", re.I)
        killed = re.compile(
            r"\b(?:remov|delet|drop|kill|deprecat|retir)\w*\s+(?:the\s+)?(?:[\w.]+(?:,|\s+and)\s+){0,3}" + stem + r"\b(?!\.\w)", re.I)
        moved = {c.sha for _, _, c in self.moves}
        return [
            c for c in self.life[1:]
            if c.sha in moved or killed.search(c.subject)
            or (re.search(r"deprecat", c.subject, re.I) and named.search(c.subject))
        ]

    @property
    def gift(self) -> str:
        """The words it was born with: the first line of the commit that added it."""
        return self.birth.subject if self.birth else ""

    @property
    def unfinished_business(self) -> List[str]:
        return find_unfinished_business(self.last_words or "")

    @property
    def favorite_imports(self) -> List[str]:
        return find_imports(self.last_words or "", self.path)


# --------------------------------------------------------------------------
# git plumbing


class Repo:
    def __init__(self, path: str = "."):
        self.path = path
        try:
            top = self._run(["rev-parse", "--show-toplevel"]).strip()
        except SeanceError:
            raise SeanceError(
                "There are no spirits here: this is not a git repository."
            ) from None
        self.root = top
        # Remember where we were inside the repo, then do all work from the top
        # so every path we hand git is root-relative.
        self.prefix = self._run(["rev-parse", "--show-prefix"]).strip()
        self.path = top

    def run(self, args: Sequence[str], check: bool = True) -> str:
        return self._run(args, check)

    def _run(self, args: Sequence[str], check: bool = True) -> str:
        return self._run_bytes(args, check).decode("utf-8", errors="replace")

    def _run_bytes(self, args: Sequence[str], check: bool = True) -> bytes:
        cmd = ["git", "-c", "core.quotePath=false", *args]
        proc = subprocess.run(
            cmd, cwd=self.path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if check and proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()
            reason = err[0] if err else "unknown error"
            raise SeanceError(f"git {args[0]} failed: {reason.replace('fatal: ', '')}")
        return proc.stdout

    @property
    def shallow_boundary(self) -> set:
        """Commits whose parents were cut off by a shallow clone."""
        if not hasattr(self, "_shallow"):
            path = self._run(["rev-parse", "--git-path", "shallow"]).strip()
            path = path if os.path.isabs(path) else os.path.join(self.root, path)
            try:
                with open(path) as fh:
                    self._shallow = {line.strip() for line in fh if line.strip()}
            except OSError:
                self._shallow = set()
        return self._shallow

    def object_type(self, spec: str) -> str:
        return self._run(["cat-file", "-t", spec], check=False).strip()

    def has_commits(self, ref: str = "HEAD") -> bool:
        return bool(self._run(["rev-parse", "--verify", "--quiet", ref + "^{commit}"], check=False).strip())

    def tree_paths(self, ref: str = "HEAD") -> set:
        if not self.has_commits(ref):
            return set()
        out = self._run(["ls-tree", "-r", "--name-only", "-z", ref])
        return set(p for p in out.split("\0") if p)

    def exists_at(self, ref: str, path: str) -> bool:
        proc = subprocess.run(
            ["git", "cat-file", "-e", f"{ref}:{path}"],
            cwd=self.path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return proc.returncode == 0

    def blob(self, ref: str, path: str) -> Optional[bytes]:
        if not self.exists_at(ref, path):
            return None
        return self._run_bytes(["cat-file", "-p", f"{ref}:{path}"])

    def blob_line_counts(self, specs: Sequence[str]) -> Dict[str, Optional[int]]:
        """Line counts for many `rev:path` specs through one cat-file process.

        Binary blobs map to None.
        """
        if not specs:
            return {}
        proc = subprocess.run(
            ["git", "cat-file", "--batch"], cwd=self.path,
            input=("\n".join(specs) + "\n").encode(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, pos, counts = proc.stdout, 0, {}
        for spec in specs:
            nl = out.index(b"\n", pos)
            header = out[pos:nl].decode(errors="replace").split()
            pos = nl + 1
            if len(header) < 3 or header[1] == "missing":
                counts[spec] = None
                continue
            size = int(header[2])
            data = out[pos:pos + size]
            pos += size + 1
            counts[spec] = None if _looks_binary(data) else _count_lines(data)
        return counts

    def log(self, args: Sequence[str]) -> Iterator[Tuple[Commit, List[Tuple[str, ...]]]]:
        """Yield (commit, [(status, path[, new_path])...]) newest first."""
        out = self._run(["log", "--format=" + _FORMAT, *args])
        for record in out.split(_RS):
            if not record.strip():
                continue
            header, _, rest = record.partition("\n")
            yield _parse_commit(header), _parse_name_status(rest)

    def message(self, sha: str) -> str:
        return self._run(["log", "-1", "--format=%B", sha]).strip()


def _parse_commit(header: str) -> Commit:
    sha, author, email, date, subject = header.split(_FS, 4)
    return Commit(sha, author, email, _parse_date(date), subject)


def _parse_date(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):  # Python < 3.11 can't parse a bare Z
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _parse_name_status(text: str) -> List[Tuple[str, ...]]:
    changes = []
    for line in text.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        parts = line.split("\t")
        changes.append((parts[0][:1], *parts[1:]))
    return changes


def _looks_binary(data: bytes) -> bool:
    return b"\0" in data[:8000]


def _count_lines(data: bytes) -> int:
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


# --------------------------------------------------------------------------
# the graveyard


def graveyard(repo: Repo, ref: str = "HEAD", pathspec: Sequence[str] = (),
              include_fragments: bool = False) -> List[Grave]:
    """Every path that died and stayed dead, most recent death first.

    Renames are reincarnations, not deaths: `-M` folds a delete+add pair into
    a single R entry, which the diff filter drops. `--cc` also shows files
    deleted while resolving a merge. Changelog fragments (one-paragraph files
    born to be deleted at release time) are left out unless asked for.
    """
    if not repo.has_commits(ref):
        return []
    alive = repo.tree_paths(ref)
    graves: Dict[str, Grave] = {}
    state: Dict[str, str] = {}
    args = ["-M", "--cc", "--diff-filter=AD", "--name-status", ref]
    if pathspec:
        args += ["--", *(_normalize(repo, p) for p in pathspec)]
    for commit, changes in repo.log(args):
        for status, path, *_ in changes:
            seen = state.get(path)
            if seen is None:
                if status == "D" and path not in alive and (include_fragments or not is_fragment(path)):
                    graves[path] = Grave(path, commit)
                    state[path] = "awaiting-birth"
                else:
                    state[path] = "ignore"
            elif seen == "awaiting-birth" and status == "A":
                graves[path].birth = commit
                state[path] = "done"
    return list(graves.values())


def deaths_in_range(repo: Repo, base: str, head: str) -> List[str]:
    """Paths that exist where `head` branched from `base` and are gone at `head`.

    A tree diff, like a pull request's "files changed": a file deleted and
    then restored inside the range didn't die, and renames don't count.
    """
    for ref in (base, head):
        if not repo.has_commits(ref):
            raise SeanceError(f"Unknown commit {ref!r}.")
    fork = repo._run(["merge-base", base, head], check=False).strip() or base
    out = repo._run(["diff", "-M", "--diff-filter=D", "--name-only", "-z", fork, head])
    return [p for p in out.split("\0") if p]


# --------------------------------------------------------------------------
# summoning one spirit


def summon(repo: Repo, path: str, ref: str = "HEAD") -> Spirit:
    path = _normalize(repo, path)
    if not repo.has_commits(ref):
        raise SeanceError("This repository has no history yet. Nothing has had time to die.")
    deaths = list(repo.log(["-1", "-M", "--cc", "--diff-filter=D", "--name-status", ref, "--", path]))
    if not deaths:
        if repo.exists_at(ref, path):
            raise SeanceError(f"{path} still walks among the living. Only the dead can be summoned.")
        raise SeanceError(f"No grave bears the name {path}. Try `git seance graveyard`.")
    death, _ = deaths[0]
    if repo.exists_at(ref, path):
        raise SeanceError(f"{path} died once but has since been resurrected. It is alive at {ref}.")
    if repo.object_type(f"{death.sha}^:{path}") == "tree":
        raise SeanceError(
            f"{path} was a whole directory. Summon its files one by one; see `git seance graveyard {path}/`.")
    # With a pathspec git can't see that a "deletion" was half of a rename.
    # The name died; the body lives on elsewhere: an afterlife.
    afterlife = None
    for _, changes in repo.log(["-1", "-M", "--name-status", death.sha]):
        for status, *paths in changes:
            if status == "R" and paths[0] == path:
                afterlife = paths[1]

    before = death.sha + "^"
    raw = repo.blob(before, path) or b""
    last_words = None if _looks_binary(raw) else raw.decode("utf-8", errors="replace")

    life: List[Commit] = []
    past_names: List[str] = []
    moves: List[Tuple[str, str, Commit]] = []
    for commit, changes in repo.log(["--follow", "-M", "--name-status", before, "--", path]):
        life.append(commit)
        for status, *paths in changes:
            if status == "R" and len(paths) == 2:
                moves.append((paths[0], paths[1], commit))
            for p in paths:
                if p != path and p not in past_names:
                    past_names.append(p)
    life.reverse()
    moves.reverse()
    birth = life[0] if life else None
    if birth and birth.sha in repo.shallow_boundary:
        birth = None  # its true birth lies beyond the shallow clone's horizon

    added, deleted = [], []
    for _, changes in repo.log(["-1", "-M", "--name-status", death.sha]):
        for status, p, *rest in changes:
            if status == "A":
                added.append(p)
            elif status == "D" and p != path:
                deleted.append(p)

    return Spirit(
        path=path,
        death=death,
        death_message=clean_message(repo.message(death.sha)),
        birth=birth,
        life=life,
        past_names=past_names,
        last_words=last_words,
        size_bytes=len(raw),
        successors=[p for p in added if not is_paperwork(p)][:6],
        died_alongside=deleted[:6],
        died_alongside_count=len(deleted),
        moves=moves,
        birth_message=clean_message(repo.message(birth.sha)) if birth else "",
        repo_name=os.path.basename(repo.root),
        afterlife=afterlife,
        afterlife_alive=bool(afterlife) and repo.exists_at(ref, afterlife),
    )


def resurrect(repo: Repo, spirit: Spirit, force: bool = False) -> str:
    target = os.path.join(repo.root, spirit.path)
    if spirit.afterlife_alive and not force:
        raise SeanceError(f"{spirit.path}'s body still lives on as {spirit.afterlife}. Use --force to raise a twin.")
    if os.path.exists(target) and not force:
        raise SeanceError(f"Something already lives at {spirit.path}. Use --force to displace it.")
    repo.run(["checkout", spirit.death.sha + "^", "--", spirit.path])
    return target


def _normalize(repo: Repo, path: str) -> str:
    """Accept paths relative to the cwd and turn them into repo-root paths."""
    path = path.replace(os.sep, "/")
    if os.path.isabs(path):
        rel = os.path.relpath(path, repo.root)
    else:
        rel = os.path.normpath(os.path.join(repo.prefix, path))
    return rel.replace(os.sep, "/")


# --------------------------------------------------------------------------
# reading the remains

# Files born in a killing commit that are bookkeeping, not heirs.
_PAPERWORK = re.compile(
    r"(^|/)(news|changelog|changes|history|authors|contributors)([._-][^/]*)?$|(^|/)(misc/news\.d|docs?|documentation)/"
    r"|\.(md|rst|txt|lock)$|(^|/)(package-lock\.json|yarn\.lock|poetry\.lock|cargo\.lock)$",
    re.I,
)


def is_paperwork(path: str) -> bool:
    return bool(_PAPERWORK.search(path))


# One-paragraph changelog entries that are born to be swept up at release.
_FRAGMENT = re.compile(r"(^|/)(misc/news\.d|changelog\.d|changes|newsfragments|\.changeset)/", re.I)


def is_fragment(path: str) -> bool:
    return bool(_FRAGMENT.search(path))


_TRAILER = re.compile(r"^(co-authored-by|signed-off-by|reviewed-by|acked-by|change-id|cc):", re.I)


def clean_message(message: str) -> str:
    """A commit message without its trailers (Co-authored-by: ... <email>)."""
    lines = [ln for ln in message.splitlines() if not _TRAILER.match(ln.strip())]
    return "\n".join(lines).strip()


_BUSINESS = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[:\s(]*(.*)")

_IMPORT_PATTERNS = {
    "Python": [r"^\s*from\s+([\w.]+)\s+import\b", r"^\s*import\s+([\w.]+)"],
    "JavaScript": [r"require\(\s*['\"]([^'\"]+)['\"]", r"^\s*import\s.*?from\s+['\"]([^'\"]+)['\"]"],
    "TypeScript": [r"require\(\s*['\"]([^'\"]+)['\"]", r"^\s*import\s.*?from\s+['\"]([^'\"]+)['\"]"],
    "C": [r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]"],
    "C++": [r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]"],
    "Go": [r"^\s*(?:import\s+)?\"([\w./-]+)\"\s*$"],
    "Rust": [r"^\s*use\s+([\w:]+)"],
    "Java": [r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;"],
    "Kotlin": [r"^\s*import\s+([\w.]+)"],
    "Ruby": [r"^\s*require(?:_relative)?\s+['\"]([^'\"]+)['\"]"],
    "PHP": [r"^\s*use\s+([\w\\]+)\s*;", r"require(?:_once)?\s*\(?\s*['\"]([^'\"]+)['\"]"],
}

_LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".c": "C",
    ".h": "C", ".cc": "C++", ".cpp": "C++", ".hpp": "C++", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".rb": "Ruby", ".php": "PHP", ".sh": "Shell",
    ".bash": "Shell", ".pl": "Perl", ".cbl": "COBOL", ".cob": "COBOL", ".f": "Fortran",
    ".f90": "Fortran", ".pas": "Pascal", ".lua": "Lua", ".swift": "Swift", ".m": "Objective-C",
    ".cs": "C#", ".vb": "Visual Basic", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".md": "Markdown", ".rst": "reStructuredText", ".txt": "plain text", ".json": "JSON",
    ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML", ".xml": "XML", ".sql": "SQL",
    ".coffee": "CoffeeScript", ".vue": "Vue", ".svelte": "Svelte", ".ex": "Elixir",
    ".erl": "Erlang", ".hs": "Haskell", ".ml": "OCaml", ".clj": "Clojure", ".scala": "Scala",
    ".r": "R", ".jl": "Julia", ".dart": "Dart", ".zig": "Zig", ".asm": "Assembly",
    ".s": "Assembly", ".bat": "Batch", ".ps1": "PowerShell", ".mk": "Makefile",
}

_SPECIAL_NAMES = {"makefile": "Makefile", "dockerfile": "Dockerfile", "gemfile": "Ruby", "rakefile": "Ruby"}


def language_of(path: str) -> str:
    base = os.path.basename(path)
    if base.lower() in _SPECIAL_NAMES:
        return _SPECIAL_NAMES[base.lower()]
    ext = os.path.splitext(base)[1].lower()
    return _LANGUAGES.get(ext, "unknown tongue")


def find_unfinished_business(text: str, limit: int = 6) -> List[str]:
    found = []
    for line in text.splitlines():
        m = _BUSINESS.search(line)
        if m and len(m.group(2).strip(" */#-:")) >= 4:  # a bare "TODO" says nothing
            note = (m.group(1) + ": " + m.group(2).strip(" */#-")).strip(": ")
            note = note[:110]
            if note not in found:
                found.append(note)
            if len(found) >= limit:
                break
    return found


def find_imports(text: str, path: str, limit: int = 8) -> List[str]:
    patterns = _IMPORT_PATTERNS.get(language_of(path))
    if not patterns:
        return []
    regexes = [re.compile(p) for p in patterns]
    found: List[str] = []
    for line in text.splitlines():
        for rx in regexes:
            m = rx.search(line)
            if m and m.group(1) not in found:
                found.append(m.group(1))
        if len(found) >= limit:
            break
    return found[:limit]


_OUTLINE = re.compile(
    r"^\s*(?:export\s+)?(?:pub(?:\(\w+\))?\s+)?(?:async\s+)?"
    r"(?:def|class|function|func|fn|struct|interface|impl|module|procedure|sub|enum|trait)\b"
)


def outline(text: str, limit: int = 40) -> List[str]:
    """The skeleton of a file: its def/class/function lines."""
    lines = [ln.rstrip() for ln in text.splitlines() if _OUTLINE.match(ln)]
    if len(lines) <= limit:
        return lines
    step = len(lines) / limit  # sample evenly so the whole body is represented
    return [lines[int(i * step)] for i in range(limit)]
