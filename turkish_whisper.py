#!/usr/bin/env python3
"""
Standalone Turkish Voice-to-Text using OpenAI Whisper.
Press Enter to start/stop recording. Text is copied to clipboard.
"""

import sys
import threading
import numpy as np
import sounddevice as sd
import pyperclip
import whisper

SAMPLE_RATE = 16000
MODEL_SIZE = "medium"

print(f"Loading Whisper '{MODEL_SIZE}' model (downloads ~1.5GB first time)...")
model = whisper.load_model(MODEL_SIZE)
print("Model ready.\n")
print("=" * 50)
print("  ENTER = start recording")
print("  ENTER again = stop + transcribe")
print("  Ctrl+C = quit")
print("=" * 50)

def record_audio():
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=callback):
        print("\n[RECORDING] Speak in Turkish... press ENTER to stop.")
        input()

    audio = np.concatenate(frames, axis=0).flatten()
    return audio

def transcribe(audio):
    print("[Transcribing...]")
    result = model.transcribe(audio, language="tr", fp16=False)
    return result["text"].strip()

def main():
    while True:
        try:
            print("\nPress ENTER to start recording (Ctrl+C to quit)...")
            input()
            audio = record_audio()

            if len(audio) / SAMPLE_RATE < 0.5:
                print("[Too short, skipped]")
                continue

            text = transcribe(audio)

            print("\n" + "─" * 50)
            print(f"TRANSCRIPT:\n{text}")
            print("─" * 50)

            pyperclip.copy(text)
            print("[Copied to clipboard]")

        except KeyboardInterrupt:
            print("\nBye.")
            sys.exit(0)
        except Exception as e:
            print(f"[Error: {e}]")

if __name__ == "__main__":
    main()
