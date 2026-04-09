#!/usr/bin/env python3
"""
Turkish voice GUI for Claude Code /voicetr skill.
Dark window, red record button, outputs transcript to stdout.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import threading
import tkinter as tk
import numpy as np
import sounddevice as sd
import whisper

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 2.0
MAX_DURATION = 60
MODEL_SIZE = "medium"

BG          = "#0d0d0d"
BTN_IDLE    = "#c0392b"
BTN_HOVER   = "#e74c3c"
BTN_PULSE   = ["#c0392b","#d44235","#e74c3c","#ff5541","#e74c3c","#d44235"]
TEXT_DIM    = "#555555"
TEXT_ACTIVE = "#ff5541"


class VoiceGUI:
    def __init__(self):
        self.model = None
        self.recording = False
        self.frames = []
        self.pulse_step = 0

        self.root = tk.Tk()
        self.root.title("voicetr")
        self.root.geometry("260x180")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        # Remove default titlebar decoration on Windows for cleaner look
        self.root.overrideredirect(True)

        # Drag support
        self.root.bind("<ButtonPress-1>",   self._drag_start)
        self.root.bind("<B1-Motion>",       self._drag_motion)
        self._drag_x = self._drag_y = 0

        # Center
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"260x180+{(sw-260)//2}+{(sh-180)//2}")

        # Close button (top-right)
        close = tk.Label(self.root, text="×", bg=BG, fg="#333333",
                         font=("Segoe UI", 14), cursor="hand2")
        close.place(x=238, y=4)
        close.bind("<Button-1>", lambda e: self.root.destroy())
        close.bind("<Enter>",    lambda e: close.config(fg="#888888"))
        close.bind("<Leave>",    lambda e: close.config(fg="#333333"))

        # Canvas for button
        self.cvs = tk.Canvas(self.root, width=260, height=120,
                             bg=BG, highlightthickness=0)
        self.cvs.pack(pady=(14, 0))

        cx, cy, r = 130, 60, 42
        self._cx, self._cy, self._r = cx, cy, r

        # Outer glow ring
        self.ring = self.cvs.create_oval(cx-r-10, cy-r-10, cx+r+10, cy+r+10,
                                          outline="#1a0000", width=2, fill="")
        # Button circle
        self.btn = self.cvs.create_oval(cx-r, cy-r, cx+r, cy+r,
                                         fill=BTN_IDLE, outline="")
        # Mic emoji
        self.icon = self.cvs.create_text(cx, cy, text="🎙",
                                          font=("Segoe UI Emoji", 20), fill="white")

        self.cvs.tag_bind(self.btn,  "<Button-1>", self._on_click)
        self.cvs.tag_bind(self.icon, "<Button-1>", self._on_click)
        self.cvs.tag_bind(self.btn,  "<Enter>",    self._on_hover)
        self.cvs.tag_bind(self.icon, "<Enter>",    self._on_hover)
        self.cvs.tag_bind(self.btn,  "<Leave>",    self._on_leave)
        self.cvs.tag_bind(self.icon, "<Leave>",    self._on_leave)

        # Status text
        self.status_var = tk.StringVar(value="loading model…")
        tk.Label(self.root, textvariable=self.status_var,
                 bg=BG, fg=TEXT_DIM, font=("Segoe UI", 9)).pack()

        # TR badge
        tk.Label(self.root, text="TR", bg=BG, fg="#2a2a2a",
                 font=("Segoe UI", 7, "bold")).pack()

        threading.Thread(target=self._load_model, daemon=True).start()

    # ── drag ──────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag_x, self._drag_y = e.x, e.y

    def _drag_motion(self, e):
        dx, dy = e.x - self._drag_x, e.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    # ── model ──────────────────────────────────────────────────────────────
    def _load_model(self):
        import warnings; warnings.filterwarnings("ignore")
        self.model = whisper.load_model(MODEL_SIZE)
        self.root.after(0, lambda: self.status_var.set("click to record"))

    # ── hover ──────────────────────────────────────────────────────────────
    def _on_hover(self, e):
        if not self.recording and self.model:
            self.cvs.itemconfig(self.btn, fill=BTN_HOVER)

    def _on_leave(self, e):
        if not self.recording:
            self.cvs.itemconfig(self.btn, fill=BTN_IDLE)

    # ── click ──────────────────────────────────────────────────────────────
    def _on_click(self, e):
        if not self.model or self.recording:
            return
        self.recording = True
        self.frames = []
        self.status_var.set("recording…")
        self._pulse()
        threading.Thread(target=self._record, daemon=True).start()

    # ── pulse animation ────────────────────────────────────────────────────
    def _pulse(self):
        if not self.recording:
            return
        i = self.pulse_step % len(BTN_PULSE)
        color = BTN_PULSE[i]
        boom = 1 + (i / len(BTN_PULSE)) * 0.18
        r = int(self._r * boom)
        cx, cy = self._cx, self._cy
        self.cvs.coords(self.btn,  cx-r, cy-r, cx+r, cy+r)
        self.cvs.itemconfig(self.btn, fill=color)
        # glow ring
        rg = r + 10
        self.cvs.coords(self.ring, cx-rg, cy-rg, cx+rg, cy+rg)
        glow = f"#{min(0x3a, i*8):02x}0000"
        self.cvs.itemconfig(self.ring, outline=glow)
        self.pulse_step += 1
        self.root.after(90, self._pulse)

    # ── record ─────────────────────────────────────────────────────────────
    def _record(self):
        chunk = int(SAMPLE_RATE * 0.1)
        silence_needed = int(SILENCE_DURATION / 0.1)
        max_chunks = int(MAX_DURATION / 0.1)
        silent = 0
        started = False

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as s:
            for _ in range(max_chunks):
                data, _ = s.read(chunk)
                self.frames.append(data.copy())
                rms = float(np.sqrt(np.mean(data ** 2)))
                if rms > SILENCE_THRESHOLD:
                    started = True; silent = 0
                elif started:
                    silent += 1
                    if silent >= silence_needed:
                        break

        self.recording = False
        self.root.after(0, self._transcribe)

    # ── transcribe ─────────────────────────────────────────────────────────
    def _transcribe(self):
        # Reset button visuals
        cx, cy, r = self._cx, self._cy, self._r
        self.cvs.coords(self.btn, cx-r, cy-r, cx+r, cy+r)
        self.cvs.itemconfig(self.btn, fill="#333333")
        self.cvs.coords(self.ring, cx-r-10, cy-r-10, cx+r+10, cy+r+10)
        self.cvs.itemconfig(self.ring, outline="#1a0000")
        self.status_var.set("transcribing…")
        threading.Thread(target=self._do_transcribe, daemon=True).start()

    def _do_transcribe(self):
        if self.frames:
            audio = np.concatenate(self.frames, axis=0).flatten()
            if len(audio) / SAMPLE_RATE >= 0.5:
                import warnings; warnings.filterwarnings("ignore")
                result = self.model.transcribe(audio, language="tr", fp16=False)
                print(result["text"].strip(), flush=True)
        self.root.after(0, self.root.destroy)


def main():
    VoiceGUI().root.mainloop()


if __name__ == "__main__":
    main()
