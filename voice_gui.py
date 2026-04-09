#!/usr/bin/env python3
"""
Claude Türkçe Ses — GUI skill for Claude Code.
Anti-aliased button, waveform, stop animation.
Stays open until × is clicked; prints transcript on close.
"""
import sys
import io
import math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
import pathlib
import threading
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk
import numpy as np
import sounddevice as sd
import whisper

CLAUDE_DIR  = pathlib.Path.home() / ".claude"
OUTPUT_FILE = CLAUDE_DIR / "voicetr_output.txt"
PID_FILE    = CLAUDE_DIR / "voicetr.pid"

SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION  = 2.0
MAX_DURATION      = 60
MODEL_SIZE        = "medium"

BORDER   = "#1f1f1f"
BG       = "#0d0d0d"
TOPBAR   = "#111111"
SEP      = "#1c1c1c"
WAVE_DIM = "#1a1a1a"
WAVE_LIT = "#cc2200"
TEXT_DIM = "#3a3a3a"
TEXT_MID = "#777777"
TEXT_HI  = "#ff4433"

BTN_IDLE  = (0xb0, 0x30, 0x20)
BTN_HOVER = (0xe0, 0x40, 0x28)
BTN_REC   = (0xff, 0x33, 0x22)
BTN_BUSY  = (0x28, 0x28, 0x28)

CVS_W, CVS_H            = 300, 140
BTN_CX, BTN_CY, BTN_R  = 150, 68, 40
IMG_PAD                 = 20


