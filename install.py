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

voicetr_content = f"""Open the Turkish voice recorder.

IMPORTANT: Run this command in FOREGROUND (do NOT use run_in_background).

```bash
"{python_exe}" "{repo / 'voice_gui.py'}"
```

A dark window opens with a red record button. Click to record in Turkish.
After recording, click "gönder →" to send the transcript to Claude (closes window).
Click × to close without sending.
Treat the transcript output as my message/question and respond to it accordingly.
If the transcript is in Turkish, you may respond in Turkish or English depending on context.
"""

# Remove old /voice skill if present
old = skill_dir / "voice.md"
if old.exists():
    old.unlink()

(skill_dir / "voicetr.md").write_text(voicetr_content, encoding="utf-8")
print(f"OK /voicetr installed: {skill_dir / 'voicetr.md'}")

# Register hotkey daemon in Windows Startup (Ctrl+Alt+V → /voicetr)
pythonw = pathlib.Path(python_exe).parent / "pythonw.exe"
daemon  = repo / "hotkey_daemon.py"
startup = pathlib.Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

shortcut_ps = f"""
$s = (New-Object -COM WScript.Shell).CreateShortcut('{startup / "voicetr-hotkey.lnk"}')
$s.TargetPath   = '{pythonw}'
$s.Arguments    = '"{daemon}"'
$s.WindowStyle  = 7
$s.Save()
"""
import subprocess
subprocess.run(["powershell", "-Command", shortcut_ps], capture_output=True)
print("OK Ctrl+Alt+V hotkey registered in Windows Startup")
