import pytest

from git_seance import history, rites
from git_seance.exorcist import Exorcist
from git_seance.history import Repo


@pytest.fixture
def judge(haunted_house):
    def make(path):
        s = history.summon(Repo(haunted_house), path)
        ex = Exorcist(s, rites.record(s))
        return lambda text: [str(c) for c in ex.judge(text).unsupported]
    return make


def test_catches_an_invented_timeline(judge):
    j = judge("scripts/deploy_friday.sh")
    assert j("1. **17:55:** Jules ran me.\n2. **17:56 – 18:15:** chaos.") == ["time: 17:56", "time: 18:15"]
    assert j("The mist hides that weekend. Priya Raman only wrote: See incident #666.") == []


def test_catches_wrong_numbers_and_years(judge):
    j = judge("legacy/PAYROLL.cbl")
    assert j("I computed for forty-four years.") == ["number: forty-four"]
    assert j("Edna Halvorsen wrote me in 1999 and I lived 24 years.") == []
    assert j("I was born in 1987.") == ["number: 1987"]


def test_catches_invented_code_and_people(judge):
    j = judge("src/fax_gateway.py")
    assert j("My finest line: `time.sleep(2 ** attempt)`") == []
    assert j("My finest line: `time.sleep(5 ** attempt)`") == ["code: time.sleep(5 ** attempt)"]
    assert j("Marguerite Okafor and Kevin Brightwater loved me.") == ["name: Kevin Brightwater"]
    assert j("```python\nreturn send_fax(number, note.encode(\"latin-1\"))\n```") == []


def test_quotes_must_be_real(judge):
    j = judge("lib/leftpad.js")
    assert j('My maker said "Vendor leftpad so we never depend on the internet again".') == []
    assert j('My maker said "I will pad strings until the heat death of the universe".') == [
        "quote: I will pad strings until the heat death of the universe"]


def test_commit_hashes_must_exist(judge):
    s_ok = judge("src/y2k_patch.c")
    assert s_ok("I died in commit deadbee1.") == ["commit: deadbee1"]


def test_no_false_alarms_on_possessives_year_words_and_quoted_messages(judge):
    j = judge("legacy/PAYROLL.cbl")
    assert j("Edna Halvorsen’s hands made me in nineteen ninety-nine.") == []
    assert j("Dev Patel's commit ended me in two thousand twenty-three.") == []
    assert j("I was born in nineteen eighty-seven.") == ["number: 1987"]
    assert j("I lived twenty-four years.") == []
    k = judge("lib/leftpad.js")
    assert k('Priya Raman wrote "Replace leftpad with `String.prototype.padStart`".') == []
