# Faceless Shorts Pipeline Documentation

> Clean, local, $0 AI token automated vertical video creation for Windows (NVIDIA RTX 3050 NVENC, D-drive isolated).

---

## 1. Installed Skills Breakdown (`.agents/skills/`)

The workspace integrates seven specialized video production skills from `.agents/skills/`. Below is a breakdown of their rules, design constraints, and how `scripts/faceless.py` currently interfaces with them.

```
                      .agents/skills/ Capabilities Matrix
 ┌──────────────────────┬────────────────────────┬──────────────────────────────────────────┐
 │ Skill                │ Core Craft & Rules     │ Safe Area & Motion Contract              │
 ├──────────────────────┼────────────────────────┼──────────────────────────────────────────┤
 │ short-form-video     │ Retention contract,    │ Center 900x1400 safe box, top 120px &    │
 │                      │ hooks in first ~1s,    │ bottom 320px clear, right 120px clear.   │
 │                      │ cuts every 2-4s.       │ Frame-driven punch-in zoom (110-112%).   │
 ├──────────────────────┼────────────────────────┼──────────────────────────────────────────┤
 │ caption-animation    │ Syllable word timing,  │ Center band y 1250-1550, 56-80px bold    │
 │                      │ 1-4 word pages, one    │ sans, 2-6px outline, active word in      │
 │                      │ yellow/crimson accent. │ yellow (#FFD43B), spring overshoot pop.  │
 ├──────────────────────┼────────────────────────┼──────────────────────────────────────────┤
 │ javascript-animation │ 100% code animation,   │ Deterministic draw(t), no setInterval,   │
 │                      │ zero external assets,  │ storyboard beat grid, blocking tracks,   │
 │                      │ layout collision checks│ boil on hand lines (seed change @ 7.5Hz).│
 ├──────────────────────┼────────────────────────┼──────────────────────────────────────────┤
 │ soundtrack           │ WebAudio synthesis,    │ Cuts on downbeats, chord change over     │
 │                      │ sync-check verification│ volume jump (+3..+5 dB max, no >+6 dB    │
 │                      │ procedural SFX table.  │ startle), ducking under narration.       │
 ├──────────────────────┼────────────────────────┼──────────────────────────────────────────┤
 │ countdown-video      │ Drift-free timers,     │ Derived from clock (total - frame/fps),  │
 │                      │ tabular-nums, odometer │ tabular-nums font, seamless background   │
 │                      │ reel & flip card motion│ looping period that divides timeline.    │
 ├──────────────────────┼────────────────────────┼──────────────────────────────────────────┤
 │ lower-thirds         │ Two-line hierarchy     │ Left-anchored, lifted above bottom 18%   │
 │                      │ (name >= 1.6x role),   │ UI zone, staggered entrance (bar->name-> │
 │                      │ brand theme locking.   │ role offset 3-6f), hold 3-5s, fast exit. │
 ├──────────────────────┼────────────────────────┼──────────────────────────────────────────┤
 │ map-animation        │ Editorial Vox maps,    │ 12fps graphic stutter over 24fps base,   │
 │                      │ D3/GeoJSON vector paths│ route strokeDashoffset draw-on, spring   │
 │                      │ or Earth Studio AE.    │ pin drops, focus+context region fills.   │
 └──────────────────────┴────────────────────────┴──────────────────────────────────────────┘
```

### Skill-by-Skill Deep Dive

#### 1. `short-form-video`
- **Purpose**: Maximizes audience retention for YouTube Shorts, Instagram Reels, and TikTok.
- **Hook Grammar**: First 0–1s must deliver a curiosity gap or visual mismatch. Supported archetypes:
  - *Open Loop*: "The reason your elevator jump fails..." (payoff delayed).
  - *Direct Promise*: "3 rules to survive an elevator drop..."
  - *Pattern Interrupt*: Instant high-velocity camera whip or visual drop on frame 1.
  - *Negation*: "Stop thinking jumping saves your life..."
- **Pacing**: Visual interrupt or cut every 1.5–3.5s. Metronomic regular cuts cause viewer fatigue; uneven cuts create forward momentum.
- **Punch-In**: Snaps camera zoom to 110–112% on key accents via spring physics (`damping: 12, stiffness: 200`).
- **Loop Seam**: Connects the last 0.5s back to frame 0 (both visual composition matching and sentence loops).

