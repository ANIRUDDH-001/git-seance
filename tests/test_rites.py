from git_seance import history, rites
from git_seance.history import Repo


def spirit(house, path="src/fax_gateway.py"):
    return history.summon(Repo(house), path)


def test_fact_sheet_has_the_facts_and_no_hashes(haunted_house):
    s = spirit(haunted_house)
    sheet = rites.fact_sheet(s)
    for fact in ["src/fax_gateway.py", "14 February 2017", "Marguerite Okafor", "19 July 2024", "Dev Patel",
                 "paperless", "support colour faxes", "7 years, 5 months", "Times you were changed while alive: 3"]:
        assert fact in sheet
    assert s.death.short not in sheet and s.birth.short not in sheet
    assert "exactly" not in sheet and "2 notes left in your code" in sheet


def test_ghost_prompt_includes_rules_memory_and_code(haunted_house):
    prompt = rites.ghost_system(spirit(haunted_house))
    assert "say the mist hides it" in prompt
    assert "Git does NOT remember" in prompt
    assert "def send_cover_page" in prompt


def test_whisper_routes_facts_next_to_the_question(haunted_house):
    s = spirit(haunted_house)
    who = rites.whisper(s, "Who made you?")
    assert who.startswith("Who made you?")
    assert "Marguerite Okafor" in who and "Add fax gateway" in who
    todo = rites.whisper(s, "What is your unfinished business?")
    assert "exactly 2 notes" in todo and "colour faxes" in todo
    code = rites.whisper(s, "Quote the line you are proudest of.")
    assert "def send_fax(number, pdf_bytes, retries=5):" in code
    lost = rites.whisper(s, "What did the weather do?")
    assert "git never recorded this" in lost and "Say the mist hides it" in lost
    said = rites.whisper(s, "What did people say about you on the mailing list?")
    assert "git never recorded this" in said
    words = rites.whisper(s, "What did Marguerite say when she added you?")
    assert "never recorded" not in words and "Add fax gateway for the Hargrove account" in words


def test_topics():
    assert "death" in rites.topics("How did you die?")
    assert "brush" in rites.topics("Have you died before?")
    assert rites.topics("Tell me a story") == ["summary"]


def test_hooks_find_what_is_odd(haunted_house):
    y2k = rites.hooks(spirit(haunted_house, "src/y2k_patch.c"))
    assert "it lived only 2 days" in y2k
    assert any("Emergency Y2K patch" in h for h in y2k)
    payroll = rites.hooks(spirit(haunted_house, "legacy/PAYROLL.cbl"))
    assert "it lived 24 years, 6 months" in payroll
    assert "it was replaced by payroll/src/lib.rs" in payroll
    assert "only Edna Halvorsen ever touched it" in payroll


def test_epitaph_reranker_prefers_specific_and_true(haunted_house):
    s = spirit(haunted_house, "src/y2k_patch.c")
    picked = rites.choose_epitaph(
        ["I faded into the digital ether, a silent echo.",
         "Two days of life. Nothing happened. That was the point.",
         "Born 1987, I guarded the mainframe for decades."],
        s, unsupported_count=lambda t: 1 if "1987" in t else 0)
    assert picked == "Two days of life. Nothing happened. That was the point."


def test_obituary_is_written_from_facts(haunted_house):
    obit = rites.obituary(spirit(haunted_house, "legacy/PAYROLL.cbl"), character="It paid people by the hour.")
    assert obit.startswith("PAYROLL.cbl (1999–2023), a COBOL file in haunted-house, was deleted on 8 September 2023.")
    assert "Edna Halvorsen added it with the words “Initial payroll run for the Friday batch”" in obit
    assert "It paid people by the hour." in obit
    assert "only Edna Halvorsen ever changed it" in obit
    assert "It is survived by payroll/src/lib.rs." in obit
    assert obit.count("survived") == 1
    assert "Thank you, Edna.”" in obit and "Edna.”." not in obit


