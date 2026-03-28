"""
Standalone debug script for the Equalize NYC Live API.
Usage: python test_live.py
"""
import sys
import io
import asyncio
import time
from pathlib import Path

# Force UTF-8 output on Windows so box-drawing / tick chars render correctly.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── ANSI helpers ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(label: str, value: str = "") -> None:
    suffix = f"  ({value})" if value else ""
    print(f"  {GREEN}✔ {label}{RESET}{suffix}")

def fail(label: str, hint: str = "") -> None:
    print(f"  {RED}✘ {label}{RESET}")
    if hint:
        print(f"    {YELLOW}→ {hint}{RESET}")

# ── 1. Config checks ──────────────────────────────────────────────────────────
print(f"\n{BOLD}── Config Check ──────────────────────────────────────────{RESET}")

import config  # noqa: E402  (import after path setup is intentional here)

config_ok = True

# GCP_PROJECT_ID
if config.PROJECT_ID:
    ok("GCP_PROJECT_ID", config.PROJECT_ID)
else:
    fail("GCP_PROJECT_ID is not set", "add GCP_PROJECT_ID=your-project-id to .env")
    config_ok = False

# GCP_LOCATION
if config.LOCATION:
    ok("GCP_LOCATION", config.LOCATION)
else:
    fail("GCP_LOCATION is not set", "add GCP_LOCATION=global to .env")
    config_ok = False

# GOOGLE_APPLICATION_CREDENTIALS
if not config.CREDENTIALS_PATH:
    fail(
        "GOOGLE_APPLICATION_CREDENTIALS is not set",
        "add GOOGLE_APPLICATION_CREDENTIALS=credentials.json to .env",
    )
    config_ok = False
elif Path(config.CREDENTIALS_PATH).is_file():
    ok("GOOGLE_APPLICATION_CREDENTIALS", config.CREDENTIALS_PATH)
else:
    fail(
        f"GOOGLE_APPLICATION_CREDENTIALS → file not found: '{config.CREDENTIALS_PATH}'",
        "place credentials.json at that path or update .env",
    )
    config_ok = False

if not config_ok:
    print(f"\n{RED}Aborting — fix the config errors above and re-run.{RESET}\n")
    raise SystemExit(1)

print(f"  {GREEN}All config checks passed.{RESET}\n")

# ── 2. Live session test ──────────────────────────────────────────────────────
QUESTION = "What are the most common bogus fines NYC gives small businesses?"


async def run() -> None:
    from live_engine import CivicAILive  # noqa: PLC0415

    print(f"{BOLD}── Opening Live Session ──────────────────────────────────{RESET}")
    t_start = time.perf_counter()

    async with CivicAILive() as ai:
        t_connected = time.perf_counter()
        print(f"  Session opened  ({t_connected - t_start:.2f}s)\n")

        print(f"{BOLD}── Sending question ──────────────────────────────────────{RESET}")
        print(f"  {YELLOW}{QUESTION}{RESET}\n")
        await ai.send_text(QUESTION)

        print(f"{BOLD}── Streaming response ────────────────────────────────────{RESET}")
        t_first_chunk: float | None = None
        audio_bytes_total = 0
        text_chunks: list[str] = []

        async for chunk in ai.receive_turn():
            if isinstance(chunk, bytes):
                if t_first_chunk is None:
                    t_first_chunk = time.perf_counter()
                    ttft = t_first_chunk - t_connected
                    print(f"  {YELLOW}[first audio chunk in {ttft:.2f}s]{RESET}")
                audio_bytes_total += len(chunk)
                print(f"  audio chunk: {len(chunk):,} bytes  (total {audio_bytes_total:,})", flush=True)
            elif isinstance(chunk, str) and chunk:
                text_chunks.append(chunk)
                print(f"  transcript : {chunk}", flush=True)

        t_done = time.perf_counter()
        total = t_done - t_start

        print(f"\n{BOLD}── Summary ───────────────────────────────────────────────{RESET}")
        print(f"  Audio received  : {GREEN}{audio_bytes_total:,} bytes{RESET}")
        print(f"  Transcript text : {GREEN}{''.join(text_chunks)[:120] or '(none)'}{RESET}")
        print(f"  Total time      : {GREEN}{total:.2f}s{RESET}\n")


asyncio.run(run())
