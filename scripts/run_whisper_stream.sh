#!/bin/bash
set -euo pipefail

# Helper script to launch whisper.cpp's live transcription demo with sensible defaults.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_DIR="$REPO_ROOT/external/whisper_cpp"
BIN_PATH="$WHISPER_DIR/build/bin/whisper-stream"

if [[ -n "${WHISPER_MODEL_PATH:-}" ]]; then
  MODEL_PATH="$WHISPER_MODEL_PATH"
else
  if [[ -f "$WHISPER_DIR/models/ggml-large-v3.bin" ]]; then
    MODEL_PATH="$WHISPER_DIR/models/ggml-large-v3.bin"
  else
    MODEL_PATH="$WHISPER_DIR/models/ggml-base.en.bin"
  fi
fi

if [[ ! -x "$BIN_PATH" ]]; then
  echo "[ERROR] whisper-stream binary not found at: $BIN_PATH" >&2
  echo "        Rebuild whisper.cpp with SDL support:" >&2
  echo "          cd \"$WHISPER_DIR\"" >&2
  echo "          cmake -B build -DWHISPER_SDL2=ON" >&2
  echo "          cmake --build build --config Release" >&2
  exit 1
fi

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "[ERROR] Whisper model not found at: $MODEL_PATH" >&2
  echo "        Download one with:" >&2
  echo "          cd \"$WHISPER_DIR\"" >&2
  echo "          ./models/download-ggml-model.sh base.en" >&2
  exit 1
fi

THREADS="$(sysctl -n hw.physicalcpu 2>/dev/null || echo 4)"

echo "[INFO] Starting live transcription with $THREADS threads."
echo "[INFO] Press Ctrl+C to stop."
echo

"$BIN_PATH" -t "$THREADS" -m "$MODEL_PATH" "$@"