#### 2. `caption-animation`
- **Purpose**: Word-synchronized karaoke captions that maintain readability when muted.
- **Timing**: Derived strictly from Whisper word timestamps (`startMs`, `endMs`) in `data/words.json`. Evenly spaced approximations are prohibited due to drift.
- **Layout & Safe Area**:
  - Center band at `y: 1250-1550` (or `y: 1400` in Inside Out, `y: 1340` in Tall Tale, `y: 1560` in Night File).
  - Keeps bottom 320px completely empty for platform UI (account handles, audio track pills, comment buttons).
  - Keeps top 120px and right 120px clear of critical glyphs.
- **Typography**: 56–80px bold sans (Inter Black / Montserrat), 2–6px ink outline, soft drop shadow, high contrast.
- **Color Accent**: Exactly one highlighted keyword per phrase chunk in yellow (`#FFD43B`) or style-specific accent (crimson in Paper Atlas, red in Night File).

#### 3. `javascript-animation`
- **Purpose**: Deterministic, zero-asset animation executed entirely on an HTML5 2D/WebGL canvas.
- **Purity Contract**: Every visual state is a pure mathematical function of film time `t` or frame `frame` (`draw(lt, d, t)`). No `requestAnimationFrame` state accumulation, no `setInterval`, and no CSS timers.
- **Hand-drawn Boil**: When wobble is used, seeds change at 7.5 Hz (every 4 frames), avoiding high-frequency noise.
- **Camera Staging**: Single continuous coordinate world with cameras pushing, orbiting, or panning (`withCamera` / Three.js perspective camera).

#### 4. `soundtrack`
- **Purpose**: Procedural audio generation, ducked music beds, and synchronized audio-visual cues.
- **Cut-to-Music Harmony**: Transitions align on downbeats; cuts are accentuated by chord progression and harmonic shifts rather than harsh volume spikes (+3 to +5 dB target, preventing >+6 dB startling spikes).
- **Procedural SFX Table**: Soft, rounded sound effects synthesized mathematically via numpy/scipy:
  - `whoosh`: Soft noise bandpass sweep (cuts & transitions).
  - `pop`: Fast exponential sine sweep (graphics/pills popping in).
  - `plop`: Liquid entry drop.
  - `gulp`: Dual-stage swallowing sweep.
  - `boing`: Frequency-modulated bounce.
  - `sizzle`: Filtered crackle for acids/reactions.
  - `sparkle`: Multi-tone arpeggio for dissolving/sparkles.
  - `thud`: Low sub-bass decay for heavy impacts.
  - `slam`: Hard-clipped distorted impact for myth busts/red X reveals.
  - `alarm`: Low-pulse warning drone.
  - `tock`: Muted click for clocks and stopwatch tickers.
  - `zip`: High-speed exit whoosh.

#### 5. `countdown-video`
- **Purpose**: Deterministic, drift-free countdown timers for launch events, stream starting cards, and urgency explainers.
- **Clock Authority**: Computed as `Math.max(0, Math.ceil(durationInSeconds - frame / fps))` — never decremented inside a tick callback.
- **Typography & Motion**: `tabular-nums` formatting prevents width jitter; odometer reels translate vertically stacked 0–9 strips; flip-card animations fold along the horizontal axis.

#### 6. `lower-thirds`
- **Purpose**: Broadcast-grade speaker titles, interview tags, and credentials.
- **Visual Hierarchy**: Primary name is dominant (≥1.6× role font size, heavier weight, near-white); secondary title/role is lighter with a brand accent color.
- **Motion Timing**: Asymmetric easing — snappy enter (12–18 frames, ease-out), readable hold (90–150 frames / 3–5s), rapid exit (8–12 frames, ease-in). Staggered reveal: Bar → Name → Role.
- **Placement**: Lifted above the bottom 18% UI zone for vertical 9:16 video.

#### 7. `map-animation`
- **Purpose**: Vox-style documentary cartography and travel routes.
- **12fps Graphic Stutter**: Base camera move runs at a smooth 24/30fps while map overlays (pins, routes, labels) snap to 12fps (`Math.floor(frame / STEP) * STEP`), providing an infographic cadence.
- **Vector Projection**: Mercator projection of GeoJSON paths to canvas SVG, route draw-on with normalized `stroke-dashoffset`, and spring overshoot pin drops.

---

## 2. Current Implementation vs. Skill Capabilities (Gap Analysis)

