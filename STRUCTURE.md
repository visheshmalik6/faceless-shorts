# Repository Structure & Architecture Reference

This document provides a complete directory map and component-by-component reference for the `faceless-shorts` codebase.

---

## 🗂️ Complete Directory Tree

```text
faceless-shorts/
├── .agents/
│   └── skills/
│       ├── caption-animation/      # Whisper word-level pop/karaoke caption skill
│       ├── countdown-video/        # Kinetic #3→#2→#1 countdown timer & progress skill
│       ├── javascript-animation/   # 2D canvas procedural motion manual
│       ├── lower-thirds/           # Broadcast lower-third banner & safe-area skill
│       ├── map-animation/          # Vintage & vector map routing skill
│       ├── short-form-video/       # Retention, hook, & loop design manual
│       └── soundtrack/             # Procedural audio & cut-on-the-beat check skill
├── scripts/
│   ├── estimate.py                 # Offline fallback timestamp estimator (zero-whisper mode)
│   ├── faceless.py                 # Core Python orchestration engine (TTS, Whisper, SFX, shots)
│   ├── new_video.sh                # Shell project scaffolder
│   ├── py                          # Python environment wrapper
│   ├── selftest.sh                 # Unit self-test runner
│   ├── setup.sh                    # Dependency installation script
│   ├── voice.py                    # Multi-engine TTS voice synthesis bridge
│   └── words.py                    # Faster-Whisper word-level audio alignment
├── shared/
│   └── world.geojson               # Bundled global coastline & border vector geometry
├── styles/
│   ├── deep-dive/                  # 3D anatomy/X-ray explainer template (isolated)
│   ├── inside-out/                 # 2D flat X-ray explainer template
│   ├── night-file/                 # 3D mystery/crime noir template (isolated)
│   ├── paper-atlas/                # 2D vintage cut-paper & cartography template (flagship)
│   ├── stick-story/                # 2D kinetic stick-figure & countdown template (flagship)
│   └── tall-tale/                  # 2D stylized illustrated true story template (flagship)
├── .gitignore                      # Git exclusion rules for clean repository state
├── CHALLENGES.md                   # Engineering hurdles and technical countermeasures
├── faceless.ps1                    # Main PowerShell CLI entry point
├── PIPELINE_DOCS.md                # Reference manual for installed agent skills
├── README.md                       # Public project overview & quick-start guide
├── SETUP.md                        # Prerequisites and installation instructions
├── SKILL.md                        # Master AI agent operational instruction manual
└── STRUCTURE.md                    # This document
```

---

## 📄 File-by-File Breakdown

### Root CLI & Utilities

#### `faceless.ps1`
- **Role**: Primary PowerShell CLI interface for developers and automation agents.
- **Commands**:
  - `doctor`: Validates Python virtualenv, Node.js, FFmpeg (`h264_nvenc`), and Chrome.
  - `create`: Wraps `scripts/faceless.py` to synthesize narration, align words, and scaffold project folders.
  - `render`: Launches headless Chromium to render the 60fps MP4.
- **Key Flags**: `--topic`, `--script`, `--style`, `--render`, `--speed`, `--voice`.
- **Environment Handling**: Enforces `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` on all subprocess invocations to prevent Windows CP1252 character corruption.

#### `SKILL.md`
- **Role**: Master instruction file for autonomous AI agents (Claude Code, Antigravity, OpenHands).
- **Contents**: Defines design philosophies, audio synchronization standards, scene progression rules, and exact workflow requirements.

---

### Scripts Directory (`scripts/`)

#### `scripts/faceless.py`
- **Role**: Central pipeline engine.
- **Responsibilities**:
  1. **Topic-to-Script Generation**: If `--script` is omitted, probes a local Ollama instance (1.2s timeout) or executes an internal Hook-Fact-Twist-Payoff structured script synthesizer.
  2. **Smart Style Selection (`detect_best_style`)**: Inspects topic keywords and routes to `paper-atlas` (geography/maps), `tall-tale` (bizarre stories/heists), or `stick-story` (science/physics/rules). Strictly excludes 3D styles (`night-file`, `deep-dive`).
  3. **Voice Synthesis Execution**: Spawns `scripts/voice.py` or Edge-TTS to produce `data/narration.wav`.
  4. **Whisper Word Alignment**: Calls `scripts/words.py` to calculate millisecond start/end timestamps for every word into `data/words.json`.
  5. **Procedural SFX & Captions**: Generates `data/cues.json` (audio markers) and `data/captions.srt`.
  6. **Bespoke `src/shots.js` Scaffolding**: Builds the beat-synced shot list with safe word-lookup guards (`safeWd`) that never crash on missing words.

#### `scripts/words.py`
- **Role**: High-precision forced audio alignment.
- **Mechanism**: Loads `faster-whisper` (or standard Whisper `small.en`) to transcribe `narration.wav` and produce JSON word timing intervals (`[{w, line, s, e}]`).
- **Resilience**: Features regex normalization (`norm()`) to guarantee word lookup queries ignore punctuation, capitalization, and hyphen variations.

