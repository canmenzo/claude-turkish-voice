#!/usr/bin/env python3
"""
Claude Türkçe Ses — Modern AI UI v2
Dark navy theme, sonar rings, gradient waveform, spinner arc.
"""
import sys, io, math, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
import numpy as np
import sounddevice as sd
import whisper

# ── Audio ──────────────────────────────────────────────────────────────────
SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION  = 2.0
MAX_DURATION      = 60
MODEL_SIZE        = "medium"

# ── Palette — dark navy, purple accent (Claude/ChatGPT vibe) ───────────────
BG_HEX   = "#0c0c12"
_BG      = (12, 12, 18)
STROKE   = "#191926"
SURF     = "#10101a"

IDLE_RGB    = (46, 44, 72)      # dim purple-grey
HOVER_RGB   = (88,  60, 195)    # purple on hover
ACCENT_RGB  = (108, 72, 228)    # main purple
REC_RGB     = (210, 48,  48)    # recording red
BUSY_RGB    = (30,  30,  46)    # processing (dark)
OK_RGB      = (30, 172,  88)    # success green

ACCENT_HEX  = "#6c48e4"
REC_HEX     = "#d23030"

TXT_HI   = "#d4d6f0"
TXT_MID  = "#44466a"
TXT_DIM  = "#1e1e30"
TXT_REC  = "#ff6464"
TXT_OK   = "#3ed882"
TXT_ACC  = "#9278f0"

# ── Layout ─────────────────────────────────────────────────────────────────
WIN_W, WIN_H = 360, 374
TOPBAR_H     = 34
CVS_W, CVS_H = 360, 248
STAT_H       = 44
BOT_H        = 46

BTN_CX, BTN_CY, BTN_R = 180, 110, 52
GLOW_STEPS  = 28
GLOW_EXT    = 62

# Sonar rings (recording animation)
RING_N     = 3
RING_MIN_R = BTN_R + 4
RING_MAX_R = BTN_R + 80

# Waveform (inside main canvas)
WAVE_N   = 30
WAVE_BW  = 4
WAVE_GAP = 3
WAVE_Y   = 208
WAVE_MH  = 22


# ── Helpers ────────────────────────────────────────────────────────────────
def _lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _hex(c):
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def _make_btn(radius, rgb):
    """Anti-aliased PIL circle baked onto BG color."""
    sc, pd = 4, 4
    sz = (radius + pd) * 2 * sc
    c  = sz // 2
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse(
        [c - radius*sc, c - radius*sc, c + radius*sc, c + radius*sc],
        fill=(*rgb, 255)
    )
    out  = sz // sc
    flat = Image.new("RGB", (out, out), _BG)
    rsz  = img.resize((out, out), Image.LANCZOS)
    flat.paste(rsz, mask=rsz.split()[3])
    return ImageTk.PhotoImage(flat)


