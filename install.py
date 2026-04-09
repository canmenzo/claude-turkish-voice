"""
Installs the /voicetr skill for Claude Code with correct local paths.
Also installs a short 'voicetr' command to Python Scripts (on PATH).
Called by install.bat — do not run directly.
"""
import os
import sys
import pathlib
import subprocess

python_exe = sys.executable
repo       = pathlib.Path(__file__).parent

# ── Claude Code skill ─────────────────────────────────────────────────────
skill_dir = pathlib.Path(os.environ["USERPROFILE"]) / ".claude" / "commands"
skill_dir.mkdir(parents=True, exist_ok=True)

# Use short 'voicetr' command so the skill shows clean output
scripts_dir = pathlib.Path(python_exe).parent / "Scripts"
voicetr_cmd = scripts_dir / "voicetr.bat"

voicetr_content = f"""Open the Turkish voice recorder.

IMPORTANT: Run this command in FOREGROUND (do NOT use run_in_background).

```bash
"{python_exe}" "{repo / 'voice_gui.py'}"
```

A dark window opens with a red record button. Click to record in Turkish.
After recording, click "gönder" to send the transcript to Claude (closes window).
Click x to close without sending.
Treat the transcript output as my message/question and respond to it accordingly.
If the transcript is in Turkish, you may respond in Turkish or English depending on context.
"""

old = skill_dir / "voice.md"
if old.exists():
    old.unlink()

(skill_dir / "voicetr.md").write_text(voicetr_content, encoding="utf-8")
print(f"OK /voicetr skill installed")

# ── voicetr.bat in ~/.claude (short, reliable path) ───────────────────────
claude_dir  = pathlib.Path(os.environ["USERPROFILE"]) / ".claude"
voicetr_bat = claude_dir / "voicetr.bat"
bat = f'@echo off\n"{python_exe}" "{repo / "voice_gui.py"}"\n'
voicetr_bat.write_text(bat, encoding="utf-8")
print(f"OK voicetr.bat installed: {voicetr_bat}")

# ── Remove startup hotkey shortcut if present ─────────────────────────────
startup_lnk = (pathlib.Path(os.environ["APPDATA"])
               / "Microsoft" / "Windows" / "Start Menu"
               / "Programs" / "Startup" / "voicetr-hotkey.lnk")
if startup_lnk.exists():
    startup_lnk.unlink()
    print("OK removed hotkey startup entry")
