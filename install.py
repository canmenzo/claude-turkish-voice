"""
Installs the /voice skill for Claude Code with the correct local paths.
Called by install.bat — do not run directly.
"""
import os
import pathlib

skill_dir = pathlib.Path(os.environ["USERPROFILE"]) / ".claude" / "commands"
skill_dir.mkdir(parents=True, exist_ok=True)

script_path = str(pathlib.Path(__file__).parent / "voice_capture.py")

content = f"""Run the following command to capture Turkish voice input from the microphone.

IMPORTANT: Run this command in FOREGROUND (do NOT use run_in_background). This avoids task notification clutter in the UI.

```bash
python "{script_path}"
```

The command will record until silence is detected and output a Turkish transcript.
Treat the transcript output as my message/question and respond to it accordingly.
If the transcript is in Turkish, you may respond in Turkish or English depending on context.
"""

(skill_dir / "voice.md").write_text(content, encoding="utf-8")
print(f"Voice skill installed: {skill_dir / 'voice.md'}")
