#!/usr/bin/env python3
"""Turn a séance transcript into an animated terminal page (for recording a demo).

Lines starting with "$ " are typed as commands, "you: " lines are typed as
questions, "👻 " lines stream like model output, "🔮" lines appear dimmed,
everything else appears at once. Usage: make_cast.py transcript.txt out.html
"""
import html
import json
import sys

KIND = [("$ ", "cmd"), ("you: ", "you"), ("👻", "ghost"), ("   🔮", "exorcist"), ("🔮", "exorcist"),
        ("🕯", "dim"), ("   medium", "dim"), ("#", "comment")]


def steps(text):
    out = []
    for line in text.splitlines():
        kind = next((k for prefix, k in KIND if line.startswith(prefix)), "out")
        out.append({"kind": kind, "text": line})
    return out


PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:#120a1f;}
.term{box-sizing:border-box;width:1000px;height:620px;margin:0;padding:22px 26px;background:#140b24;color:#e9e1f7;
 font:15.5px/1.5 "DejaVu Sans Mono",ui-monospace,Menlo,monospace;overflow:hidden;white-space:pre-wrap;word-break:break-word;}
.bar{height:30px;background:#23123d;display:flex;align-items:center;gap:8px;padding:0 14px;width:1000px;box-sizing:border-box}
.bar i{width:12px;height:12px;border-radius:50%;display:inline-block}.bar span{color:#cbb9e8;font:13px ui-sans-serif,system-ui;margin-left:10px}
.cmd{color:#ffd166}.cmd b{color:#7bd389;font-weight:400}.you{color:#9c8fb8}.ghost{color:#b9d7ff}.ghost em{color:#ff9f1c;font-style:normal}
.exorcist{color:#c792ea}.dim{color:#8a7ca8}.comment{color:#6c5f86;font-style:italic}.out{color:#e9e1f7}
.cursor{display:inline-block;width:9px;height:18px;background:#ffd166;vertical-align:-3px;animation:b 1s steps(1) infinite}
@keyframes b{50%{opacity:0}}
</style></head><body><div class="bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i><span>git seance · __TITLE__</span></div>
<div class="term" id="t"></div><script>
const steps = __STEPS__;
const t = document.getElementById('t');
const sleep = ms => new Promise(r => setTimeout(r, ms));
function line(kind){ const d=document.createElement('div'); d.className=kind; t.appendChild(d); return d; }
function scroll(){ while (t.scrollHeight > t.clientHeight && t.firstChild) t.removeChild(t.firstChild); }
const cur = document.createElement('span'); cur.className='cursor';
(async () => {
  await sleep(600);
  for (const s of steps) {
    const d = line(s.kind);
    if (s.kind === 'cmd' || s.kind === 'you') {
      const prefix = s.kind === 'cmd' ? '$ ' : 'you: ';
      d.textContent = prefix; d.appendChild(cur); scroll(); await sleep(450);
      const body = s.text.slice(prefix.length);
      for (const ch of body) { cur.before(ch); scroll(); await sleep(28 + Math.random()*40); }
      await sleep(350); cur.remove();
    } else if (s.kind === 'ghost') {
      const m = s.text.match(/^(👻 [^:]+: )(.*)$/);
      const head = document.createElement('em'); head.textContent = m ? m[1] : ''; d.appendChild(head);
      const words = (m ? m[2] : s.text).split(/(\\s+)/);
      await sleep(700);
      for (const w of words) { d.appendChild(document.createTextNode(w)); scroll(); await sleep(w.trim() ? 95 : 0); }
      await sleep(500);
    } else {
      d.textContent = s.text || ' '; scroll(); await sleep(s.text ? 140 : 60);
    }
  }
  await sleep(2500); document.title = 'done';
})();
</script></body></html>"""


def main():
    src, dst = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "a séance"
    with open(src, encoding="utf-8") as fh:
        data = steps(fh.read())
    page = PAGE.replace("__STEPS__", json.dumps(data, ensure_ascii=False)).replace("__TITLE__", html.escape(title))
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(page)


if __name__ == "__main__":
    main()