#### `scripts/voice.py`
- **Role**: Multi-engine TTS voice synthesis adapter.
- **Supported Engines**: Local Kokoro ONNX neural voice, Microsoft Edge-TTS (`en-US-AndrewNeural`, `en-US-ChristopherNeural`), and system SAPI.

#### `scripts/estimate.py`
- **Role**: Zero-dependency fallback timing estimator.
- **Mechanism**: Estimates word durations using syllable counting and character density if Whisper is temporarily unavailable, allowing offline testing without neural models.

---

### Shared Data (`shared/`)

#### `shared/world.geojson`
- **Role**: Vector geographic database (256 KB) containing simplified global coastlines, continents, and national borders.
- **Usage**: When `paper-atlas` or `tall-tale` renders geographic maps, `faceless.py` copies `shared/world.geojson` into `<project>/data/world.geojson`. The HTML5 canvas projects these real coordinates onto the 9:16 frame using equirectangular or Mercator projection, replacing crude hand-drawn polygons with real geography.

---

### Styles Directory (`styles/`)

Each subfolder represents a self-contained visual paradigm containing a `STYLE.md` guide, `style-sheet.png` visual board, and an `example/` reference project:

1. **`styles/paper-atlas/` (Flagship 2D)**:
   - **Aesthetic**: Aged parchment, cut-paper drop shadows, warm sepia, crimson routes.
   - **Key Modules**: `src/core/kit.js` (parchment generator, compass roses, cut paper polygons, ribbons, wax seals).
2. **`styles/tall-tale/` (Flagship 2D)**:
   - **Aesthetic**: Illustrated storybook aesthetic, high-contrast character cut-outs, vibrant earth tones.
   - **Key Modules**: `src/core/toon.js` (character joints, props, vehicles, dynamic arcs).
3. **`styles/stick-story/` (Flagship 2D)**:
   - **Aesthetic**: Clean kinetic line art, blueprint background grids, warning callout cards.
   - **Key Modules**: `src/core/look2d.js` (bold stick figures, countdown slates, hazard banners).
4. **`styles/inside-out/` (2D Anatomy)**:
   - **Aesthetic**: Flat 2D vector cross-sections and human biology.
5. **`styles/deep-dive/` & `styles/night-file/` (Isolated 3D WebGL)**:
   - Experimental Three.js 3D rigs and raymarching shaders. Kept in repository for research; excluded from automated production.

---

### Project Scaffolding Anatomy (`data/YYYY-MM-DD/<slug>/`)

When a Short is created, a dedicated, self-contained project folder is instantiated:

```text
data/YYYY-MM-DD/<slug>/
├── data/
│   ├── captions.srt       # Formatted SubRip subtitles
│   ├── cues.json          # SFX trigger cues (whoosh, pop, tock)
│   ├── lines.json         # Sentence-level timestamps and duration
│   ├── mix.wav            # Multiplexed narration and procedural SFX
│   ├── narration.wav      # Raw voice narration audio
│   ├── script.txt         # Plaintext narration script
│   ├── words.json         # Whisper word-level timing array
│   └── world.geojson      # Local copy of vector coastlines (if map style)
├── fonts/                 # Local font assets (Inter, Caladea)
├── renders/
│   └── out.mp4            # Final 1080×1920 60fps NVENC video
├── src/
│   ├── core/              # Canvas engine, math, and style drawing primitives
│   ├── main.js            # Video playback loop, camera punch/drift, and caption renderer
│   └── shots.js           # The master beat-synced visual animation timeline
├── tools/
│   ├── capture.mjs        # Headless Chromium frame capture & video multiplexer
│   └── mix.py             # Procedural audio synthesis & audio bed mixer
├── index.html             # HTML5 canvas container and preview canvas
└── script.json            # Caption formatting and accent highlight map
```

---

### Agent Skills Directory (`.agents/skills/`)

Modular reference manuals that guide agents and developers during visual authoring:
- **`caption-animation`**: Safe-zone typography (y: 1640), active-word karaoke pop, and line wrap math.
- **`countdown-video`**: Drift-free frame counters, `#3 → #2 → #1` kinetic transitions, and progress bar animation.
- **`javascript-animation`**: Canvas 2D math (`TAU`, `lerp`, `clamp`, `seg`, `eo`, `eio`, `eob`).
- **`lower-thirds`**: Broadcast lower-third banner reveals and branding safe zones.
- **`map-animation`**: Route interpolation, flight path tangents, passport pins, and coordinate projections.
- **`short-form-video`**: Hook structure (0–3s), retention pacing (cuts every 3–5s), and seamless 0.5s loop mechanics.
- **`soundtrack`**: Procedural SFX generation (NumPy sine sweeps, bandpass filters) and cut-on-the-beat synchronization.
