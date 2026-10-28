import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_eval_runs_end_to_end(haunted_house, fake_ollama, tmp_path):
    out = tmp_path / "eval" / "fake.json"
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "eval.py"), "--repo", f"house={haunted_house}",
         "--graves", "1", "--host", fake_ollama.url, "--model", "fake", "--out", str(out)],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(out.read_text())
    assert set(result["summary"]) == {"naive", "whisper", "guarded"}
    rows = result["rows"]
    assert len(rows) == 9 * 3  # fax_gateway: 4 answerable + 5 unanswerable questions, 3 setups
    assert all(r["path"] == "src/fax_gateway.py" for r in rows)
    assert "| guarded |" in (tmp_path / "eval" / "fake.md").read_text()


def test_eval_survives_a_silent_model(haunted_house, tmp_path):
    from conftest import FakeModel
    server = FakeModel("ollama", reply="")
    out = tmp_path / "silent.json"
    try:
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "eval.py"), "--repo", f"house={haunted_house}",
             "--graves", "1", "--modes", "naive", "--host", server.url, "--out", str(out)],
            capture_output=True, text=True, timeout=120)
    finally:
        server.close()
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(out.read_text())["summary"]["naive"]
    assert summary["silent"] == 9 and summary["answer_accuracy"] == 0
