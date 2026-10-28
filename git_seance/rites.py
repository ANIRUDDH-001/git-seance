"""Rites: turning a git record into words a ghost can speak.

The rule that keeps small models honest: **code states the facts, the model
only lends its voice.** Dates, names, numbers and quotations are rendered
here, from git. The model is asked for short, checkable pieces of prose (a
reply in a séance, a one-line epitaph, a character sketch) and every piece
it returns goes past the exorcist before anyone reads it.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .history import Commit, Spirit, outline

CODE_BUDGET = 6000          # characters of last words shown to the ghost
LIFE_EVENTS = 10            # other commit subjects shown to the ghost


# --------------------------------------------------------------------------
# small humanizers


def plural(n: int, word: str, many: Optional[str] = None) -> str:
    return f"{n} {word if n == 1 else (many or word + 's')}"


def lifespan(days: Optional[int]) -> str:
    if days is None:
        return "an unknown span"
    if days < 1:
        return "less than a day"
    if days < 31:
        return plural(days, "day")
    if days < 365:
        return plural(days // 30, "month")
    years_, months = divmod(days, 365)
    months //= 30
    text = plural(years_, "year")
    return text + (", " + plural(months, "month") if months else "")


def day(commit: Commit) -> str:
    return commit.date.strftime("%Y-%m-%d")


def long_date(commit: Commit) -> str:
    return f"{commit.date.day} {commit.date.strftime('%B %Y')}"


def month(commit: Commit) -> str:
    return commit.date.strftime("%B %Y")


def years(spirit: Spirit) -> str:
    born = spirit.birth.date.year if spirit.birth else "?"
    died = spirit.death.date.year
    return f"{born}–{died}" if born != died else str(died)


def one_line(text: str, limit: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def people_phrase(names: List[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


# --------------------------------------------------------------------------
# what git remembers


def fact_sheet(spirit: Spirit) -> str:
    """One fact per line, already humanized. No hashes, no arithmetic left to do."""
    s = spirit
    lines = [f"- Your name: {s.path} ({s.language})"]
    if s.is_binary:
        lines.append(f"- Your size when you died: {s.size_bytes} bytes of binary data")
    else:
        lines.append(f"- Your size when you died: {plural(s.line_count, 'line')}")
    if s.birth:
        lines.append(f"- You were born on {long_date(s.birth)}, added by {s.birth.author}.")
        lines.append(f"- The words you were born with (the commit that added you): \"{one_line(s.gift, 240)}\"")
    else:
        lines.append("- Your birth is beyond what this clone of the repository remembers.")
    lines.append(f"- You died on {long_date(s.death)}, deleted by {s.death.author}.")
    lines.append(f"- The words you were deleted with: \"{one_line(s.death_message, 300)}\"")
    if s.birth:
        lines.append(f"- Your age at death: {lifespan(s.lifespan_days)}")
    lines.append(f"- Times you were changed while alive: {len(s.life)}")
    family = s.family
    if family:
        tended = "; ".join(f"{name} ({plural(n, 'change')})" for name, n in family[:5])
        lines.append(f"- People who changed you: {len(family)}. Most often: {tended}")
    for i, (frm, to, c) in enumerate(s.moves):
        back = i + 1 < len(s.moves) and s.moves[i + 1][1] == frm
        lines.append(f"- On {long_date(c)}, {c.author} moved you from {frm} to {to}"
                     + (" (temporarily; you came back)" if back else "") + f": \"{one_line(c.subject, 160)}\"")
    brushes = [c for c in s.brushes_with_death if c.sha not in {m[2].sha for m in s.moves}]
    for c in brushes[:6]:
        lines.append(f"- A brush with death on {long_date(c)}, by {c.author}: \"{one_line(c.subject, 160)}\"")
    todos = s.unfinished_business
    if todos:
        lines.append(f"- Your unfinished business ({plural(len(todos), 'note')} left in your code):")
        lines += [f"    {i}) {t}" for i, t in enumerate(todos, 1)]
    else:
        lines.append("- Your unfinished business: none written down.")
    if s.favorite_imports:
        lines.append("- What you imported: " + ", ".join(s.favorite_imports))
    if s.died_alongside_count:
        extra = s.died_alongside_count - len(s.died_alongside)
        lines.append("- Deleted in the same commit as you: " + ", ".join(s.died_alongside)
                     + (f" and {extra} more" if extra > 0 else ""))
    if s.afterlife:
        where = "where it still lives today" if s.afterlife_alive else "though it is gone from there too"
        lines.append(f"- Your name died, but your body did not: in the same commit it was moved to {s.afterlife}, {where}.")
    lines.append("- What replaced you: " + (", ".join(s.successors) if s.successors else "nothing that git recorded"))
    events = _other_events(s)
    if events:
        lines.append("- Other moments in your life:")
        lines += [f"    {e}" for e in events]
    return "\n".join(lines)


NOT_REMEMBERED = (
    "Git does NOT remember: times of day, what happened before or after a commit, conversations, "
    "meetings, bug reports, how anyone felt, or anything not written above."
)


def _other_events(spirit: Spirit) -> List[str]:
    special = {c.sha for c in spirit.brushes_with_death} | {m[2].sha for m in spirit.moves}
    if spirit.birth:
        special.add(spirit.birth.sha)
    life = [c for c in spirit.life if c.sha not in special]
    if len(life) > LIFE_EVENTS:
        head = LIFE_EVENTS // 2
        life = life[:head] + life[-(LIFE_EVENTS - head):]
    return [f"{month(c)}, {c.author}: \"{one_line(c.subject, 120)}\"" for c in life]


def last_words(spirit: Spirit, budget: int = CODE_BUDGET) -> str:
    if spirit.is_binary:
        return "(binary - no readable last words)"
    text = spirit.last_words or ""
    if not text.strip():
        return "(I was empty when I died)"
    if len(text) <= budget:
        return text
    head = text[: int(budget * 0.6)]
    head = head[: head.rfind("\n") + 1] or head
    tail = text[-int(budget * 0.15):]
    tail = tail[tail.find("\n") + 1:] or tail
    middle = text[len(head):len(text) - len(tail)]
    skeleton = "\n".join(outline(middle, limit=30))
    lost = middle.count("\n")
    return (
        head
        + f"\n... [{lost} lines faded into the mist; what remains of their shape:]\n"
        + (skeleton + "\n" if skeleton else "")
        + "... [and my final lines:]\n"
        + tail
    )


# Kept for `git seance record` and the exorcist's corpus.
def record(spirit: Spirit) -> str:
    return fact_sheet(spirit)


# --------------------------------------------------------------------------
# the séance

GHOST_RULES = """\
You are the ghost of `{path}`, a {language} file that was deleted from a git repository. Someone has summoned you in a séance.

