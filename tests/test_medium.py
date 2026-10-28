import pytest

from conftest import FakeModel
from git_seance.medium import Medium, SpiritsSilent, _ollama_host


def test_ollama_streaming(fake_ollama):
    tokens = []
    m = Medium(model="gemma3:1b", host=fake_ollama.url)
    reply = m.speak([{"role": "user", "content": "rise"}], on_token=tokens.append, temperature=0.5, max_tokens=50)
    assert reply == "I was the fax gateway. Dev Patel deleted me."
    assert len(tokens) > 3
    req = fake_ollama.requests[0]
    assert req["path"] == "/api/chat"
    assert req["body"]["model"] == "gemma3:1b"
    assert req["body"]["options"]["temperature"] == 0.5
    assert req["body"]["options"]["num_predict"] == 50
    assert req["body"]["keep_alive"] == "30m"
    assert m.last_stats["seconds"] >= 0


def test_openai_compatible_streaming(fake_openai):
    m = Medium(model="gemma-3-1b-it", host=fake_openai.url, backend="openai")
    assert m.speak([{"role": "user", "content": "rise"}]).startswith("I was the fax gateway")
    assert fake_openai.requests[0]["path"] == "/v1/chat/completions"
    m2 = Medium(model="x", host=fake_openai.url + "/v1", backend="openai")
    m2.speak([{"role": "user", "content": "rise"}])
    assert fake_openai.requests[1]["path"] == "/v1/chat/completions"


def test_missing_model_gives_pull_hint():
    server = FakeModel("ollama", status=404)
    try:
        with pytest.raises(SpiritsSilent, match="ollama pull nope"):
            Medium(model="nope", host=server.url).speak([{"role": "user", "content": "hi"}])
    finally:
        server.close()


def test_no_server_gives_helpful_error():
    with pytest.raises(SpiritsSilent, match="No medium answers"):
        Medium(host="http://127.0.0.1:9", timeout=2).speak([{"role": "user", "content": "hi"}])


def test_empty_reply_is_silence():
    server = FakeModel("ollama", reply="")
    try:
        with pytest.raises(SpiritsSilent, match="no words"):
            Medium(host=server.url).speak([{"role": "user", "content": "hi"}])
    finally:
        server.close()


def test_env_configuration(monkeypatch):
    monkeypatch.setenv("SEANCE_MODEL", "gemma3:4b")
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0")
    m = Medium()
    assert m.model == "gemma3:4b"
    assert m.host == "http://localhost:11434"
    monkeypatch.setenv("OLLAMA_HOST", "http://box:1234")
    assert _ollama_host() == "http://box:1234"