### What `scripts/faceless.py` Currently Automates
- [x] Clones any chosen style from `styles/` without touching template originals.
- [x] Generates natural-sentence TTS narration using local Kokoro-82M or fallback Microsoft Edge Neural voice.
- [x] Transcribes speech with local Faster-Whisper to extract word-level timestamps (`data/words.json`).
- [x] Analyzes text to automatically chunk captions into 1–3 words with smart `*KEYWORD` highlights.
- [x] Generates bespoke beat-synced `src/shots.js` tailored to the script's clause cuts (`cut(i)`), syncing key moments with exact word timings (`Wd(keyword, i)`).
- [x] Automates camera punch-ins, drift zooms, actor poses, and procedural sound cue triggers (`whoosh`, `pop`, `thud`, `slam`, `alarm`).
- [x] Synthesizes clean ducked soundtracks and SFX locally via `tools/mix.py` (0 external credits or API keys).
- [x] Captures frames via headless Chromium into NVIDIA RTX 3050 NVENC (`h264_nvenc`) with full D-drive temporary file isolation.

### Features in `.agents/skills/` Available for Manual or Future Automation
1. **Odometer & Countdown Components (`countdown-video`)**: The math and CSS odometer strips exist in the skills library; `faceless.py` generates basic timers, but dynamic digit rolls/flips can be added to custom `src/shots.js`.
2. **Staggered Lower-Third Straps (`lower-thirds`)**: Currently names/roles appear as pill tags; the formal staggered 3-phase bar/name/role component can be embedded into documentary topics.
3. **GeoJSON Route Draw-on (`map-animation`)**: `paper-atlas` renders canvas-based maps; integrating dynamic D3 GeoJSON projections and 12fps graphic stutter quantizing allows real-world flight paths and borders.
4. **Browser OfflineAudioContext Synthesis (`soundtrack`)**: The WebAudio groove engine (`groove.js`) can synthesize multi-layer drum and chord tracks inside the browser alongside `tools/mix.py`.
5. **Sidecar SRT/VTT Generation (`caption-animation`)**: While captions are burned into the MP4 pixels, generating `.srt`/`.vtt` sidecars from `data/words.json` provides accessibility and SEO uploads.

---

## 3. Available Base Styles (`styles/`)

Every project copies one of these 6 production-ready styles into `data/YYYY-MM-DD/<slug>/`:

| Style Directory | Aesthetic & Visual Mode | Best Topics | Sound Profile |
|---|---|---|---|
| **`deep-dive`** | **3D Zack D. Films Style**: Three.js sculpted humans, sunlit realistic sets, shallow depth of field, glowing cyan x-ray glass bodies, macro red blood vessel tunnels. | Biology, human anatomy, medical what-ifs, physics experiments, organ functions. | `tension` low drone + pulse, soft heartbeat, inhale, plop, whoosh. |
| **`inside-out`** | **Flat 2D Vector Explainer**: Minimalist hero, cyan cutaway x-ray skeletons, pink internal organs, red danger markers, yellow keywords, punch-in cuts every 1.5–3s. | Body science, everyday what-ifs, digestion, quick physics, health myths. | `bed` 100 BPM arpeggio, soft pops, sizzle, whoosh, slam. |
| **`night-file`** | **3D Mystery & True Crime**: High-contrast single-light 3D rooms, faceless witness silhouettes with red rim lighting, glowing solid red subject, typewriter text, evidence inserts (case files, polaroids, red string). | Unsolved mysteries, FBI case files, historical heists, strange phenomena, creepy stories. | `tension` drone, typewriter tocks, low hum, sudden impact hits. |
| **`paper-atlas`** | **Cut-Paper Historical Maps**: Aged parchment backgrounds, drop-shadow cut paper layers, crimson travel routes, gold date ribbons, wax seals, period figures. | Historical events, ancient battles, city fires, explorations, geopolitical history. | `tension` or `bed`, paper rustle, soft whoosh, quill/stamp hits. |
| **`stick-story`** | **Survival Stick Figure**: Ink-black stick people with highly expressive acting eyes, flat vector living rooms and kitchens with day/night lighting shifts, gold numbered step cards. | Survival guides, emergency procedures ("what to do if..."), life hacks, safety steps. | `bed` playful/tense, step-card pops, boings, electric ticks, whooshes. |
| **`tall-tale`** | **2D-in-3D Animated Comedy**: 2D ink-outlined cartoon characters (round heads, bean bodies) walking and emoting inside a sunny, fully 3D stylized town with real shadows. | Funny true stories, bizarre historical events, clever con artists, unusual loopholes. | `bounce` upbeat acoustic/piano, cartoon pops, dings, stamps, chugs. |

---

## 4. End-to-End Pipeline Architecture

