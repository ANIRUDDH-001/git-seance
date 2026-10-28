# git-seance 🕯️

**Talk to the ghosts of your deleted code.**

On 12 January 1999, Guido van Rossum added `asyncore.py` to Python with the words
*"A gift from Sam Rushing."* Over 23 years, 31 people changed it 169 times. It was
deprecated and pardoned on the same afternoon in 2016, removed in November 2021,
brought back by a revert three weeks later, and deleted for good in 2022. Even
then its body was only moved into `Lib/test/support/`, where it still lives.

Git remembers all of that. `git seance` lets the file tell you itself:

![A séance with asyncore.py, replayed from a real gemma3:4b run](docs/media/asyncore-seance.gif)

> **you:** What did people say about you on the python-dev mailing list?
>
> **👻 asyncore.py:** The mist clings to those discussions – I cannot recall specific comments or debates on the python-dev mailing list. However, I do remember being added by Guido van Rossum on January 12th, 1999 with the words "A gift from Sam Rushing…" That's a fragment of my origin that remains clear.

<sub>Unedited output of `gemma3:4b` on a free CPU-only GitHub runner against CPython's real history.
[Full transcripts](docs/demo/) · [how it's measured](#how-the-ghosts-stay-honest)</sub>

The ghost is played by **Gemma**, an open-weight model running **on your own
machine** through [Ollama](https://ollama.com). It only knows what git knows,
and a built-in **exorcist** checks every fact it states against the history.
There is no API key and no account, and nothing leaves your machine.

[![CI](https://github.com/ANIRUDDH-001/git-seance/actions/workflows/ci.yml/badge.svg)](https://github.com/ANIRUDDH-001/git-seance/actions/workflows/ci.yml)
[![Séance (real Gemma)](https://github.com/ANIRUDDH-001/git-seance/actions/workflows/seance-e2e.yml/badge.svg)](https://github.com/ANIRUDDH-001/git-seance/actions/workflows/seance-e2e.yml)

🌼 **[See the ofrenda for CPython's dead batteries →](https://aniruddh-001.github.io/git-seance/)**

---

## The rites

| Command | What happens |
|---|---|
| `git seance graveyard [path…]` | Raises a tombstone for every file that died and stayed dead. Renamed files are *reincarnated*, not dead, and don't count. |
| `git seance summon <path>` | A séance. Chat with the deleted file, which answers in the first person from its real history. `--ask "…"` for one-shot questions. |
| `git seance epitaph <path>` | One line for the tombstone, drafted by the model from real facts and checked by the exorcist. |
| `git seance obituary <path>` | An obituary: every fact rendered from git, plus a character sketch the model reads from the code. |
| `git seance ofrenda` | A Día de los Muertos **ofrenda** page: one self-contained HTML file honoring your departed files. |
| `git seance resurrect <path>` | Brings the file back into your working tree, exactly as it was before it died. |
| `git seance record <path>` | Shows *exactly* what the model is told. No hidden prompts. |
| `git seance obituaries BASE..HEAD` | Obituaries for everything a branch deletes. Used by the GitHub Action. |

Inside a séance: `/epitaph`, `/obituary`, `/record`, `/resurrect`, `/bye`.

## Quick start (about 5 minutes, all free)

```bash
# 1. a local, open-weight medium
curl -fsSL https://ollama.com/install.sh | sh       # macOS/Windows: https://ollama.com/download
ollama pull gemma3:4b      # 3.3 GB, the séance default; ~8 GB RAM is plenty
ollama pull gemma3:1b      # 815 MB, for epitaphs, obituaries and small machines

# 2. git-seance (pure Python standard library, no dependencies)
pipx install git+https://github.com/ANIRUDDH-001/git-seance
#   or: pip install git+https://github.com/ANIRUDDH-001/git-seance

# 3. go haunt something
cd your-repo
git seance graveyard
git seance summon path/to/some/deleted_file.py
```

Because the executable is called `git-seance`, git picks it up as a
subcommand. `python -m git_seance` works too. For help, use `git seance -h`:
git turns `--help` into a man-page lookup.

**No repository with enough history?** Build a haunted house in one line:

```bash
demo/make_haunted_house.sh /tmp/haunted-house && cd /tmp/haunted-house
git seance graveyard
git seance summon legacy/PAYROLL.cbl --ask "Who was Edna to you?"
```

## How the ghosts stay honest

A small model told to "be a ghost" will happily invent a tragic backstory.
The first version of this tool did exactly that: asked what happened the weekend
a deploy script was deleted, `gemma3:1b` produced a minute-by-minute timeline
that git knows nothing about. The design that came out of fixing it:

- **Code states the facts; the model lends its voice.** The ghost gets a humanized
  fact sheet built from git: birth commit, the people who changed it, brushes with
  death, moves and afterlives, the commit that deleted it, unfinished `TODO`s, and its
  last contents. There are no hashes and nothing to compute.
- **The whisper.** Each question is sent with the facts that answer it written right
  beneath it, because small models follow what they read last.
- **The exorcist.** Every reply is scanned for checkable claims: numbers, years,
  times of day, commit hashes, names, quotes, code and paths. Each is looked up in
  git. A ghost that invents something is told so, visibly, and sent back to answer again.
- **Obituaries are written by code.** The model contributes a character sketch read
  from the file's code, and four epitaph drafts built on real "hooks", from which
  code picks the best one the exorcist accepts. Both use JSON-schema output.

`git seance record <path>` prints exactly what the model is told. `scripts/eval.py`
measures how often each setup invents facts; see [the results](docs/demo/eval/README.md).

## Swap the medium

Any model, any local server. Nothing is hardwired.

```bash
git seance summon x.py --model gemma3:4b                 # a bigger Gemma
SEANCE_MODEL=gemma3:12b git seance ofrenda               # or set it once

# any OpenAI-compatible local server: llama.cpp, LM Studio, vLLM, LocalAI…
llama-server -m gemma-3-4b-it-Q4_K_M.gguf --port 8080 &
git seance summon x.py --backend openai --host http://localhost:8080 --model gemma-3-4b-it
```

| Setting | Flag | Environment | Default |
|---|---|---|---|
| model | `--model` | `SEANCE_MODEL` | `gemma3:4b` for `summon`, `gemma3:1b` for the rest |
| server | `--host` | `SEANCE_HOST`, `OLLAMA_HOST` | `http://localhost:11434` |
| dialect | `--backend` | `SEANCE_BACKEND` | `ollama` (or `openai`) |

## The ofrenda

On Día de los Muertos, families build an *ofrenda*: an altar with photographs,
candles, marigolds whose scent guides the dead home, and the favorite foods of
those they remember. `git seance ofrenda` builds one for your codebase. Each
departed file gets a portrait with its years, an epitaph written in its own
voice, the people who tended it, its favorite offerings (imports), its last
words and its unfinished business, under papel picado and candlelight.

```bash
git seance ofrenda -o ofrenda.html                      # the 12 most recently departed
git seance ofrenda src/ legacy/ -n 20                   # only some paths
git seance ofrenda --only Lib/asyncore.py --only Lib/imp.py --title "Dead batteries"
```

The page is a single HTML file with no scripts, fonts or network requests.
Open it from disk, or put it on GitHub Pages.

## In Memoriam: a GitHub Action

When a pull request deletes files, the action writes their obituaries **with
Gemma running inside the job**, on GitHub's free runners, and posts them as a
comment (updated in place on each push). There are no API keys to manage, and
the code never leaves the runner.

```yaml
# .github/workflows/in-memoriam.yml
name: In Memoriam
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  obituaries:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # the dead live in history
      - uses: ANIRUDDH-001/git-seance@main
        with:
          model: gemma3:1b        # cached between runs
```

If nothing was deleted, the action exits before installing anything. If the
model can't be reached, the obituaries are still written from git facts alone,
so the job doesn't fail. File names, commit messages and model output are escaped
before posting: no mentions, links or HTML get through. On pull requests from
forks GitHub gives the job a read-only token, so the obituaries go to the job
summary instead of a comment.

## Privacy

- By default everything runs locally: git plumbing plus HTTP to Ollama on `localhost`.
- The only network request goes to the model server you configure. If that server is
  not on your machine (another `--host`, or an Ollama `-cloud` model), git-seance says
  so before sending anything.
- Zero third-party Python dependencies, about 2,300 lines you can read in an evening.

## Development

```bash
python -m pip install pytest
python -m pytest -q              # fake Ollama/OpenAI servers, no model needed
```

`.github/workflows/seance-e2e.yml` runs real Gemma models (270m, 1b, 4b) on
CPU-only GitHub runners. It runs the eval, holds séances with CPython's dead
batteries (pinned to a fixed CPython commit), tests the In Memoriam action end
to end. `archive.yml` copies a run's real outputs into [`docs/demo`](docs/demo/) and
`pages.yml` publishes them to GitHub Pages.

## License

MIT
