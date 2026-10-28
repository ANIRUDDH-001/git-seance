#!/usr/bin/env bash
# Install Ollama (if needed), serve it with models in a cacheable directory,
# and pull the requested open-weight model. Used by CI and by action.yml.
# Usage: scripts/start-ollama.sh [model]   (default: gemma3:1b)
set -euo pipefail
model="${1:-gemma3:1b}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
mkdir -p "$OLLAMA_MODELS"

if ! command -v ollama >/dev/null 2>&1; then
  echo "::group::Installing Ollama"
  # pinned, so a new release can't change the medium under us
  curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION="${OLLAMA_VERSION:-0.40.11}" sh
  echo "::endgroup::"
fi

# The Linux installer starts a systemd service as its own user with its own
# model directory. Run our own server instead so the models can be cached.
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl stop ollama 2>/dev/null || true
fi
if ! curl -sf http://localhost:11434/api/version >/dev/null; then
  nohup ollama serve > "${RUNNER_TEMP:-/tmp}/ollama.log" 2>&1 &
  for _ in $(seq 1 60); do
    curl -sf http://localhost:11434/api/version >/dev/null && break
    sleep 1
  done
fi
curl -sf http://localhost:11434/api/version || { echo "Ollama did not start"; cat "${RUNNER_TEMP:-/tmp}/ollama.log"; exit 1; }
echo
ollama pull "$model" 2>&1 | tail -n 2
ollama list
