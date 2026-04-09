"""
Installs the /voicetr skill for Claude Code with correct local paths.
Called by install.bat — do not run directly.
"""
import os
import sys
import pathlib

skill_dir = pathlib.Path(os.environ["USERPROFILE"]) / ".claude" / "commands"
skill_dir.mkdir(parents=True, exist_ok=True)

python_exe = sys.executable
repo       = pathlib.Path(__file__).parent

voicetr_content = f"""Open the Turkish voice input window.

IMPORTANT: Run this command in FOREGROUND (do NOT use run_in_background).

```bash
"{python_exe}" "{repo / 'voice_gui.py'}"
```

A small dark window opens with a red record button.
Click to record in Turkish. The window stays open — click x to send the transcript to Claude.
Treat the transcript output as my message/question and respond to it accordingly.
If the transcript is in Turkish, you may respond in Turkish or English depending on context.
"""

# Remove old /voice skill if present
old = skill_dir / "voice.md"
if old.exists():
    old.unlink()

(skill_dir / "voicetr.md").write_text(voicetr_content, encoding="utf-8")
print(f"OK /voicetr installed: {skill_dir / 'voicetr.md'}")
