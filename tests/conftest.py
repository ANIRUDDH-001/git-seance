import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def haunted_house(tmp_path_factory):
    target = tmp_path_factory.mktemp("repos") / "haunted-house"
    subprocess.run(
        ["bash", os.path.join(ROOT, "demo", "make_haunted_house.sh"), str(target)],
        check=True, stdout=subprocess.DEVNULL,
    )
    return str(target)


@pytest.fixture
def house_copy(haunted_house, tmp_path):
    """A private clone for tests that change the working tree."""
    dest = tmp_path / "house"
    subprocess.run(["git", "clone", "-q", haunted_house, str(dest)], check=True)
    return str(dest)


class FakeModel:
    """A pretend local model server speaking Ollama or OpenAI dialects."""

    def __init__(self, dialect, reply="I was the fax gateway. Dev Patel deleted me.", status=200):
        self.dialect = dialect
        self.reply = reply          # a string, or a list of strings served in turn
        self.status = status
        self.requests = []
        self.epitaphs = ["Hargrove asked twice for colour. I answered in black and white.",
                         "Born for one client, buried by a paperless one."]
        self.character = "It sent invoices by fax through an SMTP relay and retried patiently when the relay failed."
        model = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                model.requests.append({"path": self.path, "body": body})
                if model.status != 200:
                    self.send_response(model.status)
                    self.end_headers()
                    self.wfile.write(b'{"error":"model \\"nope\\" not found, try pulling it first"}')
                    return
                self.send_response(200)
                self.end_headers()
                words = [w + " " for w in model.next_reply(body).split(" ")]
                if model.dialect == "ollama":
                    for w in words:
                        self.wfile.write((json.dumps({"message": {"content": w}, "done": False}) + "\n").encode())
                    self.wfile.write((json.dumps({"message": {"content": ""}, "done": True}) + "\n").encode())
                else:
                    for w in words:
                        event = {"choices": [{"delta": {"content": w}}]}
                        self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
                    self.wfile.write(b"data: [DONE]\n\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def next_reply(self, body):
        schema = body.get("format") or (body.get("response_format") or {}).get("json_schema", {}).get("schema")
        if isinstance(schema, dict):
            props = schema.get("properties", {})
            if "epitaphs" in props:
                return json.dumps({"epitaphs": self.epitaphs})
            if "character" in props:
                return json.dumps({"character": self.character})
        if isinstance(self.reply, list):
            return self.reply.pop(0) if len(self.reply) > 1 else self.reply[0]
        return self.reply

    def close(self):
        self.server.shutdown()


@pytest.fixture
def fake_ollama():
    m = FakeModel("ollama")
    yield m
    m.close()


@pytest.fixture
def fake_openai():
    m = FakeModel("openai")
    yield m
    m.close()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("SEANCE_MODEL", "SEANCE_HOST", "SEANCE_BACKEND", "OLLAMA_HOST", "SEANCE_API_KEY", "FORCE_COLOR"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
