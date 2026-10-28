"""The exorcist: catches the model putting words in the dead's mouths.

A small model asked to play a ghost will happily invent a timeline, a
birthday or a line of code. The exorcist pulls checkable claims out of a
reply (numbers, years, times of day, commit hashes, names, quotations, code,
file paths) and looks each one up in what git actually knows about the file:
its record, its commit messages and its last contents.

It cannot judge vibes ("I was lonely"), and it doesn't try to. It only
guards the facts, which is where hallucinations do real damage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set

from .history import Spirit

_NUMBER_WORDS = {
    "zero": 0, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
}
# "one" and "a single" are too common in prose to police.
_TENS = {"twenty", "thirty", "forty", "fourty", "fifty", "sixty", "seventy", "eighty", "ninety"}

_UNITS = "one|two|three|four|five|six|seven|eight|nine"
_YEAR_WORDS = re.compile(  # "nineteen ninety-nine", "twenty twenty-three", "nineteen oh five"
    r"\b(nineteen|twenty) (?:hundred (?:and )?)?"
    r"(ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[- ](?:" + _UNITS + r"))?|oh[- ](?:" + _UNITS + r"))\b", re.I)
_TWO_THOUSAND = re.compile(r"\btwo thousand(?:[- ](?:and[- ])?(" + _UNITS + r"|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                           r"sixteen|seventeen|eighteen|nineteen|twenty(?:[- ](?:" + _UNITS + r"))?))?\b", re.I)
_CODE_BLOCK = re.compile(r"```[\w+-]*\n?(.*?)```", re.S)
_BACKTICK = re.compile(r"`([^`\n]+)`")
_QUOTED = re.compile(r"[\"“]([^\"“”]{12,}?)[\"”]")
_TIME = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")
_SHA = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")
_DIGITS = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")
_WORDNUM = re.compile(r"\b(" + "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True)) + r")(?:[- ](one|two|three|four|five|six|seven|eight|nine))?\b", re.I)
_LIST_MARKER = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?\d{1,2}[.)]\s", re.M)
_PATH = re.compile(r"(?<![\w/])(?:[\w.-]+/)*[\w-]+\.(?:py|js|ts|c|h|cc|cpp|go|rs|java|rb|php|sh|cbl|md|rst|txt|json|ya?ml|toml|html|css)\b")
_NAMEISH = re.compile(r"\b(?:by|from|with|named|called|to)\s+((?:[A-Z][\w'’-]+)(?:\s+[A-Z][\w'’-]+)*)|\b([A-Z][a-z][\w'’-]+(?:\s+[A-Z][\w'’-]+)+)")

# Capitalized words a ghost may use without them being invented people.
_COMMON_CAPS = set("""
I I'm I've I'd I'll My Me The A An And But Or So Yet For Of In On At To From By With As It Its It's This That
These Those There Their They We Our You Your He She His Her Who What When Where Why How Yes No Not Now Then
Here Once Still Perhaps Maybe Ah Oh Alas Rise Spirit Ghost Medium Death Life Mist Darkness Light Candle
Candles Séance Seance Ofrenda Gazette Repository Memoriam Rest Peace Here Lies Farewell Goodbye Hello
Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August
September October November December Halloween Día Dia Muertos Los De God Heaven Hell Python JavaScript
TypeScript Rust Go Java Ruby Perl Shell Bash COBOL Fortran Pascal Lua Swift Kotlin Scala Haskell C Git GitHub
Unix Linux Windows Mac Internet Web HTTP HTTPS SMTP API JSON HTML CSS SQL PDF TODO FIXME XXX HACK Y2K PEP
Remember Forgive Forgotten Gone Even Every Each All Some Many Few One Two Three Long Short Old New First
Last Final Never Always Only Just Too Very Much More Most Less Within Without Before After During Through
Until Since Like Unlike Truly Indeed Speak Listen Ask Tell Hear See Look Behold Whisper Whispers Echo Echoes
""".split())


@dataclass
class Claim:
    kind: str
    text: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.text}"


@dataclass
class Verdict:
    claims: List[Claim] = field(default_factory=list)
    unsupported: List[Claim] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.unsupported


def _small_number(words: str) -> int:
    total = 0
    for w in re.split(r"[- ]+", words.lower()):
        if w in _NUMBER_WORDS:
            total += _NUMBER_WORDS[w]
        elif w == "one":
            total += 1
    return total


def _year_from_words(m: re.Match) -> str:
    century = 19 if m.group(1).lower() == "nineteen" else 20
    rest = re.sub(r"^oh[- ]", "", m.group(2).lower())
    return str(century * 100 + _small_number(rest))


def spell_out_years(text: str) -> str:
    """'nineteen ninety-nine' -> '1999', 'two thousand twenty-two' -> '2022'."""
    text = _TWO_THOUSAND.sub(lambda m: str(2000 + (_small_number(m.group(1)) if m.group(1) else 0)), text)
    return _YEAR_WORDS.sub(_year_from_words, text)


def _depossess(token: str) -> str:
    return re.sub(r"['’]s$", "", token)


def _norm(text: str) -> str:
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


class Exorcist:
    def __init__(self, spirit: Spirit, record_text: str = ""):
        self.spirit = spirit
        messages = [c.subject for c in spirit.life] + [spirit.death_message, spirit.death.subject]
        people = [c.author for c in spirit.life] + [spirit.death.author]
        parts = [record_text, spirit.path, *spirit.past_names, *messages, *people,
                 *spirit.successors, *spirit.died_alongside, spirit.last_words or ""]
        self.corpus = _norm("\n".join(parts))
        self.corpus_plain = self.corpus.replace("`", "")
        self.code = _norm(spirit.last_words or "")
        self.code_lines = {_norm(ln) for ln in (spirit.last_words or "").splitlines() if ln.strip()}
        self.words = set(re.findall(r"[\w'’-]+", self.corpus))
        self.shas = {c.sha for c in spirit.life} | {spirit.death.sha}
        self.numbers = self._known_numbers()

    def _known_numbers(self) -> Set[int]:
        s = self.spirit
        known = {0, 1}
        known |= {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", self.corpus) if n.replace(",", "").isdigit()}
        dates = [c.date for c in s.life] + [s.death.date]
        for d in dates:
            known |= {d.year, d.month, d.day, d.year % 100}
        days = s.lifespan_days
        if days is not None:
            years, rest = divmod(days, 365)
            known |= {days, years, rest // 30, days // 30, days // 7, (days + 182) // 365}
        known |= {len(s.life), s.line_count, len(s.family), s.died_alongside_count, s.size_bytes,
                  len(s.unfinished_business), len(s.successors), len(s.past_names)}
        known |= {n for _, n in s.family}
        return known

    # ------------------------------------------------------------------

    def judge(self, reply: str) -> Verdict:
        verdict = Verdict()
        text = spell_out_years(reply)

        def add(kind: str, claim_text: str, ok: bool) -> None:
            claim = Claim(kind, claim_text.strip())
            verdict.claims.append(claim)
            if not ok:
                verdict.unsupported.append(claim)

        # code: fenced blocks and `inline spans` must be the file's own words
        for block in _CODE_BLOCK.findall(text):
            for line in block.splitlines():
                if len(line.strip()) >= 4:
                    add("code", line, _norm(line) in self.code)
        text = _CODE_BLOCK.sub(" ", text)

        for quote in _QUOTED.findall(text):
            q = _norm(quote.replace("`", "")).strip(" .,;:!?…*")
            add("quote", quote, q in self.corpus_plain)
        text = _QUOTED.sub(" ", text)

        for span in _BACKTICK.findall(text):
            add("code", span, _norm(span) in self.corpus)
        text = _BACKTICK.sub(" ", text)

        for m in _TIME.finditer(text):
            add("time", m.group(0), _norm(m.group(0)) in self.corpus)
        text = _TIME.sub(" ", text)

        for m in _SHA.finditer(text):
            add("commit", m.group(0), any(sha.startswith(m.group(0)) for sha in self.shas))
        text = _SHA.sub(" ", text)

        for m in _PATH.finditer(text):
            add("path", m.group(0), _norm(m.group(0)) in self.corpus)
        text = _PATH.sub(" ", text)

        text = _LIST_MARKER.sub(" ", text)
        for m in _DIGITS.finditer(text):
            raw = m.group(0).replace(",", "")
            if raw.replace(".", "").isdigit() and "." not in raw:
                add("number", m.group(0), int(raw) in self.numbers)
        for m in _WORDNUM.finditer(text):
            word = m.group(1).lower()
            value = _NUMBER_WORDS[word] + (_NUMBER_WORDS.get((m.group(2) or "").lower(), 0) if word in _TENS else 0)
            add("number", m.group(0), value in self.numbers)

        for m in _NAMEISH.finditer(text):
            name = (m.group(1) or m.group(2) or "").strip()
            tokens = [_depossess(t) for t in re.split(r"\s+", name) if t]
            strange = [t for t in tokens if t not in _COMMON_CAPS and t.strip("'’").lower() not in self.words]
            if strange:
                add("name", name, False)
            elif len(tokens) >= 2 and any(t not in _COMMON_CAPS for t in tokens):
                add("name", name, True)
        return verdict


def describe(unsupported: List[Claim], limit: int = 4) -> str:
    shown = ", ".join(f"“{c.text}”" for c in unsupported[:limit])
    more = f" and {len(unsupported) - limit} more" if len(unsupported) > limit else ""
    return shown + more
