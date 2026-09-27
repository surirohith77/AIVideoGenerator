# AI Video Studio (`AivideoGeneration`)

**Local-First Script-to-Video Platform — AI Presenter & Content Video Engine**

AI Video Studio is a local-first web application that allows users to upload media assets once, create reusable AI Presenters, define style profiles, and generate 1080p MP4 videos from scripts across two primary experiences:

1. 🎤 **AI Presenter Video (Mode A)**: Deliver corporate announcements, sales demos, and training scripts with the AI Presenter talking-head throughout.
2. 🎬 **AI Content Video (Mode B)**: Hybrid YouTube/Documentary video generator combining AI Presenter intros/explanations/outros with media B-roll, uploaded assets, Ken Burns image motion, and captions.

---

## Features

- 🎤 **AI Presenter Management & HTML5 Recording**: 5-step onboarding wizard with live camera & microphone recording (`navigator.mediaDevices.getUserMedia()`), reference quality validation, and mandatory explicit legal consent.
- ⚡ **Hardware Capability Detection**: `/api/system/capabilities` detects PyTorch CUDA, Apple MPS, CPU cores, VRAM, RAM, and local AI engines.
- 📐 **Multiple Formats & Presets**: 16:9 Widescreen, 9:16 Vertical (Shorts / Reels / TikTok), and 1:1 Square. Features presets for Enterprise Presenter, YouTube Content, and YouTube Shorts.
- 🎬 **Ken Burns Motion & Audio Ducking**: Pan/zoom animation for static images, dynamic background music volume ducking, and subtitle caption overlays.
- 💾 **Presenter Caching & Cost-Aware Rendering**: Caches presenter clips by audio hash to avoid redundant rendering.
- 🏠 **100% Local-First & API-Independent**: Operates offline using FFmpeg, local fallback TTS audio, and local rule/LLM scene planners. Optional cloud APIs can be plugged in without rewriting the app.

---

## Quick Start

### 1. Backend Startup
```bash
cd backend
./venv/bin/uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Startup
```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Testing

```bash
cd backend
./venv/bin/pytest -v tests/
```
