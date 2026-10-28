import subprocess

import pytest

from git_seance import history
from git_seance.history import Repo, SeanceError


def test_graveyard_lists_the_dead_newest_first(haunted_house):
    graves = history.graveyard(Repo(haunted_house))
    assert [g.path for g in graves] == [
        "src/fax_gateway.py",
        "legacy/PAYROLL.cbl",
        "scripts/deploy_friday.sh",
        "lib/leftpad.js",
        "src/y2k_patch.c",
    ]


def test_renamed_files_are_reincarnated_not_dead(haunted_house):
    paths = {g.path for g in history.graveyard(Repo(haunted_house))}
    assert "src/utils.py" not in paths
    assert "src/helpers.py" not in paths


def test_graves_know_birth_and_death(haunted_house):
    fax = history.graveyard(Repo(haunted_house))[0]
    assert fax.birth.author == "Marguerite Okafor"
    assert fax.birth.date.year == 2017
    assert fax.death.author == "Dev Patel"
    assert fax.death.subject.startswith("Remove fax support")


def test_graveyard_pathspec(haunted_house):
    graves = history.graveyard(Repo(haunted_house), pathspec=["src/"])
    assert [g.path for g in graves] == ["src/fax_gateway.py", "src/y2k_patch.c"]


def test_summon_builds_a_full_spirit(haunted_house):
    s = history.summon(Repo(haunted_house), "src/fax_gateway.py")
    assert s.language == "Python"
    assert s.line_count == 28
    assert [c.author for c in s.life] == ["Marguerite Okafor", "Marguerite Okafor", "Tomás Ibarra"]
    assert s.family[0] == ("Marguerite Okafor", 2)
    assert s.lifespan_days == (s.death.date - s.birth.date).days
    assert "retries=5" in s.last_words  # the content just before death
    assert s.unfinished_business == [
        "TODO: support colour faxes (Hargrove asked twice)",
        "HACK: the relay drops pages over 20, so we warn instead of splitting",
    ]
    assert s.favorite_imports == ["smtplib", "time", "email.message"]
    assert "paperless" in s.death_message


def test_successors_are_born_in_the_killing_commit(haunted_house):
    s = history.summon(Repo(haunted_house), "legacy/PAYROLL.cbl")
    assert s.successors == ["payroll/src/lib.rs"]
    assert s.language == "COBOL"
    assert s.unfinished_business == ["TODO: OVERTIME AFTER 40 HOURS (ASKED FOR IN 1999)"]


def test_short_lives(haunted_house):
    s = history.summon(Repo(haunted_house), "src/y2k_patch.c")
    assert s.lifespan_days == 2
    assert s.favorite_imports == ["stdio.h", "time.h"]
    assert s.unfinished_business[0].startswith("FIXME: this window breaks again in 2050")


def test_cannot_summon_the_living_or_the_never_born(haunted_house):
    repo = Repo(haunted_house)
    with pytest.raises(SeanceError, match="living"):
        history.summon(repo, "src/helpers.py")
    with pytest.raises(SeanceError, match="No grave"):
        history.summon(repo, "src/never_existed.py")


def test_summon_resolves_paths_relative_to_cwd(haunted_house, monkeypatch):
    import os
    os.makedirs(os.path.join(haunted_house, "src"), exist_ok=True)
    s = history.summon(Repo(os.path.join(haunted_house, "src")), "fax_gateway.py")
    assert s.path == "src/fax_gateway.py"


def test_past_lives_follow_renames(tmp_path):
    repo_dir = tmp_path / "r"
    run = lambda *a: subprocess.run(["git", *a], cwd=repo_dir, check=True, capture_output=True)
    repo_dir.mkdir()
    run("init", "-q")
    run("config", "user.name", "A")
    run("config", "user.email", "a@example.com")
    (repo_dir / "old_name.py").write_text("x = 1\n" * 20)
    run("add", "-A"); run("commit", "-qm", "birth")
    run("mv", "old_name.py", "new_name.py"); run("commit", "-qm", "rename")
    run("rm", "-q", "new_name.py"); run("commit", "-qm", "death")
    s = history.summon(Repo(str(repo_dir)), "new_name.py")
    assert s.past_names == ["old_name.py"]
    assert s.birth.subject == "birth"
    assert len(s.life) == 2


