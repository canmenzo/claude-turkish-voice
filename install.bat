@echo off
echo Installing dependencies...
python -m pip install openai-whisper sounddevice numpy pyperclip

echo.
echo Installing voice skill for Claude Code...
python install.py

echo.
echo Done! Use /voice inside Claude Code to speak in Turkish.
pause