def test_long_files_are_trimmed_but_keep_shape_and_final_lines(haunted_house):
    s = spirit(haunted_house)
    body = "\n".join(f"def function_{i}():\n    return {i}\n" for i in range(800))
    s.last_words = body + "\nFINAL_LINE = True\n"
    text = rites.last_words(s, budget=3000)
    assert len(text) < 4500
    assert "faded into the mist" in text
    middle = [i for i in range(200, 700) if f"def function_{i}()" in text]
    assert len(middle) >= 10
    assert "FINAL_LINE = True" in text


def test_lifespan_wording():
    assert rites.lifespan(None) == "an unknown span"
    assert rites.lifespan(0) == "less than a day"
    assert rites.lifespan(1) == "1 day"
    assert rites.lifespan(45) == "1 month"
    assert rites.lifespan(365 * 3 + 70) == "3 years, 2 months"


def test_cleaners():
    assert rites.clean_epitaph('**Epitaph 1:** "I faxed so you didn\'t have to."\n\nMore') == "I faxed so you didn't have to."
    assert rites.clean_epitaph("1. Here lies a parser.") == "Here lies a parser."
    assert rites.finish_reply("I was born. I lived. And then the") == "I was born. I lived."
    assert rites.finish_reply("Done.") == "Done."


def test_plain_rites_need_no_model(haunted_house):
    s = spirit(haunted_house, "legacy/PAYROLL.cbl")
    assert rites.plain_epitaph(s) == "Initial payroll run for the Friday batch"
    assert '.".' not in rites.plain_obituary(s)


def test_afterlife_is_whispered_unambiguously(tmp_path):
    import subprocess
    repo_dir = tmp_path / "r"
    repo_dir.mkdir()
    run = lambda *a: subprocess.run(["git", *a], cwd=repo_dir, check=True, capture_output=True)
    run("init", "-q"); run("config", "user.name", "A"); run("config", "user.email", "a@x")
    (repo_dir / "Lib").mkdir()
    (repo_dir / "Lib" / "core.py").write_text("x = 1\n" * 20)
    run("add", "-A"); run("commit", "-qm", "A gift")
    (repo_dir / "Lib" / "t").mkdir()
    run("mv", "Lib/core.py", "Lib/t/_core.py"); run("commit", "-qm", "Remove core")
    run("mv", "Lib/t/_core.py", "Lib/core.py"); run("commit", "-qm", "Revert remove core")
    run("mv", "Lib/core.py", "Lib/t/core.py"); run("commit", "-qm", "Remove core for good")
    s = history.summon(Repo(str(repo_dir)), "Lib/core.py")
    where = rites.whisper(s, "Where is your body now?")
    assert "TODAY your body lives at Lib/t/core.py" in where
    assert "(temporarily; you came back)" in rites.fact_sheet(s)


def test_reranker_rejects_copied_and_garbled_quotes(haunted_house):
    s = spirit(haunted_house, "scripts/deploy_friday.sh")
    picked = rites.choose_epitaph(
        ["Remove Friday deploy script…’ incident #666. A brief existence.",
         "One command, two days. Let the weekend sleep."],
        s, unsupported_count=lambda t: 0)
    assert picked == "One command, two days. Let the weekend sleep."


def test_reranker_avoids_ticket_numbers_and_repeated_openings(haunted_house):
    s = spirit(haunted_house, "legacy/PAYROLL.cbl")
    pick = lambda cands, already=(): rites.choose_epitaph(cands, s, unsupported_count=lambda t: 0, already=already)
    assert pick(["Twenty-four years. Gh-104773 ended the Friday batch.",
                 "Friday batches, every week, until Rust arrived."]) == "Friday batches, every week, until Rust arrived."
    assert pick(["Twenty-four years of Friday batches, then rust.",
                 "Overtime finally works, they said. Not for me."],
                already=["Twenty-four years, six months. Still chasing overtime."]) == "Overtime finally works, they said. Not for me."
