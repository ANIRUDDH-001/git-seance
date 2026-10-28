"""Tombstones and ledgers for the terminal."""

from __future__ import annotations

import os
import shutil
import sys
from typing import Dict, List, Optional

from .history import Grave

STONE_INNER = 21

MARIGOLD = "38;5;214"
GHOST = "38;5;153"
STONE = "38;5;246"
DIM = "2"
BOLD = "1"
RED = "38;5;167"


def use_color(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


class Painter:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __call__(self, text: str, *codes: str) -> str:
        if not self.enabled or not codes or not text:
            return text
        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def _fit(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _center(text: str, width: int = STONE_INNER + 2) -> str:
    return _fit(text, width).center(width)


def tombstone(grave: Grave, lines: Optional[int]) -> List[List[tuple]]:
    """A stone as rows of (plain_text, style) segments."""
    born = grave.birth.date.year if grave.birth else "?"
    died = grave.death.date.year
    span = f"{born} – {died}" if born != died else f"{died}"
    size = "binary" if lines is None else f"{lines} line{'s' if lines != 1 else ''}"
    w = STONE_INNER
    killer = grave.death.author.strip() or "?"
    rows = [
        [("  ." + "-" * (w - 2) + ".", STONE)],
        [(" /" + " " * w + "\\", STONE)],
        [("|", STONE), (_center("R . I . P"), BOLD), ("|", STONE)],
        [("|" + " " * (w + 2) + "|", STONE)],
        [("|", STONE), (_center(grave.name), MARIGOLD), ("|", STONE)],
        [("|", STONE), (_center(span), None), ("|", STONE)],
        [("|", STONE), (_center(size), DIM), ("|", STONE)],
        [("|", STONE), (_center("by " + killer), DIM), ("|", STONE)],
        [("|" + "_" * (w + 2) + "|", STONE)],
    ]
    return rows


def stones_row(graves: List[Grave], counts: Dict[str, Optional[int]], paint: Painter, width: int) -> str:
    stone_w = STONE_INNER + 5
    per_row = max(1, (width - 2) // stone_w)
    out = []
    for i in range(0, len(graves), per_row):
        batch = graves[i:i + per_row]
        stones = [tombstone(g, counts.get(g.path)) for g in batch]
        for r in range(len(stones[0])):
            line = "  "
            for stone in stones:
                seg = "".join(paint(text, style) if style else text for text, style in stone[r])
                plain_len = sum(len(text) for text, _ in stone[r])
                line += seg + " " * (stone_w - plain_len)
            out.append(line.rstrip())
        grass = ("\\|/,'\"" * (stone_w * len(batch)))[: stone_w * len(batch)]
        out.append("  " + paint(grass, "38;5;64"))
        out.append("")
    return "\n".join(out)


def ledger(graves: List[Grave], counts: Dict[str, Optional[int]], paint: Painter, width: int) -> str:
    head = f"  {'DIED':<10}  {'BORN':<10}  {'LINES':>6}  {'PATH':<34}  CAUSE OF DEATH"
    out = [paint(head, DIM)]
    for g in graves:
        lines = counts.get(g.path)
        born = g.birth.date.strftime("%Y-%m-%d") if g.birth else "?"
        path = _fit(g.path, 34)
        prefix = f"  {g.death.date.strftime('%Y-%m-%d'):<10}  {born:<10}  {('bin' if lines is None else str(lines)):>6}  "
        cause_room = max(10, width - len(prefix) - 36)
        cause = _fit(f"{g.death.subject} ({g.death.short}, {g.death.author})", cause_room)
        out.append(prefix + paint(f"{path:<34}", MARIGOLD) + "  " + paint(cause, DIM))
    return "\n".join(out)


def terminal_width() -> int:
    return max(60, min(shutil.get_terminal_size((100, 24)).columns, 160))
