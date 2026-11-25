# Setup & Installation Guide

This guide walks you through setting up `faceless-shorts` on a Windows or Linux workstation for high-speed local video generation.

---

## 📋 Prerequisites

Before running the engine, ensure the following core binaries are installed and accessible on your system `PATH`:

1. **PowerShell 5.1+ or PowerShell Core 7+** (Windows default).
2. **Python 3.10 – 3.12** (64-bit).
3. **Node.js 22+** (required for native ES modules and headless Chrome CDP protocol; no npm packages required).
4. **Google Chrome, Chromium, or Microsoft Edge** (installed in default location, e.g. `C:\Program Files\Google\Chrome\Application\chrome.exe`).
5. **FFmpeg with NVENC Support**:
   - Verify GPU encoder support by running:
     ```powershell
     ffmpeg -encoders | Select-String "h264_nvenc"
     ```
   - *If an NVIDIA GPU is not present, FFmpeg automatically falls back to CPU encoding (`libx264`), which works identically but renders slightly slower.*
6. **(Optional) Local Ollama**:
   - For offline AI script synthesis from a topic prompt, install [Ollama](https://ollama.com/) with `llama3` or `mistral`. If omitted, the engine uses its built-in structured script generator.

---

## 🐍 Python Virtual Environment Setup

### 1. Create and Activate Virtualenv

```powershell
cd D:\AI-Projects\faceless-shorts-skill\faceless-shorts
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Required Python Packages

Install the lightweight voice, alignment, and procedural audio libraries:

```powershell
pip install --upgrade pip
pip install faster-whisper edge-tts numpy scipy soundfile kokoro-onnx
```

> **Shared Virtualenv Note**: If you already maintain a dedicated Python virtualenv in a companion project (such as `D:\AI-Projects\stream-clips\.streamclips\venv`), you can point `faceless-shorts` to that environment without creating a duplicate venv.

---

## ⚙️ Environment Configuration

To prevent character encoding glitches on Windows, add the following environment variables to your PowerShell profile (`$PROFILE`) or pass them in your terminal session:

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
```

---

## 🩺 System Verification (`doctor`)

Run the automated diagnostics command to verify your environment:

```powershell
.\faceless.ps1 doctor
```

### Expected Output:
```text
=== Faceless Shorts Environment Doctor ===
[OK] PowerShell: 5.1.x / 7.x
[OK] Python: 3.10+ (PYTHONUTF8=1 active)
[OK] Faster-Whisper: Ready
[OK] Edge-TTS / Kokoro: Ready
[OK] Node.js: v22.x
[OK] Google Chrome: Detected
[OK] FFmpeg: Installed (h264_nvenc hardware acceleration enabled)
All systems operational!
```

---

## 🎬 Running Your First Video

Generate and render your first test video from a topic:

```powershell
.\faceless.ps1 create --topic "Why Airplanes Avoid Flying Over the Pacific" --style paper-atlas --render
```

The finished video will be ready in:
```text
data/YYYY-MM-DD/why-airplanes-avoid-flying-over-the-pacific/renders/out.mp4
```
