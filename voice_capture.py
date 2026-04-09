#!/usr/bin/env python3
"""
Turkish voice capture for Claude Code /voice skill.
Records until silence is detected, prints Turkish transcript to stdout.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import sounddevice as sd
import whisper

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01   # RMS below this = silence
SILENCE_DURATION = 2.0     # seconds of silence before stopping
MAX_DURATION = 60          # max recording seconds
MODEL_SIZE = "medium"

def load_model():
    # suppress whisper output
    import warnings
    warnings.filterwarnings("ignore")
    return whisper.load_model(MODEL_SIZE)

def record_until_silence():
    frames = []
    silent_frames = 0
    speaking_started = False
    chunk_size = int(SAMPLE_RATE * 0.1)  # 100ms chunks
    silence_chunks_needed = int(SILENCE_DURATION / 0.1)
    max_chunks = int(MAX_DURATION / 0.1)

    print("Listening... (speak in Turkish)", file=sys.stderr)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32') as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            frames.append(chunk.copy())
            rms = np.sqrt(np.mean(chunk ** 2))

            if rms > SILENCE_THRESHOLD:
                speaking_started = True
                silent_frames = 0
            elif speaking_started:
                silent_frames += 1
                if silent_frames >= silence_chunks_needed:
                    break

    return np.concatenate(frames, axis=0).flatten()

def main():
    model = load_model()
    audio = record_until_silence()

    if len(audio) / SAMPLE_RATE < 0.5:
        print("", flush=True)
        return

    import warnings
    warnings.filterwarnings("ignore")
    result = model.transcribe(audio, language="tr", fp16=False)
    transcript = result["text"].strip()
    print(transcript, flush=True)

if __name__ == "__main__":
    main()