def test_resurrected_files_leave_the_graveyard(tmp_path):
    repo_dir = tmp_path / "r"
    run = lambda *a: subprocess.run(["git", *a], cwd=repo_dir, check=True, capture_output=True)
    repo_dir.mkdir()
    run("init", "-q")
    run("config", "user.name", "A")
    run("config", "user.email", "a@example.com")
    (repo_dir / "lazarus.txt").write_text("hello\n")
    (repo_dir / "bin.dat").write_bytes(b"\x00\x01\x02" * 10)
    run("add", "-A"); run("commit", "-qm", "birth")
    run("rm", "-q", "lazarus.txt", "bin.dat"); run("commit", "-qm", "death")
    (repo_dir / "lazarus.txt").write_text("I'm back\n")
    run("add", "-A"); run("commit", "-qm", "come forth")
    repo = Repo(str(repo_dir))
    assert [g.path for g in history.graveyard(repo)] == ["bin.dat"]
    spirit = history.summon(repo, "bin.dat")
    assert spirit.is_binary and spirit.size_bytes == 30 and spirit.line_count == 0
    assert repo.blob_line_counts(["HEAD^^:bin.dat", "HEAD^^:lazarus.txt", "HEAD:nope"]) == {
        "HEAD^^:bin.dat": None, "HEAD^^:lazarus.txt": 1, "HEAD:nope": None,
    }
    with pytest.raises(SeanceError, match="resurrected|living"):
        history.summon(repo, "lazarus.txt")


def test_deaths_in_range(haunted_house):
    repo = Repo(haunted_house)
    assert sorted(history.deaths_in_range(repo, "HEAD~2", "HEAD")) == ["legacy/PAYROLL.cbl", "src/fax_gateway.py"]
    assert history.deaths_in_range(repo, "HEAD", "HEAD") == []
    # born and buried inside the range: not a death the PR causes
    assert "lib/leftpad.js" not in history.deaths_in_range(repo, "HEAD~12", "HEAD")


def test_not_a_repo(tmp_path):
    with pytest.raises(SeanceError, match="not a git repository"):
        Repo(str(tmp_path))


def test_empty_repo_has_empty_graveyard(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert history.graveyard(Repo(str(tmp_path))) == []


@pytest.mark.parametrize("path,lang", [("a/b.rs", "Rust"), ("Makefile", "Makefile"), ("x.unknown", "unknown tongue")])
def test_language_of(path, lang):
    assert history.language_of(path) == lang


def _repo(tmp_path):
    repo_dir = tmp_path / "r"
    repo_dir.mkdir()

    def run(*a):
        return subprocess.run(["git", *a], cwd=repo_dir, check=True, capture_output=True, text=True).stdout

    run("init", "-q", "-b", "main")
    run("config", "user.name", "A")
    run("config", "user.email", "a@example.com")
    return repo_dir, run


def test_deaths_inside_merge_commits_are_seen(tmp_path):
    repo_dir, run = _repo(tmp_path)
    (repo_dir / "keep").write_text("k\n")
    (repo_dir / "evil.py").write_text("x = 1\n")
    run("add", "-A"); run("commit", "-qm", "base")
    run("checkout", "-qb", "side")
    (repo_dir / "side").write_text("s\n")
    run("add", "-A"); run("commit", "-qm", "side")
    run("checkout", "-q", "main")
    (repo_dir / "m").write_text("m\n")
    run("add", "-A"); run("commit", "-qm", "main work")
    run("merge", "--no-commit", "-q", "side")
    run("rm", "-q", "evil.py"); run("commit", "-qm", "merge, and drop evil.py")
    repo = Repo(str(repo_dir))
    assert [g.path for g in history.graveyard(repo)] == ["evil.py"]
    assert history.summon(repo, "evil.py").death.subject == "merge, and drop evil.py"
    assert history.deaths_in_range(repo, "HEAD^1", "HEAD") == ["evil.py"]


def test_revert_inside_a_range_is_not_a_death(tmp_path):
    repo_dir, run = _repo(tmp_path)
    (repo_dir / "a.py").write_text("a\n")
    run("add", "-A"); run("commit", "-qm", "base")
    run("rm", "-q", "a.py"); run("commit", "-qm", "oops")
    run("revert", "--no-edit", "HEAD")
    assert history.deaths_in_range(Repo(str(repo_dir)), "HEAD~2", "HEAD") == []


def test_a_name_that_died_in_a_rename_has_an_afterlife(tmp_path):
    repo_dir, run = _repo(tmp_path)
    (repo_dir / "Lib").mkdir()
    (repo_dir / "Lib" / "asyncore.py").write_text("x = 1\n" * 20)
    run("add", "-A"); run("commit", "-qm", "A gift from Sam")
    (repo_dir / "Lib" / "support").mkdir()
    run("mv", "Lib/asyncore.py", "Lib/support/asyncore.py"); run("commit", "-qm", "Remove asyncore")
    repo = Repo(str(repo_dir))
    s = history.summon(repo, "Lib/asyncore.py")
    assert s.afterlife == "Lib/support/asyncore.py" and s.afterlife_alive
    with pytest.raises(SeanceError, match="still lives on as Lib/support/asyncore.py"):
        history.resurrect(repo, s)
    assert history.graveyard(repo) == []  # a move is not a death in the graveyard


def test_a_directory_is_not_a_spirit(tmp_path):
    repo_dir, run = _repo(tmp_path)
    (repo_dir / "pkg").mkdir()
    (repo_dir / "pkg" / "a.py").write_text("a\n")
    (repo_dir / "keep").write_text("k\n")
    run("add", "-A"); run("commit", "-qm", "birth")
    run("rm", "-rq", "pkg"); run("commit", "-qm", "death")
    with pytest.raises(SeanceError, match="whole directory"):
        history.summon(Repo(str(repo_dir)), "pkg")


def test_shallow_clones_dont_invent_births(haunted_house, tmp_path):
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "2", "file://" + haunted_house, str(shallow)], check=True)
    s = history.summon(Repo(str(shallow)), "src/fax_gateway.py")
    assert s.birth is None and s.lifespan_days is None


