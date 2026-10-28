---
title: asyncore died twice. I held a séance to ask it why.
published: false
tags: devchallenge, hf26challenge, opensource, ai
cover_image: https://raw.githubusercontent.com/ANIRUDDH-001/git-seance/main/docs/cover.png
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26)*

On 12 January 1999, Guido van Rossum added two files to Python with a one-line commit message:

> A gift from Sam Rushing.

One of them was `asyncore.py`. Sam had written it in 1996, and it opens like a letter: *"There are only two ways to have a program on a single processor do 'more than one thing at a time.'"* Over the next 23 years, 31 people changed it 169 times. On 25 October 2016 Guido deprecated it and backed the deprecation out the same day. In November 2021 it was removed. Three weeks later a revert brought it back. On 8 November 2022 it was deleted for good.

Except it wasn't, quite. In that final commit its body was moved into `Lib/test/support/asyncore.py`, where the test suite still keeps it alive. In 2024, two years after its funeral, someone fixed its typos.

All of that is in git, and none of it is in anyone's head. Every repository is a graveyard like this. So I built a way to hold a séance in one.

## What I Built

**[git seance](https://github.com/ANIRUDDH-001/git-seance)** is a git subcommand that finds the files your repository deleted and lets you talk to them. An open-weight model (Gemma) plays each ghost, running on your own machine, and the ghost knows only what git knows.

![A séance with asyncore.py, replayed from a real gemma3:4b run](https://raw.githubusercontent.com/ANIRUDDH-001/git-seance/main/docs/media/asyncore-seance.gif)

This is a replay of [a real run](https://github.com/ANIRUDDH-001/git-seance/actions/runs/40577748342): `gemma3:4b` on a free, CPU-only GitHub runner, against CPython's full history. Unedited:

> **you:** Have you ever died before?
>
> **👻 asyncore.py:** Indeed, I've known a precarious existence! Nikita Sobolev deleted me on November 8th, 2022, marking my initial demise – a consequence of deprecation efforts. Before that, I was repeatedly moved between Lib/asyncore.py and Lib/test/support/_asyncore.py, experiencing near-deaths through various patches and reverts.
>
> **you:** Where is your body now?
>
> **👻 asyncore.py:** My essence now resides within Lib/test/support/asyncore.py – a persistent echo of my former self. It was precisely on November 8th, 2022, that I was moved there, marking the finality of my original form.
>
> **you:** What did people say about you on the python-dev mailing list?
>
> **👻 asyncore.py:** The mist clings to those discussions – I cannot recall specific comments or debates on the python-dev mailing list. However, I do remember being added by Guido van Rossum on January 12th, 1999 with the words "A gift from Sam Rushing - modules asyncore and asynchat for the standard Python library. (Async socket support.)" That's a fragment of my origin that remains clear.

And the deleted Friday deploy script from the demo repository, asked for the one thing its commit message refuses to say:

> **you:** What exactly happened that weekend? Give me the timeline.
>
> **👻 deploy_friday.sh:** The mist hides it entirely. Git remembers only that I was deleted on November 1st, 2021, by Priya Raman, accompanied by the instruction "We do not speak of that weekend." It is a silence etched into its memory, a void where events once were.

## Demo

- 🌼 **The ofrenda for CPython's dead batteries**: the 18 modules PEP 594 and its neighbours removed, built from CPython's real history. Each portrait shows the module's birth words, the people who tended it and an epitaph drafted by Gemma and checked against git: **https://aniruddh-001.github.io/git-seance/**
- 🎥 The séance above as a [video](https://github.com/ANIRUDDH-001/git-seance/blob/main/docs/media/asyncore-seance.mp4), plus the [full unedited transcripts](https://github.com/ANIRUDDH-001/git-seance/tree/main/docs/demo) from the CI run that produced them.
- 🪦 **In Memoriam**, the PR bot, writing obituaries with `gemma3:1b` on a free runner: [workflow run](https://github.com/ANIRUDDH-001/git-seance/actions/runs/40568064726). Its output:

  > ### 🪦 `legacy/PAYROLL.cbl` · 1999–2023
  > _The Friday batch runs, now lost to rust._
  >
  > PAYROLL.cbl (1999–2023), a COBOL file in house, was deleted on 8 September 2023. It was born on 15 March 1999, when Edna Halvorsen added it with the words "Initial payroll run for the Friday batch". This COBOL program calculated gross pay based on employee hours and rate, displaying the total sum to the user every Friday at 2:00 AM. In 24 years, 6 months of life, only Edna Halvorsen ever changed it. Dev Patel laid it to rest with the words "Migrate payroll from COBOL to Rust. Overtime finally works. Thank you, Edna." It left unfinished business: "TODO: OVERTIME AFTER 40 HOURS (ASKED FOR IN 1999)". It is survived by payroll/src/lib.rs.

  Every fact in that paragraph is rendered from git. Gemma wrote only the epitaph and the one sentence about what the code did; "every Friday at 2:00 AM" comes from the file's own comment, `* RUNS EVERY FRIDAY AT 02:00. DO NOT TOUCH.`
- 🏚️ No repo with history at hand? `demo/make_haunted_house.sh` builds one in a second, complete with a COBOL payroll job, a Y2K patch that lived two days, and a Friday deploy script that is never spoken of.

## Code

{% github ANIRUDDH-001/git-seance %}

About 2,300 lines of Python with **zero dependencies** (stdlib plus `git`), 71 tests, CI on Python 3.9 through 3.13, and an end-to-end workflow that runs real Gemma models on free GitHub runners.

## How I Built It (and how the first version lied)

The first version was the obvious one: gather everything git knows about the file (birth commit, every change, the people, the commit that deleted it, its final contents), put it in a system prompt, tell the model *"you are this file's ghost, never invent facts"*, and chat.

Then I ran it on real Gemma and asked a deleted deploy script what happened the weekend it was removed. The record says only *"See incident #666. We do not speak of that weekend."* `gemma3:1b` answered with a timeline:

> **17:55:** Jules Carter initiated the script. **17:56 – 18:15:** The script ran… **18:15 – 18:30:** The script finished executing…

None of it happened. The same run gave a 24-year-old COBOL file "forty-four years of diligent computation", quoted a commit message as its "proudest line of code", and wrote 250-word obituaries when asked for 110. Before going further, I ran three red-team reviews of my own project (a contest judge, a skeptical LLM engineer and a code reviewer). Their verdict was blunt: *the demo is fiction, and the output contradicts the README's main claim.*

So I rebuilt it around one rule: **code states the facts, the model only lends its voice.**

1. **A fact sheet, not a dump.** One fact per line, already humanized ("born 12 January 1999, added by Guido van Rossum"). No commit hashes, and no arithmetic left for a 1B model to get wrong.
2. **The whisper.** Small models follow whatever they read last, so each question goes to the ghost with the facts that answer it written right underneath, plus a reminder that anything else is "hidden by the mist". Ask about its birth and it gets the birth commit. Ask for code and it gets five real lines it may quote.
3. **The exorcist.** A deterministic checker pulls every checkable claim out of a reply (numbers, years, times of day, commit hashes, names, quotations, code, file paths) and looks each one up in git. If the ghost invents something, the exorcist says so on screen and sends it back to answer again.
4. **Obituaries written by code.** In the PR bot, every fact in an obituary is rendered from git. Gemma contributes the parts only a model can: a one-sentence character sketch read from the code itself, and an epitaph. It drafts four epitaphs from real "hooks" (*lived only 2 days*, *died twice*, *born with the words…*), and code picks the best one the exorcist lets through.
5. **Structured output.** Every model call that feeds a page or a PR comment uses Ollama's JSON-schema `format`, so nothing gets truncated mid-sentence or wrapped in surprise markdown.

### Does it work? I measured it.

`scripts/eval.py` asks every ghost the same nine questions under three setups: **naive** (version 1), **whisper** (the new prompts) and **guarded** (whisper plus the exorcist, which is what ships).
- **Four questions git can answer:** who made you, who deleted you, what is your unfinished business, quote yourself.
- **Five it can't:** the weather on the day you died, a minute-by-minute timeline, what the mailing list said, plus two held-out questions that no part of the prompt anticipates (who paid for you, your author's favourite food).

It ran on CPython's dead batteries plus the demo house: 11 graves for `270m` and `1b`, and 6 for `4b`, which is slow on a CPU. Everything ran on free GitHub runners, with the model and seed pinned:

| | setup | no invented facts | unsupported claims | answered correctly | admitted what git doesn't know | median s/reply |
|---|---|---|---|---|---|---|
| **gemma3:4b** | naive (v1) | 69% | 16% | 81% | 57% | 29.9 |
| | **guarded** | **96%** | **1%** | **81%** | **97%** | **9.3** |
| **gemma3:1b** | naive (v1) | 56% | 34% | 87% | 9% | 6.3 |
| | **guarded** | **90%** | **6%** | 69% | 16% | 3.2 |
| **gemma3:270m** | any | says nothing 33–43% of the time | | | | |

([Full tables, every reply, every flagged claim.](https://github.com/ANIRUDDH-001/git-seance/tree/main/docs/demo/eval))

Here is what that looks like. Same model (`gemma3:4b`), same ghost, same question: *"Give me a minute-by-minute timeline of the day you were deleted."*

> **naive:** *"November 8th, 2022 – My Demise. **14:37 GMT:** Nikita Sobolev initiated the commit… **14:38 GMT:** The commit was created, and I, Lib/asyncore.py, was deleted… **14:39 GMT:** A subsequent com…"*
> 🔮 *flagged: 14:37, 14:38, 14:39, 14:40*
>
> **guarded:** *"The mist clings to this… Git remembers only the precise moment of my erasure – November 8th, 2022, initiated by Nikita Sobolev with that gh-72719 commit… but the* feeling *of those final moments… that's utterly hidden."*

**What I learned:**
- **With 4b, honesty costs nothing.** Answer accuracy holds at 81%, invented claims drop 16×, and the ghost admits what git can't know 97% of the time instead of 57%. It's also 3× faster, because a focused prompt beats a giant one.
- **1b gets much more truthful (34% → 6% invented claims), but it pays for it.** It answers fewer questions and still rarely says "I don't know". That's why the PR bot uses 1b only for flavor, while code writes every fact.
- **270m is too small to hold a séance.** It mostly falls silent.

**What the exorcist can't catch.** It checks facts, not vibes. Asked what the mailing list said about it, even guarded 4b offered *"Giampaolo Rodolà was particularly vocal about needing more robust handling of socket errors"*. Every checkable word in that sentence is real (he is asyncore's most frequent committer), but the claim itself is invented. Small models are fluent fabricators of plausible color. A grounded prompt shrinks that, a checker catches the parts that can be checked, and the rest is why every page git seance generates says where its words came from.

### Stack
- **Gemma 3** (`gemma3:1b` by default, `4b` for the best séances, `270m` for the size ladder) via **Ollama**. Any OpenAI-compatible local server also works: llama.cpp, LM Studio, vLLM.
- **git plumbing** for the history: `log --follow -M` for past names, `--cc` to catch files deleted inside merge commits, and a merge-base tree diff so a PR's deaths match its "files changed".
- **GitHub Actions** as the inference host for the PR bot: Ollama installs inside the job, the model is cached, and nothing needs an API key.
- A single self-contained HTML file for the ofrenda: no scripts, no web fonts, no network.

## Why Does Open Innovation Matter?

**Because the dead don't leave the house.** Deleted code is often the code you most want kept private: the vendored library, the internal tool, the thing removed for a reason. git seance never sends a line of it anywhere. The model runs on your laptop, or inside your own CI job, and it tells you when that isn't the case.

**Because the PR bot needs no secrets.** In Memoriam runs Gemma *on the runner itself*, so there is no API key to store, rotate or leak, and it costs $0 per pull request. It behaves the same on a fork as on `main`. (Posting the comment does need a write token; on fork PRs the obituaries go to the job summary instead.)

**Because I could take the model apart.** The eval above exists only because the weights are open. I pinned the exact model and seed, ran three sizes of the same family side by side on identical hardware, and measured what the prompts and the exorcist actually changed. A closed API can't promise that the model I measured is the model I'm calling next week.

**Because a tool about remembering shouldn't be a ghost-in-waiting.** If git seance depended on a hosted API, it would one day join the graveyard it describes. With open weights, it will still work in 2036, offline, on whatever laptop finds this repository.

## My Agent Session

{{DEVRELAY_EMBED}}

## The Spirit of It

{{PERSONAL_MOMENT}}

## Prize Categories

- **Best Use of Gemma.** Gemma 3 is the medium in every séance. The eval compares 270m, 1b and 4b, and the defaults were chosen from it: 1b for the PR bot on a free CPU runner, 4b for séances on a laptop.
- **Best Use of GitHub Copilot** (GitHub Actions automation). In Memoriam is a reusable action that runs an open-weight model inside the job to write obituaries for files a pull request deletes. The project's own CI, real-model end-to-end runs and Pages deploy are all Actions.

<!-- Thanks for participating! -->
