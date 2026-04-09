#!/usr/bin/env python3
"""
Turkish voice GUI for Claude Code /voicetr skill.
Dark window with custom title bar, red record button, waveform feedback.
Outputs transcript to stdout on completion.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import threading
import tkinter as tk
import numpy as np
import sounddevice as sd
import whisper

SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION  = 2.0
MAX_DURATION      = 60
MODEL_SIZE        = "medium"

# Palette
BORDER    = "#1f1f1f"   # root bg → acts as 1-px border
BG        = "#0d0d0d"   # main bg
TOPBAR    = "#111111"   # title bar bg
SEP       = "#1c1c1c"   # separator line
BTN_IDLE  = "#b03020"
BTN_HOVER = "#e03020"
BTN_REC   = "#ff3322"
BTN_BUSY  = "#2a2a2a"
WAVE_DIM  = "#1e1e1e"
WAVE_LIT  = "#cc2200"
TEXT_DIM  = "#444444"
TEXT_MID  = "#888888"
TEXT_HI   = "#ff4433"
WHITE     = "#ffffff"


class VoiceGUI:
    def __init__(self):
        self.model     = None
        self.recording = False
        self.frames    = []
        self.pulse_step = 0
        self.rms_buf   = [0.0] * 28   # waveform history

        # ── root ──────────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=BORDER)          # thin border effect
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        W, H = 300, 230
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        # drag on any widget calls root-level handlers
        self._drag_x = self._drag_y = 0

        # ── inner frame (real bg) ─────────────────────────────────────────
        inner = tk.Frame(self.root, bg=BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # ── title bar ─────────────────────────────────────────────────────
        bar = tk.Frame(inner, bg=TOPBAR, height=32)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="  🎙", bg=TOPBAR, fg="#cc3322",
                 font=("Segoe UI Emoji", 11)).pack(side="left")
        tk.Label(bar, text="voicetr", bg=TOPBAR, fg="#555555",
                 font=("Segoe UI", 9)).pack(side="left", padx=(2, 0))

        close_btn = tk.Label(bar, text="  ×  ", bg=TOPBAR, fg="#333333",
                             font=("Segoe UI", 13), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())
        close_btn.bind("<Enter>",    lambda e: close_btn.config(fg="#cc4444", bg="#220000"))
        close_btn.bind("<Leave>",    lambda e: close_btn.config(fg="#333333", bg=TOPBAR))

        # bind drag to title bar
        bar.bind("<ButtonPress-1>",  self._drag_start)
        bar.bind("<B1-Motion>",      self._drag_motion)
        for child in bar.winfo_children():
            child.bind("<ButtonPress-1>", self._drag_start)
            child.bind("<B1-Motion>",     self._drag_motion)

        # separator
        tk.Frame(inner, bg=SEP, height=1).pack(fill="x")

        # ── button canvas ─────────────────────────────────────────────────
        self.cvs = tk.Canvas(inner, width=300, height=130,
                             bg=BG, highlightthickness=0)
        self.cvs.pack()

        cx, cy, r = 150, 65, 38
        self._cx, self._cy, self._r = cx, cy, r

        # outer glow ring (animated during recording)
        self.ring = self.cvs.create_oval(
            cx-r-12, cy-r-12, cx+r+12, cy+r+12,
            outline=BORDER, width=2, fill=""
        )
        # shadow ring
        self.cvs.create_oval(
            cx-r-1, cy-r+2, cx+r+1, cy+r+2,
            fill="#000000", outline=""
        )
        # button
        self.btn = self.cvs.create_oval(
            cx-r, cy-r, cx+r, cy+r,
            fill=BTN_IDLE, outline=""
        )
        # mic icon
        self.icon = self.cvs.create_text(
            cx, cy, text="🎙",
            font=("Segoe UI Emoji", 18), fill=WHITE
        )

        for item in (self.btn, self.icon):
            self.cvs.tag_bind(item, "<Button-1>", self._on_click)
            self.cvs.tag_bind(item, "<Enter>",    self._on_hover)
            self.cvs.tag_bind(item, "<Leave>",    self._on_leave)

        # ── waveform canvas ───────────────────────────────────────────────
        BAR_W, BAR_GAP, WAVE_H = 6, 3, 24
        n = len(self.rms_buf)
        wave_w = n * (BAR_W + BAR_GAP) - BAR_GAP
        self.wvs = tk.Canvas(inner, width=wave_w, height=WAVE_H,
                              bg=BG, highlightthickness=0)
        self.wvs.pack(pady=(0, 6))
        self._bar_items = []
        for i in range(n):
            x = i * (BAR_W + BAR_GAP)
            item = self.wvs.create_rectangle(
                x, WAVE_H//2 - 1, x + BAR_W, WAVE_H//2 + 1,
                fill=WAVE_DIM, outline=""
            )
            self._bar_items.append(item)
        self._BAR_W, self._BAR_GAP, self._WAVE_H = BAR_W, BAR_GAP, WAVE_H

        # separator
        tk.Frame(inner, bg=SEP, height=1).pack(fill="x")

        # ── status bar ────────────────────────────────────────────────────
        status_frame = tk.Frame(inner, bg="#0a0a0a", height=28)
        status_frame.pack(fill="x")
        status_frame.pack_propagate(False)

        self.status_var = tk.StringVar(value="loading model…")
        self.status_lbl = tk.Label(
            status_frame, textvariable=self.status_var,
            bg="#0a0a0a", fg=TEXT_DIM,
            font=("Segoe UI", 8)
        )
        self.status_lbl.pack(side="left", padx=10)

        tk.Label(status_frame, text="TR", bg="#0a0a0a", fg="#1e1e1e",
                 font=("Segoe UI", 7, "bold")).pack(side="right", padx=8)

        threading.Thread(target=self._load_model, daemon=True).start()

    # ── drag ──────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_motion(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── model ──────────────────────────────────────────────────────────────
    def _load_model(self):
        import warnings; warnings.filterwarnings("ignore")
        self.model = whisper.load_model(MODEL_SIZE)
        self.root.after(0, self._on_ready)

    def _on_ready(self):
        self.status_var.set("click to record")
        self.status_lbl.config(fg=TEXT_MID)

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
        self.recording  = True
        self.frames     = []
        self.pulse_step = 0
        self.status_var.set("recording…")
        self.status_lbl.config(fg=TEXT_HI)
        self._pulse()
        threading.Thread(target=self._record, daemon=True).start()

    # ── pulse + waveform ──────────────────────────────────────────────────
    def _pulse(self):
        if not self.recording:
            return
        t   = self.pulse_step
        osc = 0.5 + 0.5 * __import__("math").sin(t * 0.35)
        r   = int(self._r + osc * 5)
        cx, cy = self._cx, self._cy
        self.cvs.coords(self.btn,  cx-r, cy-r, cx+r, cy+r)
        self.cvs.itemconfig(self.btn, fill=BTN_REC)
        # ring glow
        rg  = r + 12
        lum = int(0x22 + osc * 0x22)
        self.cvs.coords(self.ring, cx-rg, cy-rg, cx+rg, cy+rg)
        self.cvs.itemconfig(self.ring, outline=f"#{lum:02x}0000")
        # waveform bars
        self._draw_wave()
        self.pulse_step += 1
        self.root.after(60, self._pulse)

    def _draw_wave(self):
        H    = self._WAVE_H
        BW   = self._BAR_W
        half = H // 2
        for i, item in enumerate(self._bar_items):
            rms  = self.rms_buf[i]
            h    = max(2, int(rms * 280))
            h    = min(h, half - 1)
            x    = i * (BW + self._BAR_GAP)
            lit  = rms > 0.005
            color = WAVE_LIT if lit else WAVE_DIM
            self.wvs.coords(item, x, half - h, x + BW, half + h)
            self.wvs.itemconfig(item, fill=color)

    # ── record ─────────────────────────────────────────────────────────────
    def _record(self):
        chunk          = int(SAMPLE_RATE * 0.1)
        silence_needed = int(SILENCE_DURATION / 0.1)
        max_chunks     = int(MAX_DURATION / 0.1)
        silent = 0
        started = False

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as s:
                for _ in range(max_chunks):
                    if not self.recording:
                        break
                    try:
                        data, _ = s.read(chunk)
                    except Exception:
                        break
                    self.frames.append(data.copy())
                    rms = float(np.sqrt(np.mean(data ** 2)))
                    self.rms_buf.pop(0)
                    self.rms_buf.append(rms)
                    if rms > SILENCE_THRESHOLD:
                        started = True; silent = 0
                    elif started:
                        silent += 1
                        if silent >= silence_needed:
                            break
        except Exception:
            pass

        self.recording = False
        self.root.after(0, self._transcribe)

    # ── transcribe ─────────────────────────────────────────────────────────
    def _transcribe(self):
        cx, cy, r = self._cx, self._cy, self._r
        self.cvs.coords(self.btn, cx-r, cy-r, cx+r, cy+r)
        self.cvs.itemconfig(self.btn, fill=BTN_BUSY)
        self.cvs.coords(self.ring, cx-r-12, cy-r-12, cx+r+12, cy+r+12)
        self.cvs.itemconfig(self.ring, outline=BORDER)
        # dim waveform
        for item in self._bar_items:
            self.wvs.itemconfig(item, fill=WAVE_DIM)
        self.status_var.set("transcribing…")
        self.status_lbl.config(fg=TEXT_MID)
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
