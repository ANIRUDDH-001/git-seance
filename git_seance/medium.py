"""The medium: the thing that lets the dead speak.

Talks to a *local* open-weight model. Two dialects are supported, both over
plain HTTP with the standard library only:

* ``ollama``  - Ollama's native /api/chat (default, http://localhost:11434)
* ``openai``  - any OpenAI-compatible server: llama.cpp's llama-server,
                LM Studio, vLLM, LocalAI, Ollama's /v1 endpoint ...

Nothing here needs an API key, and nothing leaves the machine unless you point
``--host`` somewhere else.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Dict, Iterable, List, Optional

from .history import SeanceError

DEFAULT_MODEL = "gemma3:1b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

Message = Dict[str, str]


class SpiritsSilent(SeanceError):
    """The model could not be reached or refused to answer."""


class Medium:
    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        backend: Optional[str] = None,
        timeout: float = 600.0,
        context: int = 8192,
    ):
        self.backend = (backend or os.environ.get("SEANCE_BACKEND") or "ollama").lower()
        if self.backend not in ("ollama", "openai"):
            raise SeanceError(f"Unknown backend {self.backend!r}; use 'ollama' or 'openai'.")
        self.model = model or os.environ.get("SEANCE_MODEL") or DEFAULT_MODEL
        host = host or os.environ.get("SEANCE_HOST")
        if not host:
            host = _ollama_host() if self.backend == "ollama" else "http://localhost:8080"
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.context = context
        self.last_stats: Dict[str, float] = {}

    @property
    def where(self) -> str:
        return urllib.parse.urlsplit(self.host).hostname or self.host

    @property
    def is_local(self) -> bool:
        """True when inference happens on this machine (Ollama's *-cloud
        models are proxied through localhost but run elsewhere)."""
        cloud = self.model.endswith(("-cloud", ":cloud"))
        return self.where in ("localhost", "127.0.0.1", "::1", "0.0.0.0") and not cloud

    def __repr__(self) -> str:
        return f"Medium({self.backend}:{self.model} @ {self.host})"

    # ------------------------------------------------------------------

    def speak(
        self,
        messages: List[Message],
        on_token: Optional[Callable[[str], None]] = None,
        temperature: float = 0.6,
        max_tokens: int = 300,
        stop: Optional[List[str]] = None,
        schema: Optional[dict] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Send a conversation, stream tokens to ``on_token``, return the reply.

        ``schema`` asks the server for JSON matching a JSON schema (Ollama's
        ``format``; ``response_format`` for OpenAI-compatible servers).
        Timing and token counts of the call land in ``self.last_stats``.
        """
        seed = seed if seed is not None else _env_int("SEANCE_SEED")
        self.last_stats = {}
        started = time.monotonic()
        if self.backend == "ollama":
            url = self.host + "/api/chat"
            options = {
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": self.context,
                "num_predict": max_tokens,
            }
            if stop:
                options["stop"] = stop
            if seed is not None:
                options["seed"] = seed
            body = {"model": self.model, "messages": messages, "stream": True,
                    "keep_alive": "30m", "options": options}
            if schema:
                body["format"] = schema
            chunks = self._ollama_chunks(url, body)
        else:
            base = self.host if self.host.endswith("/v1") else self.host + "/v1"
            url = base + "/chat/completions"
            body = {"model": self.model, "messages": messages, "stream": True,
                    "temperature": temperature, "top_p": 0.9, "max_tokens": max_tokens}
            if stop:
                body["stop"] = stop
            if seed is not None:
                body["seed"] = seed
            if schema:
                body["response_format"] = {"type": "json_schema",
                                           "json_schema": {"name": "reply", "schema": schema}}
            chunks = self._openai_chunks(url, body)

        parts = []
        for piece in chunks:
            parts.append(piece)
            if on_token:
                on_token(piece)
        reply = "".join(parts).strip()
        self.last_stats.setdefault("seconds", round(time.monotonic() - started, 2))
        if not reply:
            raise SpiritsSilent("The spirit opened its mouth, but no words came (empty reply).")
        return reply

    def speak_json(self, messages: List[Message], schema: dict, **kwargs) -> dict:
        """Like speak(), but parse a JSON object (tolerating a stray code fence)."""
        text = self.speak(messages, schema=schema, **kwargs)
        text = text.strip().strip("`")
        if text.startswith("json"):
            text = text[4:]
        start, end = text.find("{"), text.rfind("}")
        try:
            value = json.loads(text[start:end + 1])
        except (ValueError, json.JSONDecodeError):
            raise SpiritsSilent("The spirit spoke in tongues (the reply was not valid JSON).") from None
        if not isinstance(value, dict):
            raise SpiritsSilent("The spirit spoke in tongues (expected a JSON object).")
        return value

    # ------------------------------------------------------------------

    def _post(self, url: str, body: dict):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        key = os.environ.get("SEANCE_API_KEY")
        if key:
            req.add_header("Authorization", "Bearer " + key)
        try:
            return urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            if e.code == 404 and "not found" in detail.lower() and self.backend == "ollama":
                raise SpiritsSilent(
                    f"The medium does not know the model '{self.model}'.\n"
                    f"  Fetch it first:  ollama pull {self.model}"
                ) from None
            raise SpiritsSilent(f"The medium refused ({e.code}): {detail}") from None
        except (urllib.error.URLError, ConnectionError, socket.timeout) as e:
            reason = getattr(e, "reason", e)
            hint = (
                "  Start Ollama (`ollama serve`) and pull a model (`ollama pull gemma3:1b`),\n"
                "  or point --host / SEANCE_HOST at your local model server."
            )
            raise SpiritsSilent(f"No medium answers at {self.host} ({reason}).\n{hint}") from None

    def _ollama_chunks(self, url: str, body: dict) -> Iterable[str]:
        with self._post(url, body) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("error"):
                    raise SpiritsSilent("The medium faltered: " + str(event["error"]))
                piece = (event.get("message") or {}).get("content", "")
                if piece:
                    yield piece
                if event.get("done"):
                    self.last_stats = {
                        k: event.get(k) for k in
                        ("prompt_eval_count", "eval_count", "prompt_eval_duration", "eval_duration", "total_duration")
                        if event.get(k) is not None
                    }
                    if "total_duration" in self.last_stats:
                        self.last_stats["seconds"] = round(self.last_stats["total_duration"] / 1e9, 2)
                    return

    def _openai_chunks(self, url: str, body: dict) -> Iterable[str]:
        with self._post(url, body) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                for choice in event.get("choices", []):
                    piece = (choice.get("delta") or {}).get("content") or ""
                    if piece:
                        yield piece


def _ollama_host() -> str:
    host = os.environ.get("OLLAMA_HOST", "").strip()
    if not host:
        return DEFAULT_OLLAMA_HOST
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    if host.count(":") == 1:  # no port given
        host += ":11434"
    return host.replace("0.0.0.0", "localhost")


def _env_int(name: str) -> Optional[int]:
    value = os.environ.get(name, "").strip()
    return int(value) if value.lstrip("-").isdigit() else None
