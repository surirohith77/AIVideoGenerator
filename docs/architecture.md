# Architecture Documentation — AI Video Studio

## Overview
AI Video Studio (`AivideoGeneration`) is built on a modular, local-first, API-independent monorepo architecture. It separates UI presentation, backend orchestration, modular provider interfaces, and video rendering pipelines.

```
                  ┌──────────────────────────────┐
                  │ Next.js 14 SaaS UI Frontend  │
                  └──────────────┬───────────────┘
                                 │ REST API (JWT)
                  ┌──────────────▼───────────────┐
                  │     FastAPI Backend Core     │
                  └──────┬───────────────┬───────┘
                         │               │
      ┌──────────────────▼──┐         ┌──▼─────────────────┐
      │ Modular AI Providers│         │  FFmpeg Video      │
      │ (LLM, TTS, Storage) │         │ Rendering Engine   │
      └─────────────────────┘         └────────────────────┘
```

## Provider Abstraction Layers
To ensure complete independence from paid APIs while preserving easy future extensibility:
- **`LLMProvider`**: Interface for script analysis into scene JSON breakdown. Implemented via `LocalLLMProvider` (OpenAI-compatible Ollama/vLLM client), `FallbackRuleLLMProvider` (smart rule-based offline analyzer), and `OpenAIProvider` (placeholder).
- **`TTSProvider`**: Interface for narration audio generation. Implemented via `LocalTTSProvider` (system `say`/`espeak` or silent audio fallback) and `ElevenLabsProvider` (placeholder).
- **`StorageProvider`**: Interface for file persistence. Implemented via `LocalStorageProvider` (local filesystem) and extensible for S3/Blob storage.

## Rendering Pipeline Mechanics
1. **Scene Clip Generation**: Converts static images to motion clips using FFmpeg `zoompan` (Ken Burns zoom in/out, pan left/right/up/down) or crops/scales video clips to 16:9, 9:16, or 1:1.
2. **Audio Assembly**: Concatenates individual scene narrations and mixes background music according to style profile `music_volume`.
3. **Caption & Subtitle Processing**: Generates SRT files and overlays captions via FFmpeg `drawtext` / `subtitles`.
4. **Branding & Export**: Overlays logo watermarks and renders H.264/AAC MP4 output.
