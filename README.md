# 🎙️ Claude Turkish Voice | Claude Türkçe Ses

> 🇹🇷 [Türkçe](#türkçe) &nbsp;|&nbsp; 🇬🇧 [English](#english)

---

## Türkçe

Claude Code için Türkçe sesli giriş. `/voicetr` yaz, butona tıkla, konuş — sözlerin otomatik olarak Claude'a iletilir.

### Nasıl çalışır

- 🎤 Butona tıkla, Türkçe konuş
- 🔇 Sessizlik algılanınca otomatik durur
- 🧠 Whisper ile yerel transkripsiyon (API anahtarı gerekmez)
- ⚡ Transcript doğrudan Claude Code prompt'una gelir

### Gereksinimler

- Windows 10/11
- Python 3.10+

### Kurulum

```
install.bat
```

İlk çalıştırmada Whisper `medium` modeli indirilir (~1.5GB).

### Kullanım

- **`/voicetr`** — küçük koyu pencere açılır, kırmızı butona tıkla, konuş, kapanır
- **`/voice`** — terminal tabanlı fallback versiyon

### Doğruluk ayarı

`voice_capture.py` ve `voice_gui.py` içinde `MODEL_SIZE = "medium"` → `"large"` yaparak doğruluğu artırabilirsin (daha yavaş).

---

## English

Turkish voice input for Claude Code. Type `/voicetr`, click the button, speak — your words go straight into Claude.

### How it works

- 🎤 Click the button, speak Turkish
- 🔇 Auto-stops on silence detection
- 🧠 Local Whisper transcription (no API key needed)
- ⚡ Transcript feeds directly into Claude Code as your prompt

### Requirements

- Windows 10/11
- Python 3.10+

### Install

```
install.bat
```

First run downloads the Whisper `medium` model (~1.5GB).

### Usage

- **`/voicetr`** — opens a small dark GUI window with animated record button
- **`/voice`** — terminal-based fallback

### Files

| File | Description |
|------|-------------|
| `voice_gui.py` | GUI skill — dark window, anti-aliased button, waveform |
| `voice_capture.py` | Terminal fallback — records until silence, prints transcript |
| `install.py` | Generates skill files with correct local paths |
| `install.bat` | One-click setup |
