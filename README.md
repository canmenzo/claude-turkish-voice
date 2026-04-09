# 🎙️ Claude Turkish Voice | Claude Türkçe Ses

🇹🇷 [Türkçe](#türkçe) &nbsp;|&nbsp; 🇬🇧 [English](#english)

---

## Türkçe

Claude Code için Türkçe sesli giriş. `/voicetr` yaz → butona tıkla → konuş → **gönder →** ile Claude'a ilet.

### Nasıl çalışır

- 🎤 Butona tıkla → konuş → sessizlikte otomatik durur
- 🧠 Whisper ile yerel transkripsiyon (API anahtarı gerekmez)
- 📋 Transcript otomatik panoya kopyalanır
- **gönder** butonuna bas → transcript Claude'a gider, pencere kapanır
- × sadece kapatır, göndermez

### Gereksinimler

- Windows 10/11
- Python 3.10+

### Kurulum

```
install.bat
```

İlk çalıştırmada Whisper `medium` modeli indirilir (~1.5GB).

### Kullanım

Claude Code içinde `/voicetr` yaz → kaydet → **gönder →**

---

## English

Turkish voice input for Claude Code. Type `/voicetr` → click record → speak → click **gönder →** to send to Claude.

### How it works

- 🎤 Click button → speak Turkish → auto-stops on silence
- 🧠 Local Whisper transcription (no API key needed)
- 📋 Transcript auto-copied to clipboard
- Click **gönder →** → transcript sent to Claude, window closes
- × just closes without sending

### Requirements

- Windows 10/11
- Python 3.10+

### Install

```
install.bat
```

First run downloads the Whisper `medium` model (~1.5GB).

### Usage

Type `/voicetr` in Claude Code → record → click **gönder →**

### Files

| File | Description |
|------|-------------|
| `voice_gui.py` | GUI — dark window, anti-aliased button, waveform, send button |
| `install.py` | Generates skill file with correct local paths |
| `install.bat` | One-click setup |
