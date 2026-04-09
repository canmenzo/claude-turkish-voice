<!-- Template only — run install.bat to generate the real skill with your local paths -->

Run the following command to capture Turkish voice input from the microphone.

IMPORTANT: Run this command in FOREGROUND (do NOT use run_in_background). This avoids task notification clutter in the UI.

```bash
python "<PATH_TO_REPO>/voice_capture.py"
```

The command will record until silence is detected and output a Turkish transcript.
Treat the transcript output as my message/question and respond to it accordingly.
If the transcript is in Turkish, you may respond in Turkish or English depending on context.
