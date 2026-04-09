# 🎙️ Claude Turkish Voice | Claude Türkçe Ses

🇹🇷 [Türkçe](#türkçe) &nbsp;|&nbsp; 🇬🇧 [English](#english)

---

## Türkçe

Claude Code için Türkçe sesli giriş. `/voicetr` yaz, butona tıkla, konuş, × ile gönder.

### Nasıl çalışır

- 🎤 Butona tıkla → Türkçe konuş → sessizlikte otomatik durur
- 🧠 Whisper ile yerel transkripsiyon (API anahtarı gerekmez)
- 🪟 Pencere açık kalır — **×** ile kapatınca transcript Claude'a gider

### Gereksinimler

- Windows 10/11
- Python 3.10+

### Kurulum

```
install.bat
```

İlk çalıştırmada Whisper `medium` modeli indirilir (~1.5GB).

### Kullanım

Claude Code içinde `/voicetr` yaz → pencere açılır → butona tıkla → konuş → **×** ile kapat → Claude cevap verir.

---

## English

Turkish voice input for Claude Code. Type `/voicetr`, click the button, speak, close with × to send.

### How it works

- 🎤 Click button → speak Turkish → auto-stops on silence
- 🧠 Local Whisper transcription (no API key needed)
- 🪟 Window stays open — closing with **×** sends the transcript to Claude

### Requirements

- Windows 10/11
- Python 3.10+

### Install

```
install.bat
```

First run downloads the Whisper `medium` model (~1.5GB).

### Usage

Type `/voicetr` in Claude Code → window opens → click button → speak → close with **×** → Claude responds.

### Files

| File | Description |
|------|-------------|
| `voice_gui.py` | GUI — dark window, anti-aliased button, waveform bars |
| `install.py` | Generates skill file with correct local paths |
| `install.bat` | One-click setup |