```
                               Data Flow Pipeline
                               
 [ my_script.txt ] (Raw plain text / script lines)
        │
        ▼
 [ faceless.ps1 create ]
        │
        ├── 1. Clone Style: styles/<style>/example -> data/YYYY-MM-DD/<slug>/
        ├── 2. Patch Tools: Update capture.mjs for D:\...\.tmp and h264_nvenc
        ├── 3. Parse Script: Build script.json with 1-3 word *KEYWORD chunks
        ├── 4. Generate TTS:
        │      ├── Kokoro-82M (if installed) -> data/narration.wav (24kHz)
        │      └── Fallback: Microsoft Edge Neural TTS -> data/narration.wav
        │      └── Computes exact line boundaries -> data/lines.json
        ├── 5. Whisper Alignment:
        │      └── Faster-Whisper (small.en) word timing -> data/words.json
        ├── 6. Bespoke Scene Construction:
        │      └── Generates customized beat-synced src/shots.js
        └── 7. Automated QA:
               └── node tools/capture.mjs check (Verifies duration & bounds)
        │
        ▼
 [ faceless.ps1 render ]
        │
        ├── 1. Extract Cues: node tools/capture.mjs cues -> data/cues.json
        ├── 2. Mix Audio: python tools/mix.py (Voice + Music + SFX) -> data/mix.wav
        └── 3. Capture & Encode:
               ├── Headless Chromium captures frame-exact canvas images
               └── FFmpeg streams frames into RTX 3050 h264_nvenc -> renders/out.mp4
```

### File Hierarchy Inside a Project (`data/YYYY-MM-DD/<slug>/`)
- `script.json`: Video metadata, narration voice, speed, music mode, and line chunks.
- `src/shots.js`: **The per-video animation controller**. Contains shot timings (`cut(i)`), camera motions, actor states, overlays, and sound cues.
- `src/main.js`: Boots fonts, timing, caption rendering, and exposes `window.OP` for Chromium.
- `src/core/`: Style engine components (`kit.js`, `lib.js`, `timing.js`, `captions.js`).
- `data/narration.wav`: Clean 24 kHz mono spoken voice track.
- `data/lines.json`: Timing start/end markers for every script line.
- `data/words.json`: Syllable-level timestamps for every spoken word.
- `data/cues.json`: Scheduled procedural SFX triggers extracted from `shots.js`.
- `data/mix.wav`: Mastered 48 kHz stereo audio track (voice + ducked music + SFX).
- `renders/out.mp4`: Final 1080×1920 9:16 vertical short.
- `review/all.jpg`: Contact sheet with time-stamped visual QA frames.

---

## 5. CLI Command & Flag Reference

### Environment Diagnostic: `doctor`
Verifies all prerequisites without writing project files.

```powershell
.\faceless.ps1 doctor
```
Checks performed:
- **Node.js**: v18+ required (verifies v22+ is present).
- **Chrome**: Validates Google Chrome binary.
- **FFmpeg / FFprobe**: Checks custom D-drive installation path.
- **NVIDIA NVENC**: Validates GPU hardware encoder `h264_nvenc` (RTX 3050).
- **Python venv**: Validates `faster_whisper`, `numpy`, `scipy`, and TTS engines (`kokoro_onnx` or `edge_tts`).
- **Shared SFX**: Validates audio assets inside `D:\AI-Projects\stream-clips\assets\sfx`.
- **D: .tmp Isolation**: Asserts `TEMP`, `TMP`, and Chrome user data are redirected to `faceless-shorts\.tmp`.

---

### Project Creation: `create`
Scaffolds a project, creates audio, computes Whisper timestamps, and writes bespoke scenes.

```powershell
# Create project (ready for review/customization before rendering)
.\faceless.ps1 create --topic "Elevator Physics" --script "my_script.txt" --style inside-out

# Create and immediately render to MP4 using NVENC
.\faceless.ps1 create --topic "Elevator Physics" --script "my_script.txt" --style inside-out --render

# Fast draft render with lower quality for rapid review
.\faceless.ps1 create --topic "Elevator Physics" --script "my_script.txt" --style inside-out --render --draft

# Create, render MP4, and generate contact sheet
.\faceless.ps1 create --topic "Elevator Physics" --script "my_script.txt" --style inside-out --render --sheet
```