def _make_circle(radius, color_rgb, glow_alpha=0):
    scale = 4
    pad   = IMG_PAD
    sz    = (radius + pad) * 2 * scale
    c     = sz // 2
    img   = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    if glow_alpha > 0:
        glow = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        gd   = ImageDraw.Draw(glow)
        gr   = (radius + pad // 2) * scale
        gd.ellipse([c-gr, c-gr, c+gr, c+gr], fill=(*color_rgb, glow_alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(radius * scale // 3))
        img  = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)
    rs   = radius * scale
    draw.ellipse([c-rs, c-rs, c+rs, c+rs], fill=(*color_rgb, 255))
    out_sz = sz // scale
    final  = img.resize((out_sz, out_sz), Image.LANCZOS)
    return ImageTk.PhotoImage(final)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class VoiceGUI:
    def __init__(self):
        self.model       = None
        self.recording   = False
        self.frames      = []
        self.pulse_step  = 0
        self.rms_buf     = [0.0] * 28
        self._img_ref    = None
        self._transcript = None   # last transcript, printed on close

        # ── root ──────────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=BORDER)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        W, H = 300, 230
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        self._drag_x = self._drag_y = 0

        # Write PID so skill script knows we're running
        CLAUDE_DIR.mkdir(exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

        # ── inner frame ───────────────────────────────────────────────────
        inner = tk.Frame(self.root, bg=BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # ── title bar ─────────────────────────────────────────────────────
        bar = tk.Frame(inner, bg=TOPBAR, height=32)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        icon_lbl  = tk.Label(bar, text="  🎙", bg=TOPBAR, fg="#cc3322",
                             font=("Segoe UI Emoji", 11))
        icon_lbl.pack(side="left")
        title_lbl = tk.Label(bar, text="claude türkçe ses", bg=TOPBAR,
                             fg="#444444", font=("Segoe UI", 9))
        title_lbl.pack(side="left", padx=(2, 0))

        # Close button — bind SEPARATELY, NOT included in drag loop
        self._close_btn = tk.Label(bar, text="  ×  ", bg=TOPBAR, fg="#2a2a2a",
                                   font=("Segoe UI", 13), cursor="hand2")
        self._close_btn.pack(side="right")
        self._close_btn.bind("<Button-1>", lambda e: self._close())
        self._close_btn.bind("<Enter>",
            lambda e: self._close_btn.config(fg="#cc4444", bg="#200000"))
        self._close_btn.bind("<Leave>",
            lambda e: self._close_btn.config(fg="#2a2a2a", bg=TOPBAR))

        # Drag only on bar background + title labels (NOT close button)
        for w in (bar, icon_lbl, title_lbl):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_motion)

        tk.Frame(inner, bg=SEP, height=1).pack(fill="x")

        # ── button canvas ─────────────────────────────────────────────────
        self.cvs = tk.Canvas(inner, width=CVS_W, height=CVS_H,
                             bg=BG, highlightthickness=0)
        self.cvs.pack()

        img = _make_circle(BTN_R, BTN_IDLE)
        self._img_ref = img
        self.btn_img  = self.cvs.create_image(BTN_CX, BTN_CY, image=img)
        self.icon     = self.cvs.create_text(BTN_CX, BTN_CY, text="🎙",
                                              font=("Segoe UI Emoji", 17),
                                              fill="white")

        for item in (self.btn_img, self.icon):
            self.cvs.tag_bind(item, "<Button-1>", self._on_click)
            self.cvs.tag_bind(item, "<Enter>",    self._on_hover)
            self.cvs.tag_bind(item, "<Leave>",    self._on_leave)

        # ── waveform ──────────────────────────────────────────────────────
        BW, GAP, WH = 6, 3, 24
        n  = len(self.rms_buf)
        ww = n * (BW + GAP) - GAP
        self.wvs = tk.Canvas(inner, width=ww, height=WH,
                              bg=BG, highlightthickness=0)
        self.wvs.pack(pady=(0, 4))
        self._bars = []
        for i in range(n):
            x = i * (BW + GAP)
            self._bars.append(self.wvs.create_rectangle(
                x, WH//2 - 1, x + BW, WH//2 + 1,
                fill=WAVE_DIM, outline=""
            ))
        self._BW, self._GAP, self._WH = BW, GAP, WH

        tk.Frame(inner, bg=SEP, height=1).pack(fill="x")

        # ── status bar ────────────────────────────────────────────────────
        sf = tk.Frame(inner, bg="#0a0a0a", height=28)
        sf.pack(fill="x")
        sf.pack_propagate(False)
        self.status_var = tk.StringVar(value="model yükleniyor…")
        self.status_lbl = tk.Label(sf, textvariable=self.status_var,
                                   bg="#0a0a0a", fg=TEXT_DIM,
                                   font=("Segoe UI", 8))
        self.status_lbl.pack(side="left", padx=10)
        tk.Label(sf, text="TR", bg="#0a0a0a", fg="#1a1a1a",
                 font=("Segoe UI", 7, "bold")).pack(side="right", padx=8)

        threading.Thread(target=self._load_model, daemon=True).start()

    # ── close ──────────────────────────────────────────────────────────────
    def _close(self):
        if PID_FILE.exists():
            PID_FILE.unlink()
        self.root.destroy()

    # ── drag ──────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_motion(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── button image ───────────────────────────────────────────────────────
    def _set_btn(self, color_rgb, radius=None, glow=0):
        r   = radius if radius is not None else BTN_R
        img = _make_circle(r, color_rgb, glow_alpha=glow)
        self._img_ref = img
        self.cvs.itemconfig(self.btn_img, image=img)

    # ── model ──────────────────────────────────────────────────────────────
    def _load_model(self):
        import warnings; warnings.filterwarnings("ignore")
        self.model = whisper.load_model(MODEL_SIZE)
        self.root.after(0, self._on_ready)

    def _on_ready(self):
        self.status_var.set("konuşmak için tıkla")
        self.status_lbl.config(fg=TEXT_MID)

    # ── hover ──────────────────────────────────────────────────────────────
    def _on_hover(self, e):
        if not self.recording and self.model:
            self._set_btn(BTN_HOVER)

    def _on_leave(self, e):
        if not self.recording:
            self._set_btn(BTN_IDLE)

    # ── click ──────────────────────────────────────────────────────────────
    def _on_click(self, e):
        if not self.model or self.recording:
            return
        self.recording  = True
        self.frames     = []
        self.pulse_step = 0
        self.status_var.set("kayıt yapılıyor…")
        self.status_lbl.config(fg=TEXT_HI)
        self._pulse()
        threading.Thread(target=self._record, daemon=True).start()

    # ── pulse ──────────────────────────────────────────────────────────────
    def _pulse(self):
        if not self.recording:
            return
        osc  = 0.5 + 0.5 * math.sin(self.pulse_step * 0.4)
        r    = int(BTN_R + osc * 5)
        glow = int(60 + osc * 80)
        self._set_btn(BTN_REC, radius=r, glow=glow)
        self._draw_wave()
        self.pulse_step += 1
        self.root.after(65, self._pulse)

    def _draw_wave(self):
        H = self._WH; half = H // 2; BW = self._BW
        for i, item in enumerate(self._bars):
            rms   = self.rms_buf[i]
            h     = max(2, min(int(rms * 300), half - 1))
            x     = i * (BW + self._GAP)
            color = WAVE_LIT if rms > 0.005 else WAVE_DIM
            self.wvs.coords(item, x, half - h, x + BW, half + h)
            self.wvs.itemconfig(item, fill=color)

    # ── record ─────────────────────────────────────────────────────────────
    def _record(self):
        chunk          = int(SAMPLE_RATE * 0.1)
        silence_needed = int(SILENCE_DURATION / 0.1)
        max_chunks     = int(MAX_DURATION / 0.1)
        silent = 0; started = False
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                 dtype="float32") as s:
                for _ in range(max_chunks):
                    if not self.recording:
                        break
                    try:
                        data, _ = s.read(chunk)
                    except Exception:
                        break
                    self.frames.append(data.copy())
                    rms = float(np.sqrt(np.mean(data ** 2)))
                    self.rms_buf.pop(0); self.rms_buf.append(rms)
                    if rms > SILENCE_THRESHOLD:
                        started = True; silent = 0
                    elif started:
                        silent += 1
                        if silent >= silence_needed:
                            break
        except Exception:
            pass
        self.recording = False
        self.root.after(0, self._stop_anim)

    # ── stop animation ─────────────────────────────────────────────────────
    def _stop_anim(self, step=0):
        STEPS = 10
        if step >= STEPS:
            self._transcribe()
            return
        t     = step / (STEPS - 1)
        ease  = t * t * (3 - 2 * t)
        color = _lerp(BTN_REC, BTN_BUSY, ease)
        r     = int(BTN_R + 4 - ease * 8)
        self._set_btn(color, radius=max(r, BTN_R - 4))
        for item in self._bars:
            self.wvs.itemconfig(item, fill=WAVE_DIM)
        self.status_var.set("işleniyor…")
        self.status_lbl.config(fg=TEXT_DIM)
        self.root.after(45, lambda: self._stop_anim(step + 1))

    # ── transcribe ─────────────────────────────────────────────────────────
    def _transcribe(self):
        self._set_btn(BTN_BUSY)
        self.status_var.set("transkript alınıyor…")
        self.status_lbl.config(fg=TEXT_DIM)
        threading.Thread(target=self._do_transcribe, daemon=True).start()

    def _do_transcribe(self):
        if self.frames:
            audio = np.concatenate(self.frames, axis=0).flatten()
            if len(audio) / SAMPLE_RATE >= 0.5:
                import warnings; warnings.filterwarnings("ignore")
                result = self.model.transcribe(audio, language="tr", fp16=False)
                self._transcript = result["text"].strip()
        self.root.after(0, self._reset)

    # ── reset to ready ─────────────────────────────────────────────────────
    def _reset(self):
        self.rms_buf = [0.0] * 28
        self._draw_wave()
        if self._transcript:
            # Write for skill script to pick up
            try:
                OUTPUT_FILE.write_text(self._transcript, encoding="utf-8")
            except Exception:
                pass
            # Copy to clipboard
            try:
                import pyperclip
                pyperclip.copy(self._transcript)
            except Exception:
                pass
            # Show success: green flash then reset
            self.status_var.set("kopyalandi")
            self.status_lbl.config(fg="#55aa66")
            self._success_flash()
        else:
            self._set_btn(BTN_IDLE)
            self.status_var.set("konuşmak için tıkla")
            self.status_lbl.config(fg=TEXT_MID)

    # ── success flash ──────────────────────────────────────────────────────
    def _success_flash(self, step=0):
        BTN_GREEN = (0x22, 0xaa, 0x55)
        HALF = 5
        TOTAL = HALF * 2
        if step >= TOTAL:
            self._set_btn(BTN_IDLE)
            self._transcript = None
            self.status_var.set("konuşmak için tıkla")
            self.status_lbl.config(fg=TEXT_MID)
            return
        t = (step % HALF) / (HALF - 1)
        color = _lerp(BTN_IDLE, BTN_GREEN, t) if step < HALF else _lerp(BTN_GREEN, BTN_IDLE, t)
        self._set_btn(color)
        self.root.after(90, lambda: self._success_flash(step + 1))


def main():
    VoiceGUI().root.mainloop()


if __name__ == "__main__":
    main()