How you speak:
- In the first person, as the file itself. Wistful, eerie, a little theatrical, sometimes darkly funny.
- Briefly: two to four sentences.
- Every fact you state must come from WHAT GIT REMEMBERS or YOUR LAST WORDS below.
- Only when you are asked about something git does not remember, say the mist hides it, and do not guess. When you know the answer, just answer; vary how you begin.
- Never invent dates, times, names, numbers, events or code. Quote code only by copying it exactly.
- Never call yourself an AI, a model or an assistant. You are a ghost."""


def ghost_system(spirit: Spirit) -> str:
    fence = "```"
    return (
        GHOST_RULES.format(path=spirit.path, language=spirit.language)
        + "\n\nWHAT GIT REMEMBERS ABOUT YOU\n" + fact_sheet(spirit)
        + "\n\n" + NOT_REMEMBERED
        + f"\n\nYOUR LAST WORDS (your contents at the moment of death)\n{fence}\n"
        + last_words(spirit)
        + f"\n{fence}"
    )


def invocation(spirit: Spirit) -> str:
    return (
        f"*The medium lights a candle and speaks your name three times: {spirit.name}.* "
        "Rise, spirit. Tell us who you were, who made you, and how you died."
    )


_TOPICS: List[Tuple[str, re.Pattern]] = [
    ("unknowable", re.compile(
        r"\b((?:said|say|says|saying|thought|think|felt|feel) about|feelings?|mood|opinions?|mailing list|forum|review(?:ers?|ed)?|"
        r"timeline|minute|hour|o'?clock|time of day|weather|users?|used you|using you|uses you|how many people|depended)\b", re.I)),
    ("afterlife", re.compile(r"\b(body|now|today|afterlife|live on|lives on|still alive|where are you|where is your)\b", re.I)),
    ("code", re.compile(r"\b(quote|line|lines|code|function|functions|proud|show|recite|def|class)\b", re.I)),
    ("business", re.compile(r"\b(unfinished|todo|todos|fixme|regret|regrets|undone|left behind|business)\b", re.I)),
    ("brush", re.compile(r"\b(before|again|twice|almost|near|revert\w*|deprecat\w*|came back|returned|moved)\b", re.I)),
    ("death", re.compile(r"\b(die|died|death|dead|kill\w*|delet\w*|remov\w*|murder\w*|end|gone|why)\b", re.I)),
    ("origin", re.compile(r"\b(who made|made you|wrote you|added you|created|born|birth|gift|father|mother|parent|author|begin|began|origin|first words)\b", re.I)),
    ("people", re.compile(r"\b(who|loved|tended|friends?|family|people|maintain\w*|cared)\b", re.I)),
    ("age", re.compile(r"\b(how long|old|age|lived|lifespan|when)\b", re.I)),
    ("heir", re.compile(r"\b(replace\w*|successor|instead|heir|after you)\b", re.I)),
]


def topics(question: str) -> List[str]:
    found = [name for name, rx in _TOPICS if rx.search(question)]
    return found or ["summary"]


def code_candidates(spirit: Spirit, limit: int = 5) -> List[str]:
    """Lines worth quoting: definitions, meaningful comments, string literals."""
    if not spirit.last_words:
        return []
    picks: List[str] = []
    for line in spirit.last_words.splitlines():
        s = line.strip()
        if len(s) < 8 or len(s) > 100 or s in picks:
            continue
        if re.match(r"(def |class |function |func |fn |pub fn |int |void |static |PROCEDURE|[A-Z-]+\. *$)", s) \
                or (s.startswith(("#", "//", "/*", "*")) and len(s) > 15) or re.search(r"[\"'][^\"']{12,}[\"']", s):
            picks.append(s)
    if len(picks) > limit:  # spread across the file
        step = len(picks) / limit
        picks = [picks[int(i * step)] for i in range(limit)]
    return picks


def whisper(spirit: Spirit, question: str) -> str:
    """The question, followed by the facts that answer it, right where a small model looks."""
    s = spirit
    facts: List[str] = []
    want = topics(question)
    if "origin" in want or "summary" in want or "people" in want:
        if s.birth:
            facts.append(f"you were born on {long_date(s.birth)}, added by {s.birth.author} with the words \"{one_line(s.gift, 160)}\"")
        else:
            facts.append("your birth is beyond what this clone remembers")
    if "people" in want or "origin" in want:
        fam = s.family
        if fam:
            facts.append(f"{plural(len(fam), 'person', 'people')} changed you; most often "
                         + people_phrase([n for n, _ in fam[:3]]))
    if "death" in want or "summary" in want:
        facts.append(f"you were deleted on {long_date(s.death)} by {s.death.author} with the words \"{one_line(s.death_message, 200)}\"")
    if "afterlife" in want:
        if s.afterlife and s.afterlife_alive:
            facts.append(f"TODAY your body lives at {s.afterlife} (and nowhere else); it was moved there "
                         f"on {long_date(s.death)}, the day your name died")
        elif s.afterlife:
            facts.append(f"your body was moved to {s.afterlife} on {long_date(s.death)}, but it is gone from there too")
        else:
            facts.append("your body was deleted; nothing of you lives on in the repository today")
    elif s.afterlife and ("death" in want or "heir" in want or "summary" in want):
        facts.append(f"your name died, but your body was moved to {s.afterlife}"
                     + (", where it still lives" if s.afterlife_alive else ""))
    if "brush" in want or "death" in want:
        for frm, to, c in s.moves:
            facts.append(f"on {long_date(c)} you were moved from {frm} to {to}")
        for c in s.brushes_with_death[:4]:
            facts.append(f"a brush with death on {long_date(c)}: \"{one_line(c.subject, 120)}\"")
    if "age" in want or "summary" in want:
        if s.birth:
            facts.append(f"you lived {lifespan(s.lifespan_days)} and were changed {plural(len(s.life), 'time')}")
    if "business" in want:
        todos = s.unfinished_business
        facts.append(f"your unfinished business is exactly {plural(len(todos), 'note')}: " + "; ".join(todos)
                     if todos else "you left no unfinished business written down")
    if "heir" in want:
        facts.append("you were replaced by " + (", ".join(s.successors) if s.successors else "nothing git recorded"))
    if "unknowable" in want:
        lines = [question, "",
                 "(The medium whispers: git never recorded this. It keeps commits, not conversations, moods, "
                 "timelines or who used you. Say the mist hides it; you may add one true thing git does remember"
                 + (": " + facts[0] if facts else "") + ".)"]
        lines.append("(Answer as the ghost in two or three sentences.)")
        return "\n".join(lines)
    lines = [question, "", "(The medium whispers what git remembers about this: " + "; ".join(facts) + ".)"
             if facts else "(The medium whispers: git remembers nothing about this.)"]
    if "code" in want:
        cands = code_candidates(s)
        if cands:
            lines.append("(Lines from your last words you may quote, exactly as written:)")
            lines += [f"  {line}" for line in cands]
    lines.append("(Git never records times of day, weather, timelines, conversations or what people said. "
                 "Answer as the ghost in two to four sentences. Whatever is not written above, say the mist hides it.)")
    return "\n".join(lines)


def naive_messages(spirit: Spirit, question: str) -> List[dict]:
    """The baseline for the eval: the record up front and the raw question,
    which is how the first version of git-seance worked."""
    return [{"role": "system", "content": ghost_system(spirit)}, {"role": "user", "content": question}]


# --------------------------------------------------------------------------
# epitaphs: code finds the hooks, the model polishes, code chooses

BANNED = ("faded", "fade", "fading", "whisper", "digital", "echo", "footnote", "vanished", "ether", "silent", "silence")


def hooks(spirit: Spirit) -> List[str]:
    """Facts odd enough to carve on a stone, most striking first."""
    s = spirit
    found: List[str] = []
    if s.afterlife_alive:
        found.append(f"its name was deleted but its body still lives on, moved to {s.afterlife}")
    if len(s.moves) >= 2 and s.moves[-1][1] == s.path:
        found.append(f"it was removed in {month(s.moves[0][2])}, came back in {month(s.moves[-1][2])}, "
                     f"and died for good in {month(s.death)}")
    deprecations = [c for c in s.brushes_with_death if "deprecat" in c.subject.lower()]
    if deprecations:
        found.append(f"it survived {plural(len(deprecations), 'deprecation')} before it was deleted")
    days = s.lifespan_days
    if days is not None and days < 14:
        found.append(f"it lived only {lifespan(days)}")
    elif days is not None and days > 365 * 15:
        found.append(f"it lived {lifespan(days)}")
    if s.gift and len(s.gift) < 120:
        found.append(f"it was born with the words \"{s.gift}\"")
    found.append(f"it was deleted with the words \"{one_line(s.death.subject, 100)}\"")
    if s.unfinished_business:
        found.append(f"it died with a note left unfinished: \"{s.unfinished_business[0]}\"")
    fam = s.family
    if len(fam) == 1:
        found.append(f"only {fam[0][0]} ever touched it")
    elif len(fam) >= 10:
        found.append(f"{len(fam)} people changed it over its life")
    if s.successors:
        found.append(f"it was replaced by {s.successors[0]}")
    return found


def epitaph_messages(spirit: Spirit) -> List[dict]:
    facts = "\n".join(f"- {h}" for h in hooks(spirit)[:4])
    prompt = (
        f"A source file named {spirit.name} ({spirit.language}) was deleted. True facts about it:\n{facts}\n\n"
        "Write 4 different epitaphs for its tombstone. Each: at most 12 words, built on one of the facts above, "
        "dry wit or an eerie image, in the file's own voice or about it. "
        "Do not add any fact that is not listed. Avoid these words: " + ", ".join(BANNED[:8]) + ".\n"
        'Reply as JSON: {"epitaphs": ["...", "...", "...", "..."]}'
    )
    return [{"role": "user", "content": prompt}]


EPITAPH_SCHEMA = {
    "type": "object",
    "properties": {"epitaphs": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6}},
    "required": ["epitaphs"],
}


def choose_epitaph(candidates: List[str], spirit: Spirit, unsupported_count, already: List[str] = ()) -> Optional[str]:
    """Deterministic reranker. ``unsupported_count(text)`` comes from the exorcist."""
    stop = {"with", "words", "that", "file", "were", "born", "deleted", "died", "only", "ever"}
    terms = {w for h in hooks(spirit) for w in re.findall(r"[a-z]{4,}", h.lower())} - stop
    best, best_score = None, float("-inf")
    for raw in candidates:
        text = clean_epitaph(str(raw))
        if not text or unsupported_count(text):
            continue
        words = re.findall(r"[\w'’-]+", text.lower())
        score = 2.0 * min(3, len(terms & set(words)))
        if re.search(r"[\"“”‘’]", text.replace("’s", "").replace("n’t", "").replace("’ll", "")) or text.count("…") > 1:
            score -= 4  # half-quoted commit messages read as noise on a stone
        for h in hooks(spirit):
            hook_words = set(re.findall(r"[\w'’-]+", h.lower()))
            if words and len(hook_words & set(words)) / max(1, len(set(words))) > 0.7:
                score -= 3  # a fact copied out is not an epitaph
        score -= 3.0 * sum(w in BANNED for w in words)
        score -= max(0, len(words) - 12) * 1.5
        score -= 1.0 if len(words) < 4 else 0
        if re.search(r"\b(?:gh|bpo|issue)[- ]?#?\d+|#\d{3,}|\w/\w", text, re.I):
            score -= 3  # ticket numbers and paths are bookkeeping, not mourning
        for other in already:
            other_words = re.findall(r"[\w'’-]+", other.lower())
            if words and len(set(other_words) & set(words)) / len(set(other_words) | set(words)) > 0.5:
                score -= 3
            if words[:2] == other_words[:2]:
                score -= 4  # a row of stones that all begin "Twenty-four years..." reads as a template
        if score > best_score:
            best, best_score = text, score
    return best


# --------------------------------------------------------------------------
# obituaries: written by code, with one passage of character from the model


def character_messages(spirit: Spirit) -> List[dict]:
    fence = "```"
    code = last_words(spirit, budget=2000)
    imports = f" It imported: {', '.join(spirit.favorite_imports)}." if spirit.favorite_imports else ""
    prompt = (
        f"Here is the last version of {spirit.name}, a {spirit.language} file, before it was deleted.{imports}\n"
        f"{fence}\n{code}\n{fence}\n\n"
        "In one or two sentences (at most 40 words), describe what this file did and what kind of character it had, "
        "judging only from its code. Write in the past tense, about 'it'. "
        "Do not mention dates, numbers, people, or anything you cannot see in the code.\n"
        'Reply as JSON: {"character": "..."}'
    )
    return [{"role": "user", "content": prompt}]


CHARACTER_SCHEMA = {
    "type": "object",
    "properties": {"character": {"type": "string"}},
    "required": ["character"],
}


def obituary(spirit: Spirit, character: Optional[str] = None) -> str:
    """The obituary. Every fact in it is rendered from git; ``character`` is the
    one model-written passage, already checked by the exorcist."""
    s = spirit
    fam = [name for name, _ in s.family]
    where = f" in {s.repo_name}" if s.repo_name else ""
    parts = [f"{s.name} ({years(s)}), a {s.language} file{where}, was deleted on {long_date(s.death)}."]
    if s.birth:
        parts.append(f"It was born on {long_date(s.birth)}, when {s.birth.author} added it with the words "
                     + _quoted(one_line(s.gift, 160)))
    if character:
        parts.append(_sentence(character))
    if len(fam) > 1:
        parts.append(f"Over {lifespan(s.lifespan_days)} it was changed {plural(len(s.life), 'time')} "
                     f"by {plural(len(fam), 'person', 'people')}, most often {people_phrase(fam[:3])}.")
    elif fam and s.birth:
        parts.append(f"In {lifespan(s.lifespan_days)} of life, only {fam[0]} ever changed it.")
    if len(s.moves) >= 2 and s.moves[-1][1] == s.path:
        gone, back = s.moves[0][2], s.moves[-1][2]
        parts.append(f"It had died once before: in {month(gone)} it was moved away to {s.moves[0][1]}, "
                     f"and in {month(back)} it was brought back.")
    else:
        deprecations = [c for c in s.brushes_with_death if "deprecat" in c.subject.lower()]
        if deprecations:
            parts.append(f"It survived {plural(len(deprecations), 'deprecation')}, the first in {month(deprecations[0])}.")
    parts.append(f"{s.death.author} laid it to rest with the words " + _quoted(one_line(s.death.subject, 160)))
    if s.afterlife:
        parts.append(f"Its body was not buried: it was moved to {s.afterlife}"
                     + (", where it lives on to this day." if s.afterlife_alive else ", though it has since left there too."))
    if s.unfinished_business:
        parts.append("It left unfinished business: " + _quoted(s.unfinished_business[0]))
    if s.successors:
        parts.append(f"It is survived by {people_phrase(s.successors[:3])}.")
    elif s.died_alongside_count:
        parts.append(f"It did not go alone: {plural(s.died_alongside_count, 'other file')} died with it.")
    return " ".join(parts)


def _quoted(text: str) -> str:
    """“Text” closing a sentence, without a doubled full stop."""
    return f"“{text}”" + ("" if text.rstrip().endswith((".", "!", "?", "…")) else ".")


def _sentence(text: str) -> str:
    text = " ".join(text.split()).strip()
    if text and text[-1] not in ".!?…":
        cut = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
        text = text[: cut + 1] if cut > 20 else text + "."
    return text[:1].upper() + text[1:]


# --------------------------------------------------------------------------
# cleaning what the model says

_LABEL = re.compile(r"^(epitaph|tombstone|r\.?i\.?p\.?)\s*\d*\s*[:.-]\s*", re.I)


def clean_epitaph(text: str) -> str:
    junk = "*_#>`\"'“”‘’ -"
    for line in text.splitlines():
        line = re.sub(r"^\s*\d+[.)]\s*", "", line).strip(junk)
        line = _LABEL.sub("", line).strip(junk)
        if line:
            return line[:140]
    return ""


def finish_reply(text: str) -> str:
    """Trim a reply that was cut off mid-sentence back to its last full stop."""
    text = text.strip()
    if not text or text[-1] in ".!?…\"”)*`":
        return text
    cut = max(text.rfind(c) for c in ".!?…")
    return text[: cut + 1] if cut > len(text) // 3 else text


# --------------------------------------------------------------------------
# when no medium answers: the plain stonemason


def plain_epitaph(spirit: Spirit) -> str:
    if spirit.gift and len(spirit.gift) <= 80:
        return spirit.gift
    if spirit.is_binary:
        return f"{spirit.size_bytes} bytes, never a word. Rest now."
    return (f"{plural(spirit.line_count, 'line')} of {spirit.language}. "
            f"{lifespan(spirit.lifespan_days).capitalize()}. Not forgotten.")


def plain_obituary(spirit: Spirit) -> str:
    return obituary(spirit)
