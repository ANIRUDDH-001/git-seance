"""A Día de los Muertos ofrenda for departed source files.

On an ofrenda, families place photographs, candles, marigolds (cempasúchil,
whose scent guides the dead home) and the favorite foods of those they
remember. Here each departed file gets a portrait with its years, its epitaph,
the hands that tended it, its favorite offerings (its imports), its last words
and the business it left unfinished.

One self-contained HTML file: no scripts, no fonts, no network. It works from
a USB stick at a candlelit desk, and on GitHub Pages.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from . import rites
from .history import Spirit

_TRIVIAL_LAST_LINES = {"", "}", "};", ")", ");", "]", "end", "fi", "esac", "*/", "\"\"\"", "'''", "</html>", "})", "});"}


def last_line(spirit: Spirit) -> str:
    for line in reversed((spirit.last_words or "").splitlines()):
        s = line.strip()
        if s not in _TRIVIAL_LAST_LINES and not s.startswith(("#", "//")):
            return s[:90] + ("…" if len(s) > 90 else "")
    return ""


def _e(text) -> str:
    return html.escape(str(text), quote=True)


_FLAG_COLORS = ["#e4007c", "#ff8c00", "#7b2cbf", "#00a6a6", "#ffd23f", "#2ec4b6", "#ff5d8f"]

# Each banner flag is a rectangle with shapes punched out (evenodd fill), like
# the tissue paper of papel picado.
_CUTOUTS = [
    "M30 22a8 8 0 1 0 0.1 0Z M14 46l6-6 6 6-6 6Z M34 46l6-6 6 6-6 6Z M10 14h4v4h-4Z M46 14h4v4h-4Z",
    "M30 14l10 16-10 16-10-16Z M12 50a4 4 0 1 0 0.1 0Z M48 50a4 4 0 1 0 0.1 0Z M16 18h3v3h-3Z M41 18h3v3h-3Z",
    "M22 20a5 5 0 1 0 0.1 0Z M38 20a5 5 0 1 0 0.1 0Z M24 34h12l-6 8Z M18 48h24v3H18Z",
]


def _banner(count: int = 9) -> str:
    flags = []
    for i in range(count):
        color = _FLAG_COLORS[i % len(_FLAG_COLORS)]
        cut = _CUTOUTS[i % len(_CUTOUTS)]
        flags.append(
            f'<svg class="flag" viewBox="0 0 60 64" aria-hidden="true" style="--d:{(i % 4) * 0.4:.1f}s">'
            f'<path fill="{color}" fill-rule="evenodd" d="M0 0H60V56l-5 8-5-8-5 8-5-8-5 8-5-8-5 8-5-8-5 8-5-8-5 8-5-8Z {cut}"/>'
            "</svg>"
        )
    return '<div class="banner">' + "".join(flags) + "</div>"


def _portrait(spirit: Spirit, epitaph: str) -> str:
    s = spirit
    family = ", ".join(name for name, _ in s.family[:3]) or "unknown hands"
    if len(s.family) > 3:
        family += f" and {len(s.family) - 3} more"
    parts = [
        '<article class="portrait">',
        '<div class="frame">',
        f'<p class="lang">{_e(s.language)}</p>',
        f'<h3 title="{_e(s.path)}">{_e(s.name)}</h3>',
        f'<p class="dir">{_e(s.path.rsplit("/", 1)[0] + "/" if "/" in s.path else "/")}</p>',
        f'<p class="years">{_e(rites.years(s))}</p>',
        "</div>",
        (f'<p class="gift"><span>born with the words</span>“{_e(rites.one_line(s.gift, 140))}”'
         f'<span>— {_e(s.birth.author)}, {_e(rites.long_date(s.birth))}</span></p>' if s.birth and s.gift else ""),
        (f'<blockquote>{_e(epitaph)}</blockquote>' if epitaph and epitaph != s.gift else ""),
        "<dl>",
        f"<dt>Tended by</dt><dd>{_e(family)}</dd>",
        f"<dt>Lived</dt><dd>{_e(rites.lifespan(s.lifespan_days))}, {_e(rites.plural(len(s.life), 'commit'))}</dd>",
    ]
    if len(s.moves) >= 2 and s.moves[-1][1] == s.path:
        parts.append(f"<dt>Died once before</dt><dd>moved away {_e(rites.month(s.moves[0][2]))}, "
                     f"brought back {_e(rites.month(s.moves[-1][2]))}</dd>")
    if s.afterlife:
        parts.append(f"<dt>Afterlife</dt><dd>its body lives on in <code>{_e(s.afterlife)}</code></dd>"
                     if s.afterlife_alive else f"<dt>Afterlife</dt><dd>moved to <code>{_e(s.afterlife)}</code></dd>")
    parts.append(f'<dt>Laid to rest</dt><dd>by {_e(s.death.author)}: {_e(s.death.subject)} '
                 f'<span class="sha">{_e(s.death.short)}</span></dd>')
    if s.favorite_imports:
        foods = " ".join(f"<code>{_e(i)}</code>" for i in s.favorite_imports[:5])
        parts.append(f"<dt>Favorite offerings</dt><dd>{foods}</dd>")
    words = last_line(s)
    if words:
        parts.append(f"<dt>Last words</dt><dd><code>{_e(words)}</code></dd>")
    if s.unfinished_business:
        parts.append(f"<dt>Unfinished business</dt><dd>{_e(s.unfinished_business[0])}</dd>")
    parts += ["</dl>", '<div class="candle" aria-hidden="true"><i></i></div>', "</article>"]
    return "".join(parts)


def _tiers(items: List[str]) -> List[List[str]]:
    """Three levels, like a traditional ofrenda: heaven, earth, underworld."""
    n = len(items)
    if n <= 3:
        return [items]
    top = max(1, n // 4)
    mid = max(1, (n - top) // 2)
    return [items[:top], items[top:top + mid], items[top + mid:]]


def build_ofrenda(title: str, offerings: List[Tuple[Spirit, str]], model: Optional[str] = None,
                  local: bool = True) -> str:
    portraits = [_portrait(s, ep) for s, ep in offerings]
    tiers = "".join(
        f'<section class="tier tier-{i}">' + "".join(row) + "</section>"
        for i, row in enumerate(_tiers(portraits))
    )
    lines = sum(s.line_count for s, _ in offerings)
    hands = len({name for s, _ in offerings for name, _ in s.family})
    if model and local:
        voice = (f"Epitaphs drafted by <code>{_e(model)}</code>, an open-weight model running on this machine, "
                 "and checked against git history. No code left the machine.")
    elif model:
        voice = f"Epitaphs drafted by <code>{_e(model)}</code> and checked against git history."
    else:
        voice = "Each stone carries the words its file was born with."
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    petals = "".join(
        f'<span class="petal" style="left:{(i * 37) % 100}%;--t:{9 + (i * 7) % 8}s;--d:{(i * 1.3) % 9:.1f}s"></span>'
        for i in range(18)
    )
    return _TEMPLATE.format(
        title=_e(title),
        banner=_banner(),
        tiers=tiers,
        count=len(offerings),
        lines=f"{lines:,}",
        hands=hands,
        voice=voice,
        stamp=stamp,
        petals=petals,
    )


_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ofrenda · {title}</title>
<meta name="description" content="A Día de los Muertos ofrenda for the files deleted from {title}, made with git-seance.">
<style>
:root {{
  --night: #140b24; --night-2: #23123d; --paper: #fff7e8; --ink: #2a1a12;
  --marigold: #ff9f1c; --marigold-deep: #e86a00; --rose: #e4007c; --wood: #5b3218; --wood-light: #7a4524;
  --muted: #cbb9e8; --candle: #fff3d6;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; }}
body {{
  background: radial-gradient(1200px 600px at 50% -10%, #3a1d63 0%, var(--night) 60%) fixed, var(--night);
  color: var(--paper); font: 16px/1.5 ui-serif, Georgia, "Times New Roman", serif; min-height: 100vh; overflow-x: hidden;
}}
.banner {{ display: flex; justify-content: center; gap: 6px; padding: 0 8px; position: relative; }}
.banner::before {{ content: ""; position: absolute; left: 0; right: 0; top: 2px; height: 2px; background: #d9c7a3; opacity: .6; }}
.flag {{ width: clamp(34px, 9vw, 72px); height: auto; transform-origin: top center; animation: sway 5s ease-in-out infinite; animation-delay: var(--d); filter: drop-shadow(0 4px 6px rgba(0,0,0,.35)); }}
@keyframes sway {{ 0%,100% {{ transform: rotate(-2deg); }} 50% {{ transform: rotate(2deg); }} }}
header {{ text-align: center; padding: 28px 16px 8px; }}
header .kicker {{ letter-spacing: .3em; text-transform: uppercase; color: var(--marigold); font: 600 12px/1 ui-sans-serif, system-ui, sans-serif; margin: 0 0 12px; }}
h1 {{ font-size: clamp(32px, 6vw, 60px); margin: 0; font-weight: 600; text-shadow: 0 0 24px rgba(255,159,28,.35); }}
header p.sub {{ color: var(--muted); font-style: italic; margin: 10px auto 0; max-width: 36em; }}
.stats {{ display: flex; justify-content: center; flex-wrap: wrap; gap: 8px 28px; margin: 18px 0 0; font: 14px/1.3 ui-sans-serif, system-ui, sans-serif; color: var(--muted); }}
.stats b {{ color: var(--paper); font-size: 20px; display: block; font-family: ui-serif, Georgia, serif; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 24px 16px 40px; }}
.tier {{
  display: flex; flex-wrap: wrap; justify-content: center; gap: 22px; padding: 26px 18px 30px; margin: 0 auto 0;
  border-bottom: 18px solid var(--wood); position: relative;
  background: linear-gradient(to bottom, transparent 70%, rgba(0,0,0,.25));
  box-shadow: 0 14px 0 -4px var(--wood-light), 0 24px 30px rgba(0,0,0,.45);
}}
.tier-0 {{ max-width: 70%; }} .tier-1 {{ max-width: 86%; }} .tier-2 {{ max-width: 100%; }}
.tier + .tier {{ margin-top: 26px; }}
.tier::after {{ /* marigold garland along each shelf */
  content: ""; position: absolute; left: 0; right: 0; bottom: -14px; height: 12px;
  background: radial-gradient(circle at 6px 6px, var(--marigold) 0 5px, var(--marigold-deep) 5.5px 6px, transparent 6.5px) 0 0 / 14px 12px repeat-x;
}}
.portrait {{
  width: 250px; background: var(--paper); color: var(--ink); border-radius: 6px; padding: 14px 14px 46px; position: relative;
  box-shadow: 0 10px 24px rgba(0,0,0,.45), inset 0 0 0 1px rgba(0,0,0,.08); transform: rotate(var(--r, 0deg));
}}
.portrait:nth-child(3n+1) {{ --r: -1.2deg; }} .portrait:nth-child(3n+2) {{ --r: 0.8deg; }} .portrait:nth-child(3n) {{ --r: -0.4deg; }}
.frame {{
  border: 6px double var(--marigold-deep); border-radius: 50% 50% 8px 8px / 30% 30% 8px 8px; padding: 22px 10px 12px; text-align: center;
  background: radial-gradient(circle at 50% 30%, #fff 0%, #f4e7cf 70%);
}}
.frame .lang {{ font: 600 10px/1 ui-sans-serif, system-ui, sans-serif; letter-spacing: .2em; text-transform: uppercase; color: var(--rose); margin: 0 0 8px; }}
.frame h3 {{ margin: 0; font-size: 19px; word-break: break-word; }}
.frame .dir {{ margin: 2px 0 0; font: 12px/1.3 ui-monospace, SFMono-Regular, Menlo, monospace; color: #7d6650; word-break: break-all; }}
.frame .years {{ margin: 8px 0 0; font-size: 15px; letter-spacing: .08em; }}
.gift {{ margin: 12px 2px 0; text-align: center; font-size: 13.5px; line-height: 1.4; color: #5a3a26; }}
.gift span {{ display: block; font: 600 9.5px/1.6 ui-sans-serif, system-ui, sans-serif; letter-spacing: .14em; text-transform: uppercase; color: #9a7a5f; }}
.gift span:last-child {{ text-transform: none; letter-spacing: 0; font-weight: 400; font-size: 11px; }}
blockquote {{ margin: 14px 4px 10px; font-style: italic; font-size: 15px; text-align: center; color: #4b2d1e; }}
blockquote::before {{ content: "“"; }} blockquote::after {{ content: "”"; }}
dl {{ margin: 0; font: 12.5px/1.4 ui-sans-serif, system-ui, sans-serif; }}
dt {{ color: var(--marigold-deep); font-weight: 700; text-transform: uppercase; letter-spacing: .08em; font-size: 10px; margin-top: 8px; }}
dd {{ margin: 1px 0 0; overflow-wrap: anywhere; }}
code {{ font: 11.5px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; background: #f3e5c9; padding: 0 4px; border-radius: 3px; }}
.sha {{ font: 11px ui-monospace, monospace; color: #8a7461; }}
.candle {{ position: absolute; left: 50%; bottom: -10px; width: 18px; height: 40px; margin-left: -9px; background: linear-gradient(90deg, #f6e7c7, var(--candle) 40%, #e9d6ae); border-radius: 3px; }}
.candle i {{ position: absolute; left: 50%; top: -20px; width: 12px; height: 20px; margin-left: -6px; border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
  background: radial-gradient(circle at 50% 75%, #fff 0 20%, #ffd166 35%, #ff7b00 70%, transparent 72%); filter: blur(.3px);
  box-shadow: 0 0 18px 6px rgba(255,170,60,.45); animation: flicker 1.8s ease-in-out infinite alternate; transform-origin: 50% 100%; }}
@keyframes flicker {{ 0% {{ transform: scale(1) rotate(-2deg); opacity: .95; }} 40% {{ transform: scale(1.08,.94) rotate(2deg); }} 100% {{ transform: scale(.94,1.06) rotate(-1deg); opacity: 1; }} }}
.petal {{ position: fixed; top: -20px; width: 10px; height: 10px; border-radius: 60% 0 60% 0; background: var(--marigold); opacity: .8;
  animation: fall var(--t) linear infinite; animation-delay: var(--d); pointer-events: none; }}
@keyframes fall {{ to {{ transform: translateY(110vh) rotate(540deg); }} }}
footer {{ text-align: center; color: var(--muted); font: 13px/1.6 ui-sans-serif, system-ui, sans-serif; padding: 10px 16px 40px; max-width: 46em; margin: 0 auto; }}
footer a {{ color: var(--marigold); }}
footer code {{ background: rgba(255,255,255,.08); color: var(--paper); }}
@media (max-width: 640px) {{ .tier-0, .tier-1, .tier-2 {{ max-width: 100%; }} .portrait {{ width: 100%; max-width: 320px; }} }}
@media (prefers-reduced-motion: reduce) {{ .flag, .candle i, .petal {{ animation: none; }} .petal {{ display: none; }} }}
</style>
</head>
<body>
{banner}
<header>
  <p class="kicker">Día de los Muertos · Ofrenda</p>
  <h1>{title}</h1>
  <p class="sub">Every deleted file was a gift from someone. For the files we let go, and for the hands that made them: what is remembered never fully dies.</p>
  <div class="stats"><span><b>{count}</b>departed files</span><span><b>{lines}</b>lines laid to rest</span><span><b>{hands}</b>people who tended them</span></div>
</header>
<main>
{tiers}
</main>
<footer>
  <p>{voice}</p>
  <p>Built {stamp} with <a href="https://github.com/ANIRUDDH-001/git-seance">git-seance</a>. Summon any of them: <code>git seance summon &lt;path&gt;</code></p>
</footer>
{petals}
</body>
</html>
"""
