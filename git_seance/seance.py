"""A séance: the medium (model), the rites (prompts) and the exorcist (checks)
working together on one spirit.

Shared by the CLI, the GitHub Action and the eval, so all three measure and
ship exactly the same behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from . import rites
from .exorcist import Exorcist, Verdict, describe
from .history import Spirit
from .medium import Medium, SpiritsSilent

HISTORY_BUDGET = 9000   # characters of conversation kept after the system prompt


@dataclass
class Reply:
    text: str
    verdict: Verdict
    corrected_from: Optional[str] = None   # the first answer, if the exorcist sent it back
    seconds: float = 0.0


class Seance:
    def __init__(self, spirit: Spirit, medium: Optional[Medium], strict: bool = True):
        self.spirit = spirit
        self.medium = medium
        self.strict = strict
        self.exorcist = Exorcist(spirit, rites.record(spirit))
        self.messages: List[dict] = [{"role": "system", "content": rites.ghost_system(spirit)}]

    # ------------------------------------------------------------------
    # conversation

    def ask(self, question: str, on_token: Optional[Callable[[str], None]] = None,
            on_correction: Optional[Callable[[Verdict], None]] = None) -> Reply:
        """Ask the ghost something. Facts that answer it are whispered right
        after the question; if the exorcist finds invented facts in the answer,
        the ghost is sent back once to answer again."""
        if self.medium is None:
            raise SpiritsSilent("No medium is present; a séance needs a model.")
        self.messages.append({"role": "user", "content": rites.whisper(self.spirit, question)})
        try:
            text = rites.finish_reply(self.medium.speak(self._window(), on_token=on_token,
                                                        temperature=0.5, max_tokens=220))
        except SpiritsSilent:
            self.messages.pop()
            raise
        seconds = self.medium.last_stats.get("seconds", 0.0)
        verdict = self.exorcist.judge(text)
        first = None
        if self.strict and not verdict.clean:
            if on_correction:
                on_correction(verdict)
            first = text
            self.messages.append({"role": "assistant", "content": text})
            self.messages.append({"role": "user", "content": (
                f"(The medium frowns. Git does not remember {describe(verdict.unsupported)}. "
                "Answer the question again in two or three sentences, using only what git remembers. "
                "Where git is silent, say the mist hides it.)")})
            try:
                text = rites.finish_reply(self.medium.speak(self._window(), on_token=on_token,
                                                            temperature=0.3, max_tokens=200))
            finally:
                # forget the false answer and the scolding; keep the corrected answer
                del self.messages[-2:]
            seconds += self.medium.last_stats.get("seconds", 0.0)
            verdict = self.exorcist.judge(text)
        self.messages.append({"role": "assistant", "content": text})
        return Reply(text, verdict, corrected_from=first, seconds=seconds)

    def _window(self) -> List[dict]:
        """System prompt + the summoning + as many recent turns as fit."""
        system, rest = self.messages[:1], self.messages[1:]
        kept: List[dict] = []
        used = 0
        for msg in reversed(rest[2:]):
            used += len(msg["content"])
            if used > HISTORY_BUDGET:
                break
            kept.append(msg)
        kept.reverse()
        return system + rest[:2] + kept if len(rest) > 2 else system + rest

    # ------------------------------------------------------------------
    # the written rites

    def epitaph(self, already: List[str] = ()) -> str:
        """One line for the stone: the model drafts four, code picks the best
        one that the exorcist passes; the gift (birth words) if none survive."""
        if self.medium is not None:
            for attempt in range(2):
                try:
                    data = self.medium.speak_json(rites.epitaph_messages(self.spirit), rites.EPITAPH_SCHEMA,
                                                  temperature=0.9 if attempt == 0 else 0.7, max_tokens=160)
                except SpiritsSilent:
                    if attempt:
                        raise
                    continue
                cands = data.get("epitaphs") or []
                if isinstance(cands, str):
                    cands = [cands]
                best = rites.choose_epitaph(list(cands), self.spirit,
                                            lambda t: len(self.exorcist.judge(t).unsupported), already)
                if best:
                    return best
        return rites.plain_epitaph(self.spirit)

    def character(self) -> Optional[str]:
        """The model's sketch of what the file was like, or None if every
        attempt invented something."""
        if self.medium is None:
            return None
        for attempt in range(3):
            try:
                data = self.medium.speak_json(rites.character_messages(self.spirit), rites.CHARACTER_SCHEMA,
                                              temperature=0.4 + 0.2 * attempt, max_tokens=120)
            except SpiritsSilent:
                if attempt == 2:
                    raise
                continue
            text = " ".join(str(data.get("character", "")).split())
            if 20 <= len(text) <= 400 and self.exorcist.judge(text).clean and "survived" not in text.lower():
                return text
        return None

    def obituary(self) -> str:
        return rites.obituary(self.spirit, self.character())
