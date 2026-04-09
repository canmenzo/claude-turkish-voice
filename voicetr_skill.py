"""
Claude Code /voicetr skill runner.
Starts the GUI if not running, waits for transcript, prints it, exits.
Claude Code gets the transcript when this script exits.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
import time
import pathlib
import subprocess

CLAUDE_DIR   = pathlib.Path.home() / ".claude"
OUTPUT_FILE  = CLAUDE_DIR / "voicetr_output.txt"
PID_FILE     = CLAUDE_DIR / "voicetr.pid"
TIMEOUT      = 180  # seconds to wait for user to record


def gui_alive():
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True
        )
        return str(pid) in result.stdout
    except Exception:
        return False


# Remove stale output from previous session
if OUTPUT_FILE.exists():
    OUTPUT_FILE.unlink()

# Start GUI if not already open
if not gui_alive():
    gui_path = str(pathlib.Path(__file__).parent / "voice_gui.py")
    subprocess.Popen(
        [sys.executable, gui_path],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    )
    time.sleep(0.3)  # let the process start

# Wait for transcript file (written by GUI after each recording)
start = time.time()
while time.time() - start < TIMEOUT:
    if OUTPUT_FILE.exists():
        try:
            transcript = OUTPUT_FILE.read_text(encoding="utf-8").strip()
            OUTPUT_FILE.unlink()
            if transcript:
                print(transcript, flush=True)
        except Exception:
            pass
        sys.exit(0)
    time.sleep(0.15)

sys.exit(0)
