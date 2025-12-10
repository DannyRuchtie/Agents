#!/usr/bin/env python3
"""Live voice chat using whisper.cpp for STT and MasterAgent for responses."""

from __future__ import annotations

import asyncio
import os
import shlex
import signal
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.master_agent import MasterAgent
from config.paths_config import ensure_directories
from config.settings import VOICE_SETTINGS, load_settings, save_settings
from utils.voice import voice_output

WHISPER_DIR = REPO_ROOT / "external" / "whisper_cpp"
WHISPER_BIN = WHISPER_DIR / "build" / "bin" / "whisper-stream"
DEFAULT_MODELS = [
    WHISPER_DIR / "models" / "ggml-large-v3.bin",
    WHISPER_DIR / "models" / "ggml-base.en.bin",
]


def resolve_model_path() -> Path:
    """Resolve the Whisper model path, preferring env override then large model."""
    override = os.getenv("WHISPER_MODEL_PATH")
    if override:
        model_path = Path(override).expanduser().resolve()
        if not model_path.exists():
            raise FileNotFoundError(f"WHISPER_MODEL_PATH points to missing file: {model_path}")
        return model_path

    for candidate in DEFAULT_MODELS:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No Whisper model found. Run ./models/download-ggml-model.sh <model> inside "
        f"{WHISPER_DIR}"
    )


def detect_thread_count() -> int:
    """Best-effort physical core count for whisper.cpp."""
    try:
        value = subprocess.check_output(["sysctl", "-n", "hw.physicalcpu"], text=True).strip()
        return max(1, int(value))
    except Exception:
        return max(1, os.cpu_count() or 1)


class SystemSpeaker:
    """Minimal macOS system TTS wrapper using the `say` command."""

    def __init__(self, voice: Optional[str]):
        self.voice = voice
        self.process: Optional[subprocess.Popen[str]] = None

    def speak(self, text: str) -> None:
        self.stop()
        cmd = ["say"]
        if self.voice:
            cmd.extend(["-v", self.voice])
        cmd.append(text)
        try:
            self.process = subprocess.Popen(cmd)
        except FileNotFoundError:
            print("[WARN] macOS 'say' command not available; skipping audio playback.")
            self.process = None

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            with suppress(Exception):
                self.process.wait(timeout=1)
        self.process = None

    def is_playing(self) -> bool:
        return bool(self.process and self.process.poll() is None)

    def shutdown(self) -> None:
        self.stop()


async def stream_stdout(
    reader: asyncio.StreamReader,
    queue: asyncio.Queue[str],
    mute_event: asyncio.Event,
) -> None:
    """Parse whisper-stream stdout into transcribed chunks."""
    inside_block = False
    buffer: list[str] = []
    last_chunk: Optional[str] = None

    while not reader.at_eof():
        raw = await reader.readline()
        if not raw:
            break
        text = raw.decode("utf-8", errors="ignore").strip()
        if not text:
            continue

        if mute_event.is_set():
            inside_block = False
            buffer.clear()
            continue

        # Handle VAD markers when running with --step 0
        if text.startswith("### Transcription") and "START" in text:
            inside_block = True
            buffer.clear()
            continue

        if text.startswith("### Transcription") and "END" in text:
            inside_block = False
            chunk = " ".join(buffer).strip()
            buffer.clear()
            if chunk and chunk != last_chunk:
                last_chunk = chunk
                await queue.put(chunk)
            continue

        if text == "[Start speaking]":
            print(text)
            continue

        if inside_block:
            if text.startswith("[") and "]" in text:
                _, remainder = text.split("]  ", 1) if "]  " in text else text.split("]", 1)
                buffer.append(remainder.strip())
            else:
                buffer.append(text)
            continue

        # Fallback for non-VAD output (no block markers)
        cleaned = text.replace("\x1b[2K\r", "").strip()
        if cleaned and cleaned != last_chunk:
            last_chunk = cleaned
            await queue.put(cleaned)


async def stream_stderr(reader: asyncio.StreamReader) -> None:
    """Forward whisper-stream stderr to our stderr."""
    while not reader.at_eof():
        raw = await reader.readline()
        if not raw:
            break
        sys.stderr.write(raw.decode("utf-8", errors="ignore"))
        sys.stderr.flush()


