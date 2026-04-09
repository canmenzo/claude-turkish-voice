# 🎙️ Claude Turkish Voice

> 🇹🇷 [Türkçe](#türkçe) &nbsp;|&nbsp; 🇬🇧 [English](#english)

---

## Türkçe

Claude Code için Türkçe sesli giriş — OpenAI Whisper kullanır. `/voice` yaz, Türkçe konuş, sözlerin otomatik olarak mesaja dönüşür.

### Nasıl çalışır

- 🎤 Sessizlik algılanana kadar mikrofondan kaydeder
- 🧠 Whisper'ı yerel çalıştırır (API anahtarı gerekmez)
- ⚡ Transkripti doğrudan Claude Code'a mesaj olarak iletir

### Gereksinimler

- Windows 10/11
- Python 3.10+

### Kurulum

```
install.bat
```

Bağımlılıkları yükler ve `/voice` skill'ini Claude Code'a kaydeder.
İlk çalıştırmada Whisper `medium` modeli indirilir (~1.5GB).

### Kullanım

Claude Code'da `/voice` yazıp Enter'a bas. Türkçe konuş. Claude ne dediğini anlayıp cevap verir.

### Doğruluk

`medium` model kullanır. Daha iyi doğruluk için `voice_capture.py` içinde `MODEL_SIZE = "medium"` → `"large"` yap (daha yavaş).

---

## English

Turkish voice-to-text for Claude Code using OpenAI Whisper. Type `/voice` in Claude Code, speak Turkish, and your words become the prompt — automatically.

### How it works

- 🎤 Records from your mic until silence is detected
- 🧠 Runs OpenAI Whisper locally (no API key needed)
- ⚡ Outputs Turkish transcript directly into Claude Code as your message

### Requirements

- Windows 10/11
- Python 3.10+

### Install

```
install.bat
```

This installs Python dependencies and registers the `/voice` skill in Claude Code.

First run downloads the Whisper `medium` model (~1.5GB).

### Usage

Type `/voice` and press Enter in Claude Code. Speak in Turkish. Claude will respond to what you said.

### Standalone (clipboard)
```
python turkish_whisper.py
```
Press Enter to start, Enter again to stop. Transcript is copied to clipboard.

### Files

| File | Description |
|------|-------------|
| `voice_capture.py` | Claude Code integration — records until silence, prints transcript |
| `turkish_whisper.py` | Standalone interactive version with clipboard support |
| `.claude/commands/voice.md` | Claude Code skill definition |
| `install.bat` | One-click setup |

### Accuracy

Uses Whisper `medium` model. Change `MODEL_SIZE = "medium"` to `"large"` in either script for better accuracy (slower).
