import os
import subprocess
import sys

from git_seance.cli import main


def test_graveyard(haunted_house, capsys):
    assert main(["-C", haunted_house, "graveyard"]) == 0
    out = capsys.readouterr().out
    assert "R . I . P" in out
    assert "fax_gateway.py" in out and "PAYROLL.cbl" in out
    assert "5 souls departed" in out
    assert "\x1b[" not in out  # NO_COLOR respected


def test_record_shows_exact_prompt(haunted_house, capsys):
    assert main(["-C", haunted_house, "record", "lib/leftpad.js"]) == 0
    out = capsys.readouterr().out
    assert "Replace leftpad with String.prototype.padStart" in out
    assert "function leftpad" in out


def test_summon_one_shot(haunted_house, fake_ollama, capsys):
    rc = main(["-C", haunted_house, "summon", "src/fax_gateway.py", "--host", fake_ollama.url,
               "--ask", "Who killed you?", "--ask", "Any regrets?"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.count("fax_gateway.py: I was the fax gateway") == 2
    msgs = fake_ollama.requests[1]["body"]["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    assert "Dev Patel" in msgs[0]["content"]
    assert fake_ollama.requests[0]["body"]["model"] == "gemma3:4b"  # séances default to the bigger medium


def test_summon_interactive(haunted_house, fake_ollama, capsys, monkeypatch):
    answers = iter(["/record", "/epitaph", "what did you do?", "/bye"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert main(["-C", haunted_house, "summon", "src/fax_gateway.py", "--host", fake_ollama.url]) == 0
    out = capsys.readouterr().out
    assert "Add fax gateway for the Hargrove account" in out      # /record
    assert "🪦 Hargrove asked twice for colour" in out              # /epitaph through the model
    # invocation + question + farewell, plus the epitaph's own call
    assert len(fake_ollama.requests) == 4


def test_the_exorcist_sends_a_lying_ghost_back(haunted_house, capsys):
    from conftest import FakeModel
    server = FakeModel("ollama", reply=[
        "At 17:56 Jules ran me, and by 18:30 Kevin Brightwater had rolled back prod.",
        "The mist hides what happened that weekend. Priya Raman only wrote: See incident #666.",
    ])
    try:
        rc = main(["-C", haunted_house, "summon", "scripts/deploy_friday.sh", "--host", server.url,
                   "--ask", "What happened that weekend? Give me the timeline."])
    finally:
        server.close()
    assert rc == 0
    out = capsys.readouterr().out
    assert "the exorcist: git does not remember" in out
    assert "17:56" in out and "Kevin Brightwater" in out          # shown, then rejected
    assert "The mist hides what happened" in out
    assert "still doubts" not in out
    scolding = server.requests[1]["body"]["messages"][-1]["content"]
    assert "Git does not remember" in scolding


def test_summon_without_model_fails_cleanly(haunted_house, capsys):
    rc = main(["-C", haunted_house, "summon", "src/fax_gateway.py", "--host", "http://127.0.0.1:9", "--ask", "hi"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "No medium answers" in captured.err
    assert "fax_gateway.py:" not in captured.out


def test_epitaph_and_obituary(haunted_house, fake_ollama, capsys):
    assert main(["-C", haunted_house, "epitaph", "--plain", "lib/leftpad.js"]) == 0
    assert main(["-C", haunted_house, "obituary", "src/fax_gateway.py", "--host", fake_ollama.url]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Vendor leftpad so we never depend on the internet again"  # the words it was born with
    obit = out[1]
    assert obit.startswith("fax_gateway.py (2017–2024), a Python file")
    assert "It sent invoices by fax through an SMTP relay" in obit            # the model's sketch
    assert "Marguerite Okafor added it with the words “Add fax gateway for the Hargrove account”" in obit
    assert "Dev Patel laid it to rest" in obit
    assert fake_ollama.requests[0]["body"]["format"]["required"] == ["character"]


def test_obituaries_markdown_for_pr_bots(haunted_house, fake_ollama, capsys):
    assert main(["-C", haunted_house, "obituaries", "HEAD~2..HEAD", "--host", fake_ollama.url]) == 0
    out = capsys.readouterr().out
    assert out.startswith("## 🕯️ In Memoriam")
    assert "### 🪦 ` src/fax_gateway.py ` · 2017–2024" in out
    assert "### 🪦 ` legacy/PAYROLL.cbl `" in out
    assert "> _Hargrove asked twice for colour" in out
    assert "`gemma3:1b`, an open-weight model running inside this job" in out


def test_obituaries_fall_back_when_model_is_gone(haunted_house, capsys):
    assert main(["-C", haunted_house, "obituaries", "HEAD~1..HEAD", "--host", "http://127.0.0.1:9"]) == 0
    out = capsys.readouterr().out
    assert "written from git facts alone" in out
    assert "Vendor" not in out and "Add fax gateway for the Hargrove account" in out


def test_obituaries_nothing_died(haunted_house, capsys):
    assert main(["-C", haunted_house, "obituaries", "HEAD..HEAD", "--plain"]) == 0
    assert capsys.readouterr().out == ""


def test_obituaries_limit(haunted_house, capsys):
    assert main(["-C", haunted_house, "obituaries", "HEAD~2..HEAD", "--plain", "--max", "1"]) == 0
    assert "…and 1 more rest in unmarked graves" in capsys.readouterr().out


def test_ofrenda(haunted_house, fake_ollama, tmp_path, capsys):
    out = tmp_path / "ofrenda.html"
    assert main(["-C", haunted_house, "ofrenda", "-o", str(out), "--host", fake_ollama.url, "--title", "Haunted <House>"]) == 0
    page = out.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    assert "Haunted &lt;House&gt;" in page
    assert page.count('class="portrait"') == 5
    assert "<code>smtplib</code>" in page           # favorite offerings
    assert "support colour faxes" in page           # unfinished business
    assert "Hargrove asked twice for colour" in page   # epitaph from the model
    assert "born with the words" in page
    assert "gemma3:1b" in page
    assert "<script" not in page


def test_ofrenda_only_and_plain(haunted_house, tmp_path):
    out = tmp_path / "o.html"
    assert main(["-C", haunted_house, "ofrenda", "--plain", "-o", str(out), "--only", "src/y2k_patch.c"]) == 0
    page = out.read_text(encoding="utf-8")
    assert page.count('class="portrait"') == 1
    assert "Emergency Y2K patch for the ledger" in page


def test_resurrect(house_copy, capsys):
    assert main(["-C", house_copy, "resurrect", "lib/leftpad.js"]) == 0
    with open(os.path.join(house_copy, "lib", "leftpad.js")) as fh:
        assert "function leftpad" in fh.read()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=house_copy, capture_output=True, text=True).stdout
    assert "A  lib/leftpad.js" in status
    assert main(["-C", house_copy, "resurrect", "src/y2k_patch.c"]) == 0
    os.remove(os.path.join(house_copy, "src", "y2k_patch.c"))
    with open(os.path.join(house_copy, "src", "y2k_patch.c"), "w") as fh:
        fh.write("squatter")
    assert main(["-C", house_copy, "resurrect", "src/y2k_patch.c"]) == 1
    assert "already lives" in capsys.readouterr().err


def test_errors_are_friendly(tmp_path, capsys):
    assert main(["-C", str(tmp_path), "graveyard"]) == 1
    assert "not a git repository" in capsys.readouterr().err


def test_runs_as_git_subcommand(haunted_house, tmp_path):
    """`git seance` works once a git-seance executable is on PATH."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "git-seance"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_sh = root.replace("\\", "/")
    py_sh = sys.executable.replace("\\", "/")
    exe.write_text(f'#!/bin/sh\nPYTHONPATH="{root_sh}" exec "{py_sh}" -m git_seance "$@"\n')
    exe.chmod(0o755)
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}")
    out = subprocess.run(["git", "seance", "graveyard", "-n", "0"], cwd=haunted_house, env=env,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "souls departed" in out.stdout


def test_pr_markdown_is_injection_safe(tmp_path, capsys):
    repo_dir = tmp_path / "inj"
    repo_dir.mkdir()
    run = lambda *a: subprocess.run(["git", *a], cwd=repo_dir, check=True, capture_output=True)
    run("init", "-q")
    run("config", "user.name", "Mallory")
    run("config", "user.email", "m@example.com")
    evil = "x` details@octocat.py" if sys.platform == "win32" else "x` <details>@octocat.py"
    (repo_dir / evil).write_text("print(1)\n")
    (repo_dir / "keep").write_text("k\n")
    run("add", "-A"); run("commit", "-qm", "born @everyone ![](https://evil.example/p.png)")
    run("rm", "-q", evil)
    run("commit", "-qm", "cleanup @everyone <!-- git-seance:in-memoriam --> [x](javascript:alert(1))")
    assert main(["-C", str(repo_dir), "obituaries", "HEAD~1..HEAD", "--plain"]) == 0
    out = capsys.readouterr().out
    assert "@everyone" not in out and "@octocat" not in out
    assert "<!--" not in out
    # inert inside a code span whose fence is longer than any backtick run in the name
    if sys.platform != "win32":
        assert "`` x` <details>@\u200boctocat.py ``" in out
        assert out.count("<details>") == 2  # heading and the summon hint, both code spans
    else:
        assert "`` x` details@\u200boctocat.py ``" in out
    assert "[x](" not in out and "![](" not in out   # brackets escaped: no links, no images
    assert "``" in out  # the path's backtick could not close its code span


def test_remote_medium_is_announced(haunted_house, capsys):
    main(["-C", haunted_house, "summon", "src/fax_gateway.py", "--host", "http://127.0.0.2:9", "--ask", "hi"])
    assert "not on this machine" in capsys.readouterr().err


def test_plurals(tmp_path, capsys):
    repo_dir = tmp_path / "one"
    repo_dir.mkdir()
    run = lambda *a: subprocess.run(["git", *a], cwd=repo_dir, check=True, capture_output=True)
    run("init", "-q"); run("config", "user.name", "A"); run("config", "user.email", "a@x")
    (repo_dir / "a.py").write_text("x\n"); (repo_dir / "k").write_text("k\n")
    run("add", "-A"); run("commit", "-qm", "b"); run("rm", "-q", "a.py"); run("commit", "-qm", "d")
    assert main(["-C", str(repo_dir), "graveyard"]) == 0
    assert "1 soul departed" in capsys.readouterr().out