async def handle_transcripts(
    queue: asyncio.Queue[str],
    master_agent: MasterAgent,
    tts_provider: str,
    system_speaker: Optional[SystemSpeaker],
    mute_event: asyncio.Event,
) -> None:
    """Process user utterances sequentially via MasterAgent."""
    print("\nSpeak naturally. Say 'exit' or 'quit' to finish.\n")
    while True:
        text = await queue.get()
        queue.task_done()

        if text.lower() in {"exit", "quit", "stop"}:
            print("👋 Ending voice session.")
            break

        print(f"\nYou: {text}")
        voice_output.stop_speaking()
        if system_speaker:
            system_speaker.stop()

        try:
            response = await master_agent.process(text)
        except Exception as exc:
            print(f"Assistant error: {exc}")
            continue

        if not getattr(master_agent, "last_response_streamed", False):
            print(f"\nAssistant: {response}")

        if VOICE_SETTINGS.get("enabled", False):
            mute_event.set()
            try:
                if tts_provider == "system" and system_speaker:
                    system_speaker.speak(response)
                    # Wait until system voice finishes speaking
                    while system_speaker.is_playing():
                        await asyncio.sleep(0.05)
                else:
                    voice_output.speak(response)
                    # Wait for voice_output to finish queued playback
                    # Wait briefly for playback to start
                    for _ in range(100):
                        if voice_output.speaking_flag.is_set():
                            break
                        await asyncio.sleep(0.02)
                    while voice_output.speaking_flag.is_set() or not voice_output.audio_queue.empty():
                        await asyncio.sleep(0.05)
            finally:
                mute_event.clear()


async def run_voice_chat() -> None:
    """Entry point for the async voice chat loop."""
    if not WHISPER_BIN.exists():
        raise FileNotFoundError(
            f"whisper-stream binary not found at {WHISPER_BIN}. "
            "Rebuild whisper.cpp with SDL2 support."
        )

    model_path = resolve_model_path()
    threads = detect_thread_count()

    load_dotenv()
    load_settings()
    ensure_directories()

    default_tts_provider = VOICE_SETTINGS.get("tts_provider", "openai")
    target_tts_provider = os.getenv("VOICE_CHAT_TTS_PROVIDER", default_tts_provider).lower()

    # Enable voice output for this session and temporarily switch provider
    previous_voice_state = VOICE_SETTINGS.get("enabled", False)
    previous_tts_provider = VOICE_SETTINGS.get("tts_provider", "openai")
    VOICE_SETTINGS["enabled"] = True
    VOICE_SETTINGS["tts_provider"] = target_tts_provider
    save_settings()

    tts_provider = VOICE_SETTINGS.get("tts_provider", target_tts_provider).lower()
    system_speaker: Optional[SystemSpeaker] = None
    if tts_provider == "system":
        system_speaker = SystemSpeaker(VOICE_SETTINGS.get("system_voice"))

    master_agent = MasterAgent()

    cmd = [
        str(WHISPER_BIN),
        "-m",
        str(model_path),
        "-t",
        str(threads),
        "--step",
        "0",  # enable VAD mode for cleaner chunked output
        "--length",
        "10000",
        "--keep",
        "200",
        "-l",
        "auto",
    ]

    print("[INFO] Launching whisper-stream:")
    print("       " + shlex.join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    transcripts: asyncio.Queue[str] = asyncio.Queue()
    mute_event = asyncio.Event()

    stdout_task = asyncio.create_task(
        stream_stdout(process.stdout, transcripts, mute_event)
    )  # type: ignore[arg-type]
    stderr_task = asyncio.create_task(stream_stderr(process.stderr))  # type: ignore[arg-type]
    handler_task = asyncio.create_task(
        handle_transcripts(transcripts, master_agent, tts_provider, system_speaker, mute_event)
    )

    try:
        await handler_task
    finally:
        for task in (stdout_task, stderr_task):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.send_signal(signal.SIGINT)
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=3)

        transcripts.put_nowait("exit")
        mute_event.clear()

        if system_speaker:
            system_speaker.shutdown()

        VOICE_SETTINGS["enabled"] = previous_voice_state
        VOICE_SETTINGS["tts_provider"] = previous_tts_provider
        save_settings()


def main() -> None:
    try:
        asyncio.run(run_voice_chat())
    except KeyboardInterrupt:
        print("\nSession interrupted.")
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
