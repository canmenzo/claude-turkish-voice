"""
Installs the /voice skill for Claude Code with the correct local paths.
Called by install.bat — do not run directly.
"""
import os
import sys
import pathlib

skill_dir = pathlib.Path(os.environ["USERPROFILE"]) / ".claude" / "commands"
skill_dir.mkdir(parents=True, exist_ok=True)

python_exe = sys.executable
repo = pathlib.Path(__file__).parent

# /voice — terminal fallback
voice_content = f"""Run the following command to capture Turkish voice input from the microphone.

IMPORTANT: Run this command in FOREGROUND (do NOT use run_in_background). This avoids task notification clutter in the UI.

```bash
"{python_exe}" "{repo / 'voice_capture.py'}"
```

The command will record until silence is detected and output a Turkish transcript.
Treat the transcript output as my message/question and respond to it accordingly.
If the transcript is in Turkish, you may respond in Turkish or English depending on context.
"""

# /voicetr — GUI window
voicetr_content = f"""Open the Turkish voice input window.

IMPORTANT: Run this command in FOREGROUND (do NOT use run_in_background).

```bash
"{python_exe}" "{repo / 'voice_gui.py'}"
```

A small dark window will open with a red record button. Click it to start recording in Turkish.
The window closes automatically after silence is detected and transcription is done.
Treat the transcript output as my message/question and respond to it accordingly.
If the transcript is in Turkish, you may respond in Turkish or English depending on context.
"""

(skill_dir / "voice.md").write_text(voice_content, encoding="utf-8")
print(f"OK /voice  installed: {skill_dir / 'voice.md'}")

(skill_dir / "voicetr.md").write_text(voicetr_content, encoding="utf-8")
print(f"OK /voicetr installed: {skill_dir / 'voicetr.md'}")