def test_fragments_and_trailers(tmp_path):
    repo_dir, run = _repo(tmp_path)
    (repo_dir / "Misc" / "NEWS.d").mkdir(parents=True)
    (repo_dir / "Misc" / "NEWS.d" / "123.rst").write_text("Fixed a thing.\n")
    (repo_dir / "old.py").write_text("x = 1\n")
    run("add", "-A"); run("commit", "-qm", "birth")
    (repo_dir / "Misc" / "NEWS.d" / "456.rst").write_text("Removed old.\n")
    run("rm", "-q", "old.py", "Misc/NEWS.d/123.rst")
    run("add", "-A"); run("commit", "-qm", "Remove old\n\nCo-authored-by: B <b@example.com>")
    repo = Repo(str(repo_dir))
    assert [g.path for g in history.graveyard(repo)] == ["old.py"]
    assert len(history.graveyard(repo, include_fragments=True)) == 2
    s = history.summon(repo, "old.py")
    assert s.death_message == "Remove old"
    assert s.successors == []  # a NEWS entry is paperwork, not an heir


def test_brushes_with_death_and_moves(tmp_path):
    repo_dir, run = _repo(tmp_path)
    (repo_dir / "Lib").mkdir()
    (repo_dir / "Lib" / "telnet.py").write_text("x = 1\n" * 30)
    run("add", "-A"); run("commit", "-qm", "A gift from Sam")
    (repo_dir / "Lib" / "telnet.py").write_text("x = 2\n" * 30)
    run("commit", "-qam", "Remove duplicate import os")
    run("commit", "-q", "--allow-empty", "-m", "unrelated")
    (repo_dir / "Lib" / "telnet.py").write_text("x = 3\n" * 30)
    run("commit", "-qam", "Deprecate telnet.connect() only")
    (repo_dir / "Lib" / "telnet.py").write_text("x = 4\n" * 30)
    run("commit", "-qam", "Deprecate the telnet module")
    (repo_dir / "Lib" / "tests").mkdir()
    run("mv", "Lib/telnet.py", "Lib/tests/_telnet.py"); run("commit", "-qm", "Remove telnet")
    run("mv", "Lib/tests/_telnet.py", "Lib/telnet.py"); run("commit", "-qm", "Revert remove telnet")
    run("rm", "-q", "Lib/telnet.py"); run("commit", "-qm", "Remove telnet for good")
    s = history.summon(Repo(str(repo_dir)), "Lib/telnet.py")
    assert s.gift == "A gift from Sam"
    assert [c.subject for c in s.brushes_with_death] == [
        "Deprecate the telnet module", "Remove telnet", "Revert remove telnet"]
    assert [(a, b) for a, b, _ in s.moves] == [
        ("Lib/telnet.py", "Lib/tests/_telnet.py"), ("Lib/tests/_telnet.py", "Lib/telnet.py")]