# ── Main GUI ───────────────────────────────────────────────────────────────
class VoiceGUI:
    def __init__(self):
        self.model       = None
        self.recording   = False
        self.frames      = []
        self.rms_buf     = [0.0] * WAVE_N
        self._img_ref    = None
        self._transcript = None
        self._tick       = 0
        self._ring_phase = 0.0
        self._spinning   = False
        self._loading    = True

        # ── Root window ────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=STROKE)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{WIN_W}x{WIN_H}+{(sw-WIN_W)//2}+{(sh-WIN_H)//2}")
        self._dx = self._dy = 0

        # ── Inner frame (1 px border via root bg) ──────────────────────────
        inner = tk.Frame(self.root, bg=BG_HEX)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Title bar ───────────────────────────────────────────────────────
        bar = tk.Frame(inner, bg=BG_HEX, height=TOPBAR_H)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        title = tk.Label(bar, text="  voice", bg=BG_HEX, fg=TXT_DIM,
                         font=("Segoe UI", 9), cursor="fleur")
        title.pack(side="left", padx=(2, 0))

        self._xbtn = tk.Label(bar, text="✕", bg=BG_HEX, fg=TXT_DIM,
                              font=("Segoe UI", 10), cursor="hand2", padx=14)
        self._xbtn.pack(side="right")
        self._xbtn.bind("<Button-1>", lambda e: self.root.destroy())
        self._xbtn.bind("<Enter>",    lambda e: self._xbtn.config(fg="#e05060", bg="#18080c"))
        self._xbtn.bind("<Leave>",    lambda e: self._xbtn.config(fg=TXT_DIM,  bg=BG_HEX))

        for w in (bar, title):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)

        tk.Frame(inner, bg=STROKE, height=1).pack(fill="x")

        # ── Main canvas ─────────────────────────────────────────────────────
        self.cvs = tk.Canvas(inner, width=CVS_W, height=CVS_H,
                             bg=BG_HEX, highlightthickness=0)
        self.cvs.pack()

        # Z-order (back → front): rings → glow → wave bars → button → spinner → icon

        # Sonar rings — outline-only ovals, visible during recording
        self._rings = [
            self.cvs.create_oval(0, 0, 0, 0, fill="", outline=BG_HEX, width=1)
            for _ in range(RING_N)
        ]

        # Glow ovals — soft radial fill behind button
        self._glow = [
            self.cvs.create_oval(0, 0, 0, 0, fill=BG_HEX, outline="")
            for _ in range(GLOW_STEPS)
        ]

        # Waveform bars
        total_w = WAVE_N * (WAVE_BW + WAVE_GAP) - WAVE_GAP
        wx0 = (CVS_W - total_w) // 2
        self._bars = []
        for i in range(WAVE_N):
            x = wx0 + i * (WAVE_BW + WAVE_GAP)
            bid = self.cvs.create_rectangle(
                x, WAVE_Y - 2, x + WAVE_BW, WAVE_Y + 2,
                fill=TXT_DIM, outline=""
            )
            self._bars.append((bid, x))

        # Button image (PIL AA circle)
        img = _make_btn(BTN_R, IDLE_RGB)
        self._img_ref = img
        self._btn_id  = self.cvs.create_image(BTN_CX, BTN_CY, image=img)

        # Spinner arc (around button, processing state)
        AR = BTN_R + 14
        self._spinner = self.cvs.create_arc(
            BTN_CX - AR, BTN_CY - AR, BTN_CX + AR, BTN_CY + AR,
            start=90, extent=110, style="arc",
            outline=BG_HEX, width=2
        )
        self._spin_angle = 90

        # Mic / state icon (topmost)
        self._icon = self.cvs.create_text(
            BTN_CX, BTN_CY, text="🎙",
            font=("Segoe UI Emoji", 20), fill=TXT_HI
        )

        # Bind button & icon
        for item in (self._btn_id, self._icon):
            self.cvs.tag_bind(item, "<Button-1>", self._on_click)
            self.cvs.tag_bind(item, "<Enter>",    self._on_enter)
            self.cvs.tag_bind(item, "<Leave>",    self._on_leave)

        tk.Frame(inner, bg=STROKE, height=1).pack(fill="x")

        # ── Status area ─────────────────────────────────────────────────────
        stat = tk.Frame(inner, bg=BG_HEX, height=STAT_H)
        stat.pack(fill="x")
        stat.pack_propagate(False)

        self._sv  = tk.StringVar(value="model yükleniyor…")
        self._slbl = tk.Label(stat, textvariable=self._sv,
                              bg=BG_HEX, fg=TXT_DIM,
                              font=("Segoe UI", 10))
        self._slbl.pack(expand=True)

        tk.Frame(inner, bg=STROKE, height=1).pack(fill="x")

        # ── Bottom bar — send button ─────────────────────────────────────
        bot = tk.Frame(inner, bg=SURF, height=BOT_H)
        bot.pack(fill="x")
        bot.pack_propagate(False)

        # Canvas-drawn send button for clean styling
        self._sbcvs = tk.Canvas(bot, width=130, height=30,
                                bg=SURF, highlightthickness=0,
                                cursor="hand2")
        self._sbcvs.place(relx=0.5, rely=0.5, anchor="center")
        self._sb_bg  = self._sbcvs.create_rectangle(
            0, 0, 130, 30, fill=TXT_DIM, outline="")
        self._sb_txt = self._sbcvs.create_text(
            65, 15, text="gönder →",
            fill=BG_HEX, font=("Segoe UI", 9, "bold"))
        self._sbcvs.bind("<Button-1>", self._send)
        self._send_active = False

        # Start model load + loading animation
        threading.Thread(target=self._load_model, daemon=True).start()
        self._loading_anim()

    # ── Drag ───────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    # ── Loading pulse (while model loads) ──────────────────────────────────
    def _loading_anim(self):
        if not self._loading:
            return
        osc = 0.5 + 0.5 * math.sin(self._tick * 0.12)
        g   = int(20 + osc * 38)
        self._set_btn(IDLE_RGB, glow_alpha=g)
        self._tick += 1
        self.root.after(60, self._loading_anim)

    # ── Model ──────────────────────────────────────────────────────────────
    def _load_model(self):
        import warnings; warnings.filterwarnings("ignore")
        self.model = whisper.load_model(MODEL_SIZE)
        self.root.after(0, self._on_ready)

    def _on_ready(self):
        self._loading = False
        self._tick    = 0
        self._set_btn(IDLE_RGB)
        self._sv.set("tıkla, konuş")
        self._slbl.config(fg=TXT_MID)

    # ── Glow ───────────────────────────────────────────────────────────────
    def _set_btn(self, rgb, radius=None, glow_alpha=0):
        r   = radius if radius is not None else BTN_R
        img = _make_btn(r, rgb)
        self._img_ref = img
        self.cvs.itemconfig(self._btn_id, image=img)

        cx, cy = BTN_CX, BTN_CY
        for i, oval in enumerate(self._glow):
            if glow_alpha == 0:
                self.cvs.coords(oval, 0, 0, 0, 0)
                continue
            t      = i / (GLOW_STEPS - 1)          # 0 = outermost, 1 = innermost
            oval_r = r + int(GLOW_EXT * (1.0 - t))
            intens = (glow_alpha / 255.0) * (t ** 1.4)
            c      = _lerp(_BG, rgb, intens)
            self.cvs.coords(oval, cx-oval_r, cy-oval_r, cx+oval_r, cy+oval_r)
            self.cvs.itemconfig(oval, fill=_hex(c))

    # ── Sonar rings ────────────────────────────────────────────────────────
    def _draw_rings(self, rgb, visible=True):
        if not visible:
            for ring in self._rings:
                self.cvs.itemconfig(ring, outline=BG_HEX)
            return
        cx, cy = BTN_CX, BTN_CY
        step = 1.0 / RING_N
        for i, ring in enumerate(self._rings):
            phase = (self._ring_phase + i * step) % 1.0
            r     = int(RING_MIN_R + phase * (RING_MAX_R - RING_MIN_R))
            alpha = (1.0 - phase) ** 2     # fade as it expands
            c     = _lerp(_BG, rgb, alpha * 0.6)
            w     = max(1, int((1.0 - phase) * 2.5))
            self.cvs.coords(ring, cx-r, cy-r, cx+r, cy+r)
            self.cvs.itemconfig(ring, outline=_hex(c), width=w)

    # ── Waveform ───────────────────────────────────────────────────────────
    def _draw_wave(self, active=True):
        for i, (bid, x) in enumerate(self._bars):
            rms = self.rms_buf[i]
            if active and rms > 0.002:
                h = max(2, min(int(rms * 340), WAVE_MH))
                t = min(rms / 0.06, 1.0)   # gradient: dim → accent
                c = _lerp(IDLE_RGB, ACCENT_RGB, t)
                self.cvs.coords(bid, x, WAVE_Y-h, x+WAVE_BW, WAVE_Y+h)
                self.cvs.itemconfig(bid, fill=_hex(c))
            else:
                self.cvs.coords(bid, x, WAVE_Y-2, x+WAVE_BW, WAVE_Y+2)
                self.cvs.itemconfig(bid, fill=TXT_DIM)

    # ── Spinner arc (processing) ───────────────────────────────────────────
    def _spin_start(self):
        self._spinning   = True
        self._spin_angle = 90
        AR = BTN_R + 14
        self.cvs.coords(self._spinner,
                        BTN_CX-AR, BTN_CY-AR, BTN_CX+AR, BTN_CY+AR)
        self._do_spin()

    def _spin_stop(self):
        self._spinning = False
        self.cvs.itemconfig(self._spinner, outline=BG_HEX)

    def _do_spin(self):
        if not self._spinning:
            return
        self._spin_angle = (self._spin_angle - 9) % 360
        self.cvs.itemconfig(self._spinner,
                            start=self._spin_angle, extent=115,
                            outline=ACCENT_HEX)
        self.root.after(28, self._do_spin)

    # ── Hover ──────────────────────────────────────────────────────────────
    def _on_enter(self, e):
        if not self.recording and self.model and not self._loading:
            self._set_btn(HOVER_RGB, glow_alpha=55)

    def _on_leave(self, e):
        if not self.recording and not self._loading:
            self._set_btn(IDLE_RGB)

    # ── Click — start recording ────────────────────────────────────────────
    def _on_click(self, e):
        if not self.model or self.recording or self._loading:
            return
        self.recording    = True
        self.frames       = []
        self._tick        = 0
        self._ring_phase  = 0.0
        self._transcript  = None
        self._set_send(False)
        self._sv.set("dinliyorum…")
        self._slbl.config(fg=TXT_REC)
        self.cvs.itemconfig(self._icon, text="■")
        self._rec_anim()
        threading.Thread(target=self._record, daemon=True).start()

    # ── Recording animation ────────────────────────────────────────────────
    def _rec_anim(self):
        if not self.recording:
            return
        t   = self._tick
        osc = 0.5 + 0.5 * math.sin(t * 0.32)
        r   = int(BTN_R + osc * 4)
        g   = int(65 + osc * 145)
        self._set_btn(REC_RGB, radius=r, glow_alpha=g)
        self._ring_phase = (self._ring_phase + 0.011) % 1.0
        self._draw_rings(REC_RGB, visible=True)
        self._draw_wave(active=True)
        self._tick += 1
        self.root.after(52, self._rec_anim)

    # ── Record thread ──────────────────────────────────────────────────────
    def _record(self):
        chunk  = int(SAMPLE_RATE * 0.1)
        sil_n  = int(SILENCE_DURATION / 0.1)
        max_c  = int(MAX_DURATION / 0.1)
        silent = 0; started = False
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="float32") as s:
                for _ in range(max_c):
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
                        if silent >= sil_n:
                            break
        except Exception:
            pass
        self.recording = False
        self.root.after(0, self._stop_anim)

    # ── Stop recording animation ───────────────────────────────────────────
    def _stop_anim(self, step=0):
        STEPS = 9
        if step >= STEPS:
            self._draw_rings(REC_RGB, visible=False)
            for _, bid in [(b, b) for b, _ in self._bars]:
                pass  # reset in _draw_wave below
            self._draw_wave(active=False)
            self.cvs.itemconfig(self._icon, text="…")
            self._sv.set("işleniyor…")
            self._slbl.config(fg=TXT_DIM)
            self._transcribe()
            return
        t    = step / (STEPS - 1)
        ease = t * t * (3 - 2 * t)
        r    = max(BTN_R - int(ease * 7), BTN_R - 7)
        self._set_btn(_lerp(REC_RGB, BUSY_RGB, ease), radius=r, glow_alpha=0)
        self._draw_wave(active=False)
        self.root.after(38, lambda: self._stop_anim(step + 1))

    # ── Transcribe ─────────────────────────────────────────────────────────
    def _transcribe(self):
        self._set_btn(BUSY_RGB)
        self._spin_start()
        threading.Thread(target=self._do_transcribe, daemon=True).start()

    def _do_transcribe(self):
        if self.frames:
            audio = np.concatenate(self.frames, axis=0).flatten()
            if len(audio) / SAMPLE_RATE >= 0.5:
                import warnings; warnings.filterwarnings("ignore")
                result = self.model.transcribe(audio, language="tr", fp16=False)
                self._transcript = result["text"].strip()
                try:
                    import pyperclip; pyperclip.copy(self._transcript)
                except Exception:
                    pass
        self.root.after(0, self._on_done)

    def _on_done(self):
        self._spin_stop()
        self.rms_buf = [0.0] * WAVE_N
        self._draw_wave(active=False)
        self.cvs.itemconfig(self._icon, text="🎙")
        if self._transcript:
            self._flash_ok()
            self._set_send(True)
            self._sv.set("kopyalandı ✓")
            self._slbl.config(fg=TXT_OK)
        else:
            self._set_btn(IDLE_RGB)
            self._sv.set("tıkla, konuş")
            self._slbl.config(fg=TXT_MID)

    # ── Success flash ──────────────────────────────────────────────────────
    def _flash_ok(self, step=0):
        HALF, TOTAL = 6, 12
        if step >= TOTAL:
            self._set_btn(IDLE_RGB)
            return
        t   = (step % HALF) / (HALF - 1)
        rgb = _lerp(IDLE_RGB, OK_RGB, t) if step < HALF else _lerp(OK_RGB, IDLE_RGB, t)
        g   = int(55 * math.sin(math.pi * step / TOTAL))
        self._set_btn(rgb, glow_alpha=g)
        self.root.after(75, lambda: self._flash_ok(step + 1))

    # ── Send button ────────────────────────────────────────────────────────
    def _set_send(self, active):
        self._send_active = active
        if active:
            self._sbcvs.itemconfig(self._sb_bg,  fill=ACCENT_HEX)
            self._sbcvs.itemconfig(self._sb_txt, fill=TXT_HI)
            self._sbcvs.bind("<Enter>",
                lambda e: self._sbcvs.itemconfig(self._sb_bg, fill="#8060f0"))
            self._sbcvs.bind("<Leave>",
                lambda e: self._sbcvs.itemconfig(self._sb_bg, fill=ACCENT_HEX))
        else:
            self._sbcvs.itemconfig(self._sb_bg,  fill=TXT_DIM)
            self._sbcvs.itemconfig(self._sb_txt, fill=BG_HEX)
            self._sbcvs.unbind("<Enter>")
            self._sbcvs.unbind("<Leave>")

    def _send(self, e=None):
        if not self._send_active or not self._transcript:
            return
        print(self._transcript, flush=True)
        script = sys.argv[0]
        def _relaunch():
            import subprocess
            subprocess.Popen(
                [sys.executable, script],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        threading.Timer(3.0, _relaunch).start()
        self.root.destroy()


def main():
    VoiceGUI().root.mainloop()


if __name__ == "__main__":
    main()