#### Available Flags for `create`
- `--topic "<title>"` (*Required*): Short title. Used to derive directory slug and header metadata.
- `--script "<path>"` (*Required*): Path to `.txt` (one sentence per line) or structured `.json` script.
- `--style <name>` (*Optional, default: `inside-out`*): `deep-dive` | `inside-out` | `night-file` | `paper-atlas` | `stick-story` | `tall-tale`.
- `--voice <name>` (*Optional*): TTS voice override (e.g., `am_michael`, `af_heart`, or `en-US-AndrewNeural`).
- `--speed <float>` (*Optional, default: `1.0`*): Speech rate multiplier (e.g., `1.05`).
- `--music <mode>` (*Optional*): `bed` | `tension` | `none` | `audio/track.mp3`.
- `--render`: Triggers local capture and FFmpeg encode immediately after creation.
- `--draft`: Uses ultrafast draft encoding profile (`-preset p1 -cq 28`).
- `--sheet`: Produces visual contact sheet at `review/all.jpg`.

---

### Local Rendering: `render`
Renders an existing project folder locally with zero AI tokens.

```powershell
# Standard high quality render
.\faceless.ps1 render "data\2026-11-25\elevator-physics"

# Fast preview draft
.\faceless.ps1 render "data\2026-11-25\elevator-physics" --draft

# Render MP4 and produce contact sheet for visual QA
.\faceless.ps1 render "data\2026-11-25\elevator-physics" --sheet
```

---

## 6. Customization & Troubleshooting Guide

### How to Customize Scenes in `src/shots.js`
Every project directory contains its own `src/shots.js`. You can modify drawing logic, adjust camera positions, or trigger sound cues without spending AI tokens:

```javascript
// Example snippet inside data/YYYY-MM-DD/<slug>/src/shots.js
const st = cut(2); // cut on line 2 pause
const hitWord = Wd('impact', 2); // triggers when "impact" is spoken

add({
  id: 'S03',
  at: st,
  cam: [540, 850], // camera center
  zoom: 0.12,      // push-in zoom intensity
  note: 'Hero prepares for floor impact',
  draw(lt, d, t) {
    K.room();
    // Use kit helpers to pose characters
    K.man({
      x: 540,
      y: 1180,
      s: 1.6,
      mouth: lt > (hitWord - st) ? 'o' : 'flat',
      eyes: lt > (hitWord - st) ? 'wide' : 'n',
    });
    // Add visual cards within 900x1400 safe area
    K.pill('IMPACT: 52 MPH', 540, 360, 56, C.red, C.white, eob(seg(lt, 0.1, 0.4)));
  }
});

// Add procedural audio cues
cue(st, 'whoosh');
cue(hitWord, 'slam', { gain: 0.8 });
```

After modifying `src/shots.js`:
```powershell
# 1. Test in browser preview mode (interactive timeline)
node tools/capture.mjs preview

# 2. Re-render final MP4
.\faceless.ps1 render "data\YYYY-MM-DD\<slug>"
```

---

### Modifying Narration or Timing in `script.json`
If you edit script lines in `script.json`:
1. Re-run voice and alignment:
   ```powershell
   & "D:\AI-Projects\stream-clips\.streamclips\venv\Scripts\python.exe" scripts/voice.py "data\YYYY-MM-DD\<slug>"
   & "D:\AI-Projects\stream-clips\.streamclips\venv\Scripts\python.exe" scripts/words.py "data\YYYY-MM-DD\<slug>"
   ```
2. Re-render the short:
   ```powershell
   .\faceless.ps1 render "data\YYYY-MM-DD\<slug>"
   ```

---

### D-Drive Isolation & Troubleshooting

#### Issue: `PermissionError` or Sandbox Lock on `.tmp`
- **Root Cause**: Windows sandbox security occasionally restricts subfolder creation within `.tmp`.
- **Mitigation**: `scripts/faceless.py` wraps subfolder setup in exception handlers and passes environment variables dynamically to subprocesses.
- **Manual Verification**: Run PowerShell with standard user permissions in `D:\AI-Projects\faceless-shorts-skill\faceless-shorts`. Ensure `TEMP` points to `.tmp`:
  ```powershell
  $env:TEMP = "$PWD\.tmp"
  $env:TMP = "$PWD\.tmp"
  ```

#### Issue: Chromium Fails to Launch in Capture
- **Check**: Ensure no orphaned Chrome background tasks are holding port or user-data locks:
  ```powershell
  Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
  ```

#### Issue: NVENC Initialization Error
- **Check**: Ensure NVIDIA display drivers support CUDA/NVENC. Run `.\faceless.ps1 doctor` to verify `h264_nvenc` availability. If running on a system without an NVIDIA GPU, fallback to CPU encoding by specifying `-c:v libx264` inside the project's `tools/capture.mjs`.
