"""Clean Windows CLI runner for faceless-shorts.

Commands:
  doctor
  create --topic "<title>" --script "<path>" [--style auto|<name>] [--render]
  render "<project_dir>" [--draft] [--sheet]
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLES_DIR = ROOT / "styles"
DATA_DIR = ROOT / "data"
TMP_DIR = ROOT / ".tmp"

VENV_PY = Path(r"D:\AI-Projects\stream-clips\.streamclips\venv\Scripts\python.exe")
FFMPEG_BIN = Path(r"D:\gem\ffmpeg-2026-11-19-git-01ca75d350-full_build\ffmpeg\bin")
FFMPEG_EXE = FFMPEG_BIN / "ffmpeg.exe"
FFPROBE_EXE = FFMPEG_BIN / "ffprobe.exe"
SHARED_SFX_DIR = Path(r"D:\AI-Projects\stream-clips\assets\sfx")

CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def enforce_d_drive_env() -> dict[str, str]:
    """Ensure all temp/cache directories stay inside D:\\...\\.tmp."""
    try:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        for sub in ("faceless-home", "hf-cache", "torch-cache", "cache"):
            (TMP_DIR / sub).mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass

    env = os.environ.copy()
    env["TEMP"] = str(TMP_DIR)
    env["TMP"] = str(TMP_DIR)
    env["TMPDIR"] = str(TMP_DIR)
    env["FACELESS_HOME"] = str(TMP_DIR / "faceless-home")
    env["HF_HOME"] = str(TMP_DIR / "hf-cache")
    env["TORCH_HOME"] = str(TMP_DIR / "torch-cache")
    env["XDG_CACHE_HOME"] = str(TMP_DIR / "cache")
    env["PATH"] = f"{FFMPEG_BIN};{env.get('PATH', '')}"

    os.environ.update({
        "TEMP": env["TEMP"],
        "TMP": env["TMP"],
        "TMPDIR": env["TMPDIR"],
        "FACELESS_HOME": env["FACELESS_HOME"],
        "HF_HOME": env["HF_HOME"],
        "TORCH_HOME": env["TORCH_HOME"],
        "XDG_CACHE_HOME": env["XDG_CACHE_HOME"],
        "PATH": env["PATH"],
    })
    return env


def find_chrome() -> Path | None:
    for c in CHROME_CANDIDATES:
        if c and Path(c).is_file():
            return Path(c)
    return None


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "short"


def run_cmd(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=check)


# ---------------------------------------------------------------------------
# Smart Style Detection
# ---------------------------------------------------------------------------
def detect_best_style(topic: str, script_text: str = "") -> str:
    """Intelligently inspect topic and script lines to select the optimal base style.

    Allowed auto-selection targets (ONLY the reliable, high-contrast 2D canvas styles):
    - paper-atlas: geography, countries, history, wars, borders, travel, economics, trade routes.
    - tall-tale: bizarre true stories, heists, mysteries, scams, weird history, pop culture.
    - stick-story: default for everything else (science, physics, psychology, survival, how-to, tech).

    NOTE: 'night-file' and 'deep-dive' are strictly banned from auto-selection.
    """
    text = f"{topic} {script_text}".lower()

    paper_atlas_kw = [
        "geography", "map", "maps", "country", "countries", "border", "borders", "territory",
        "empire", "emperor", "dynasty", "war", "battle", "kingdom", "continent", "ocean", "sea",
        "thames", "trade route", "silk road", "london", "europe", "asia", "america", "africa",
        "colony", "treaty", "century", "ancient", "1600", "1700", "1800", "1900", "king", "queen",
        "parchment", "fleet", "naval", "invasion", "travel", "economics", "gdp", "gold", "silver",
        "panama canal", "roman", "rome", "egypt", "viking", "persian", "greek", "conquest"
    ]

    tall_tale_kw = [
        "bizarre", "crazy", "weird", "scam", "loophole", "heist", "stole", "robbed", "fake", "hoax",
        "con artist", "prank", "cheated", "lawsuit", "sued", "true story", "unbelievable", "mystery",
        "disappeared", "vanished", "cooper", "balloon boy", "mailed", "airline", "lottery",
        "millionaire", "casino", "impostor", "pop culture", "ridiculous", "absurd", "crime", "robbery"
    ]

    score_atlas = sum(text.count(k) for k in paper_atlas_kw)
    score_tall = sum(text.count(k) for k in tall_tale_kw)

    if score_atlas > 0 and score_atlas >= score_tall:
        return "paper-atlas"
    if score_tall > 0 and score_tall > score_atlas:
        return "tall-tale"

    return "stick-story"  # Default for all science, physics, psychology, survival, tech


# ---------------------------------------------------------------------------
# One-Line Topic-to-Script High-Retention Synthesizer
# ---------------------------------------------------------------------------
def generate_script_from_topic(topic: str) -> list[str]:
    """Generate a punchy 7-9 sentence (35-45s) narration script with strong hook and payoff."""
    # 1. Attempt local LLM (Ollama or local OpenAI-compatible endpoint) with fast timeout
    try:
        import urllib.request
        prompt = (
            f"Write a punchy 7 to 8 sentence narration script for a 40-second YouTube Short about: '{topic}'.\n"
            "Rules:\n"
            "1. First sentence MUST be a provocative hook under 3 seconds.\n"
            "2. Include concrete numbers, years, percentages, or speeds.\n"
            "3. Include a counter-intuitive twist or comparison (Myth vs Reality).\n"
            "4. End with a decisive golden rule payoff that loops back to the beginning.\n"
            "Output only the sentences, one per line, with no labels, numbers, or bullet points."
        )
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps({"model": "llama3", "prompt": prompt, "stream": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            data = json.loads(resp.read().decode())
            raw_text = data.get("response", "").strip()
            lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            if len(lines) >= 6:
                return lines[:9]
    except Exception:
        pass

    # 2. Rich Domain-Aware High-Retention Script Synthesizer
    t = topic.lower()
    clean_topic = re.sub(
        r"^(why\s+did\s+the|why\s+do|why\s+are|why\s+|how\s+to|how\s+|what\s+happens\s+if\s+you|what\s+if\s+you|can\s+you\s+survive|can\s+you|the\s+secret\s+of\s+the|the\s+bizarre\s+true\s+story\s+of\s+the|the\s+bizarre\s+true\s+story\s+of|the\s+true\s+story\s+of|the)\s+",
        "",
        topic,
        flags=re.I,
    ).strip("? .!")
    clean_title = clean_topic.title()

    # Category A: History, Empires, Wars, Maps, Trade Routes (paper-atlas archetype)
    if any(k in t for k in ["rome", "roman", "empire", "london fire", "fire of london", "silk road", "panama canal", "war", "history", "geography", "border", "territory", "trade", "napoleon", "egypt", "viking"]):
        if "roman" in t or "rome" in t:
            return [
                "Most people think the Roman Empire collapsed overnight from barbarian invasions.",
                "In reality, the collapse took over two hundred years of internal economic rot.",
                "By the year 400, Roman currency had lost more than ninety-eight percent of its silver value.",
                "To pay for sprawling borders, emperors simply debased the coins and raised taxes.",
                "The hyperinflation got so severe that Roman citizens actually welcomed the invading tribes.",
                "Instead of a single catastrophic battle, Rome withered from within until the final emperor fell in 476.",
                "Borders cannot save an empire if the internal currency is completely worthless.",
                "History always repeats itself: sound money and strong trade routes remain the true foundation of every superpower.",
            ]
        elif "fire" in t and "london" in t:
            return [
                "In 1666, a tiny spark in a London bakery ignited one of the greatest disasters in human history.",
                "For four straight days, violent eastern winds drove an unstoppable wall of fire across the city.",
                "Over thirteen thousand homes and eighty-seven parish churches were reduced to glowing ash.",
                "Yet despite seventy thousand people being left completely homeless, only six verified deaths were ever recorded.",
                "The catastrophic inferno consumed four-fifths of London and destroyed the bubonic plague outbreak in one stroke.",
                "The city banned wooden architecture forever, rebuilding London entirely in fireproof stone and brick.",
                "From the ashes of 1666 emerged the modern urban grid and the world first property insurance industry.",
                "Sometimes the most destructive catastrophes end up reshaping human civilization forever.",
            ]
        elif "canal" in t or "panama" in t:
            return [
                "In 1914, engineers completed the Panama Canal, cutting eight thousand miles off ocean voyages.",
                "Building this fifty-mile shortcut cost over twenty-five thousand lives and four hundred million dollars.",
                "Instead of digging at sea level, engineers lifted massive ships eighty-five feet above the mountains.",
                "Gravity-fed water locks lift each vessel using fifty-two million gallons of fresh lake water.",
                "Today, over fourteen thousand cargo ships cross the continental divide every single year.",
                "A single passage through the canal saves shipping companies hundreds of thousands of dollars in fuel.",
                "This engineering marvel fundamentally transformed global trade and reshaped modern geopolitics.",
                "Mastering the narrowest waterways on the map remains the ultimate key to global commerce.",
            ]
        else:
            return [
                f"Have you ever wondered what really determined the fate of {clean_title}?",
                f"Across centuries of conflict, historians traced how {clean_title} completely altered world trade routes.",
                "Controlling these vital corridors moved over sixty percent of global wealth between continents.",
                "When rival powers clashed, trade collapsed by more than seventy-five percent in a single year.",
                "Navies and armies scrambled across thousands of miles to redraw every border on the map.",
                "The struggle transformed regional economies and permanently shifted the global balance of power.",
                f"Even today, the lasting legacy of {clean_title} defines modern borders and international law.",
                "Mastering the map has always been the ultimate secret to mastering the world.",
            ]

    # Category B: Bizarre true stories, scams, heists, hoaxes, loopholes (tall-tale archetype)
    elif any(k in t for k in ["balloon boy", "cooper", "scam", "loophole", "heist", "hoax", "stole", "robbed", "fake", "con artist", "lottery", "bizarre", "crazy", "weird", "unbelievable"]):
        if "balloon" in t:
            return [
                "In 2009, millions of viewers watched in horror as a homemade silver flying saucer soared into the Colorado sky.",
                "The parents claimed their six-year-old son Falcon was trapped inside the runaway aircraft.",
                "The military scrambled National Guard helicopters and Denver International Airport halted flights for over an hour.",
                "When the balloon finally touched down fifty miles away, the craft was completely empty.",
                "Hours later, the boy emerged from his home attic, revealing his parents told him to hide.",
                "During a live television interview, the boy accidentally confessed they did it all for a reality show.",
                "The grand media spectacle ended with felony convictions and thirty-six thousand dollars in restitution.",
                "The bizarre Balloon Boy incident remains the most infamous live television hoax in American history.",
            ]
        elif "cooper" in t:
            return [
                "In 1971, a quiet man in a dark suit hijacked a Boeing 727 over the Pacific Northwest.",
                "He demanded two hundred thousand dollars in cash and four parachutes before releasing the passengers.",
                "Flying at ten thousand feet into freezing rain, he lowered the rear airstair and vanished into the void.",
                "Despite a massive FBI manhunt across Washington forests, not a single trace was found.",
                "Nine years later, rotting bundles of his twenties were uncovered along the Columbia River.",
                "To this day, D.B. Cooper remains the only unsolved air piracy case in American aviation history.",
                "A single calculated leap created an enduring legend that continues to baffle investigators today.",
            ]
        else:
            return [
                f"This might be the most bizarre true story you will ever hear about {clean_title}.",
                f"It all started when an audacious scheme exploited a massive legal loophole in the system.",
                "The mastermind managed to walk away with over two hundred thousand dollars before anyone noticed.",
                "Investigators realized the entire operation took less than forty-eight hours to execute.",
                "When authorities finally intervened, the truth proved even stranger than the original crime.",
                "The unbelievable trick exposed a gaping flaw that forced regulators to rewrite the rules forever.",
                f"Decades later, the crazy true story of {clean_title} remains an unforgettable legend.",
                "Never underestimate how far someone will go when they find a loophole in plain sight.",
            ]

    # Category C: Physics, Survival, How-To, Everyday Science (stick-story archetype)
    else:
        if "elevator" in t:
            return [
                "Imagine falling inside a pitch-black elevator shaft from the fiftieth floor.",
                "Most people believe jumping right before impact will save their life.",
                "Let us do the actual physics on why that idea fails completely.",
                "At floor fifty, the falling cab is dropping downward at over sixty miles per hour.",
                "Even an Olympic athlete can only jump upward at about eight miles per hour.",
                "Subtracting eight from sixty still leaves you slamming into the floor at fifty-two miles per hour.",
                "Even worse, inside a closed blind box, jumping a split second too early slams your head into the ceiling first.",
                "Your real best move is lying flat on your back to spread the impact force across your entire body.",
                "Physics always wins, so save your legs and hit the floor flat.",
            ]
        elif "space" in t or "gun" in t:
            return [
                "What actually happens if you pull the trigger of a handgun in deep space?",
                "First, modern ammunition contains its own internal oxidizer, so the bullet fires normally in a vacuum.",
                "Because there is zero atmospheric friction, the bullet travels forever at over two thousand miles per hour.",
                "According to Newton third law of motion, the recoil pushes your body backward at about four inches per second.",
                "If you fire a gun while orbiting a planet, your bullet can actually orbit all the way around.",
                "That means without changing trajectory, you could theoretically shoot yourself in the back.",
                "In deep space, every action produces an eternal reaction with zero air resistance to slow it down.",
                "Physics in a vacuum never forgives, so keep your finger off the trigger in orbit.",
            ]
        else:
            return [
                f"Here is the counter-intuitive science behind {clean_title} that almost nobody understands.",
                f"At first glance, {clean_title} seems straightforward, but the underlying physics tell a very different story.",
                "Most people assume the outcome is driven by a single obvious factor.",
                "In reality, the physical forces at play multiply by over sixty percent under high-stress conditions.",
                "When you compare the common intuition against actual laboratory testing, the math fails completely.",
                "A split second difference in timing can turn a routine situation into a catastrophic failure.",
                "The true secret comes down to how forces distribute across the entire system.",
                f"Remember this golden rule: understand the hidden physics of {clean_title}, and you will always stay ahead.",
            ]


# ---------------------------------------------------------------------------
# Topic-Aware Visual Analysis for Dynamic 2D Scenes
# ---------------------------------------------------------------------------
def analyze_line_visuals(text: str, line_idx: int, total_lines: int, prev_mod: str = "") -> dict:
    """Analyze a script line to determine the most dynamic 2D canvas visual module."""
    t = text.lower()

    # 1. Concrete numbers, percentages, speed, currency, years
    m_speed = re.search(r"(\b\d+\s*(?:mph|km/h|miles\s*per\s*hour|feet\s*per\s*second)\b)", text, re.I)
    m_money = re.search(r"(\$[\d,]+|\b\d+\s*(?:million|thousand|billion|hundred)\s*dollars?|\b\d+\s*dollars?)", text, re.I)
    m_pct = re.search(r"(\b\d+%\b|\b\d+\s*percent\b|\b(?:ninety|eighty|seventy|sixty|fifty|forty|thirty|twenty)\s*percent\b)", text, re.I)
    m_year = re.search(r"\b(?:in\s+)?(1[4-9]\d\d|20\d\d)\b", text, re.I) or re.search(r"\byear\s+(\d{3,4})\b", text, re.I)
    m_num = re.search(r"\b(\d{1,3}(?:,\d{3})+|\d+)\b", text)

    # 2. Comparisons / Contrast
    is_vs = any(w in t for w in [" vs ", " versus ", "instead of", "compared to", "rather than", "fails completely", "difference", "contrary", "myth vs", "opposite"])

    # 3. Motion: Falling vs Jumping/Upward
    is_falling = any(w in t for w in ["fall from", "falling", "drop from", "dropping", "drops", "downward", "plummet", "floor flat", "ground", "shaft"])
    is_jumping = any(w in t for w in ["jump", "jumps", "jumping", "leap", "upward", "ceiling", "soared", "aircraft", "flying"])

    # 4. Location / Map
    is_location = any(w in t for w in ["country", "countries", "border", "borders", "territory", "map", "ocean", "river", "sea", "london", "washington", "seattle", "pacific", "atlantic", "colorado", "denver", "rome", "roman", "america", "europe", "asia", "route", "trade", "canal", "panama", "harbor"])

    # 5. Rule / Warning / Failure
    is_rule = line_idx >= total_lines - 2 or any(w in t for w in ["always", "never", "best move", "rule", "remember", "lesson", "superpower"])
    is_fail = any(w in t for w in ["slam", "crash", "smash", "bonk", "fail", "fails", "danger", "hazard", "conviction", "empty", "rot", "worthless"])

    if m_speed:
        return {"mod": "counter", "val": m_speed.group(0).upper(), "labelA": "", "labelB": ""}
    if m_money:
        return {"mod": "counter", "val": m_money.group(0).upper(), "labelA": "", "labelB": ""}
    if m_pct:
        return {"mod": "counter", "val": m_pct.group(0).upper(), "labelA": "", "labelB": ""}
    if m_year:
        val = m_year.group(1) if m_year.groups() else m_year.group(0)
        return {"mod": "year", "val": val, "labelA": "", "labelB": ""}
    if is_vs:
        return {"mod": "comparison", "val": "VS", "labelA": "MYTH", "labelB": "REALITY"}
    if is_falling and prev_mod != "falling":
        return {"mod": "falling", "val": "60 MPH", "labelA": "DROP", "labelB": "DOWN"}
    if is_jumping and prev_mod != "jumping":
        return {"mod": "jumping", "val": "8 MPH", "labelA": "JUMP", "labelB": "UP"}
    if m_num and int(m_num.group(1).replace(",", "")) > 20:
        return {"mod": "counter", "val": m_num.group(1), "labelA": "", "labelB": ""}
    if is_location and prev_mod != "map":
        return {"mod": "map", "val": "SECTOR 1", "labelA": "", "labelB": ""}
    if is_rule:
        return {"mod": "rule", "val": "GOLDEN RULE", "labelA": "", "labelB": ""}
    if is_fail:
        return {"mod": "warning", "val": "WARNING", "labelA": "", "labelB": ""}

    return {"mod": "action", "val": "", "labelA": "", "labelB": ""}


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------
def cmd_doctor(_args: argparse.Namespace) -> int:
    env = enforce_d_drive_env()
    failures = 0

    def report(ok: bool, name: str, detail: str, warn_only: bool = False) -> None:
        nonlocal failures
        tag = "[OK]  " if ok else ("[WARN]" if warn_only else "[FAIL]")
        print(f"{tag} {name:<16} {detail}")
        if not ok and not warn_only:
            failures += 1

    # 1. Node.js
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True, env=env)
        ver = r.stdout.strip()
        major = int(ver.lstrip("v").split(".")[0])
        report(major >= 18, "Node.js", f"{ver} (need >= v18)")
    except Exception as exc:
        report(False, "Node.js", f"missing or failed: {exc}")

    # 2. Chrome
    chrome = find_chrome()
    report(chrome is not None, "Chrome", str(chrome) if chrome else "Google Chrome not found")

    # 3. FFmpeg / FFprobe
    ff_ok = FFMPEG_EXE.is_file() and FFPROBE_EXE.is_file()
    ff_detail = str(FFMPEG_BIN)
    if ff_ok:
        try:
            r = subprocess.run([str(FFMPEG_EXE), "-version"], capture_output=True, text=True, check=True, env=env)
            first_line = r.stdout.splitlines()[0] if r.stdout else "ok"
            ff_detail = f"{first_line} ({FFMPEG_BIN})"
        except Exception as exc:
            ff_ok = False
            ff_detail = f"failed: {exc}"
    report(ff_ok, "FFmpeg/FFprobe", ff_detail)

    # 4. h264_nvenc
    nvenc_ok = False
    nvenc_detail = "h264_nvenc not listed"
    if FFMPEG_EXE.is_file():
        r = subprocess.run([str(FFMPEG_EXE), "-hide_banner", "-encoders"], capture_output=True, text=True, env=env)
        if "h264_nvenc" in r.stdout:
            nvenc_ok = True
            nvenc_detail = "h264_nvenc available (RTX 3050)"
    report(nvenc_ok, "NVENC", nvenc_detail)

    # 5. Python venv + packages
    py_ok = VENV_PY.is_file()
    py_detail = str(VENV_PY)
    if py_ok:
        probe = (
            "import importlib.util, sys; "
            "req=['faster_whisper','numpy','scipy']; "
            "opt=['kokoro_onnx','edge_tts']; "
            "miss=[m for m in req if not importlib.util.find_spec(m)]; "
            "tts=[m for m in opt if importlib.util.find_spec(m)]; "
            "print(f'{sys.version.split()[0]}|miss={miss}|tts={tts}')"
        )
        r = subprocess.run([str(VENV_PY), "-c", probe], capture_output=True, text=True, env=env)
        if r.returncode == 0 and "miss=[]" in r.stdout:
            py_detail = f"Python {r.stdout.strip()} ({VENV_PY})"
        else:
            py_ok = False
            py_detail = f"venv check failed: {r.stdout.strip()} {r.stderr.strip()}"
    report(py_ok, "Python venv", py_detail)

    # 6. Shared SFX
    sfx_ok = SHARED_SFX_DIR.is_dir()
    if sfx_ok:
        items = [p.name for p in SHARED_SFX_DIR.iterdir()]
        sfx_detail = f"{SHARED_SFX_DIR} ({len(items)} entries)"
    else:
        sfx_detail = f"missing: {SHARED_SFX_DIR}"
    report(sfx_ok, "Shared SFX", sfx_detail)

    # 7. D-drive .tmp isolation
    tmp_ok = TMP_DIR.is_dir() and Path(env["TEMP"]).resolve() == TMP_DIR.resolve()
    report(tmp_ok, "D: .tmp", f"TEMP/TMP/Chrome -> {TMP_DIR}")

    print("-" * 60)
    if failures == 0:
        print("DOCTOR OK: all checks passed.")
        return 0
    print(f"DOCTOR FAILED: {failures} check(s) failed.")
    return 1


# ---------------------------------------------------------------------------
# Project patching (only on copied project under data/, NEVER in styles/)
# ---------------------------------------------------------------------------
def patch_project_capture(proj: Path) -> None:
    """Update copied project's tools/capture.mjs to use .tmp and h264_nvenc."""
    cap = proj / "tools" / "capture.mjs"
    if not cap.is_file():
        return
    txt = cap.read_text(encoding="utf-8")
    tmp_js = str(TMP_DIR).replace("\\", "/")

    # Force Chromium user-data-dir & sheet temp dir into D:\...\.tmp
    txt = txt.replace("os.tmpdir()", f"'{tmp_js}'")

    # Ensure .geojson MIME type is supported
    if "'.geojson'" not in txt and "'.json': 'application/json'" in txt:
        txt = txt.replace("'.json': 'application/json'", "'.json': 'application/json', '.geojson': 'application/json'")

    # Switch libx264 -> h264_nvenc
    old_codec = (
        "'-c:v', 'libx264', '-preset', flags.has('--draft') ? 'ultrafast' : 'veryfast', "
        "'-crf', flags.has('--draft') ? '28' : '18', '-pix_fmt', 'yuv420p',"
    )
    new_codec = (
        "'-c:v', 'h264_nvenc', '-preset', flags.has('--draft') ? 'p1' : 'p4', "
        "'-rc', 'vbr', '-cq', flags.has('--draft') ? '28' : '20', '-pix_fmt', 'yuv420p',"
    )
    if old_codec in txt:
        txt = txt.replace(old_codec, new_codec)
    elif "'libx264'" in txt:
        txt = txt.replace("'libx264'", "'h264_nvenc'")

    cap.write_text(txt, encoding="utf-8")


def patch_project_mix(proj: Path) -> None:
    """Update copied project's tools/mix.py for +4 dB crisp SFX balance & ducking."""
    mix_py = proj / "tools" / "mix.py"
    if not mix_py.is_file():
        return
    txt = mix_py.read_text(encoding="utf-8")

    # +4 dB crisp boost on procedural SFX so cues cut through cleanly
    if "db(LEVEL[c['type']])" in txt and "+ 4.0" not in txt:
        txt = txt.replace("db(LEVEL[c['type']])", "db(LEVEL[c['type']] + 4.0)")

    # Enhanced ducking under narration
    old_duck = "m *= (1 - 0.55 * np.clip(lev * 3, 0, 1))[:, None]"
    new_duck = "m *= (1 - 0.65 * np.clip(lev * 3.5, 0, 1))[:, None]"
    if old_duck in txt:
        txt = txt.replace(old_duck, new_duck)

    mix_py.write_text(txt, encoding="utf-8")


# ---------------------------------------------------------------------------
# Automatic captions.srt sidecar export
# ---------------------------------------------------------------------------
def format_srt_time(sec: float) -> str:
    ms = int(round(max(0.0, sec) * 1000))
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(proj: Path) -> Path | None:
    """Export standard timed captions.srt from words.json and lines.json."""
    words_file = proj / "data" / "words.json"
    lines_file = proj / "data" / "lines.json"
    if not words_file.is_file():
        return None

    words = json.loads(words_file.read_text(encoding="utf-8-sig"))
    if not words:
        return None

    # Group words into 2-4 word readable subtitle cards
    srt_cues = []
    cur_tokens = []
    for w in words:
        cur_tokens.append(w)
        # Break on punctuation or after 3-4 words
        txt = w["w"].strip()
        is_break = re.search(r"[,.?!;:]$", txt) or len(cur_tokens) >= 4
        if is_break:
            srt_cues.append({
                "start": cur_tokens[0]["s"],
                "end": cur_tokens[-1]["e"],
                "text": " ".join(t["w"] for t in cur_tokens),
            })
            cur_tokens = []
    if cur_tokens:
        srt_cues.append({
            "start": cur_tokens[0]["s"],
            "end": cur_tokens[-1]["e"],
            "text": " ".join(t["w"] for t in cur_tokens),
        })

    lines_out = []
    for idx, cue in enumerate(srt_cues, start=1):
        lines_out.append(str(idx))
        lines_out.append(f"{format_srt_time(cue['start'])} --> {format_srt_time(cue['end'])}")
        lines_out.append(cue["text"])
        lines_out.append("")

    srt_path = proj / "data" / "captions.srt"
    srt_path.write_text("\n".join(lines_out), encoding="utf-8")
    print(f"Generated sidecar subtitles: {srt_path}")
    return srt_path


# ---------------------------------------------------------------------------
# Script parsing & caption chunking
# ---------------------------------------------------------------------------
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "in", "into", "is", "it", "its", "of", "on", "or", "so", "that", "the",
    "this", "to", "up", "was", "with", "your", "you",
}


def make_caps(text: str) -> str:
    """Split a line into 1-3 word uppercase chunks with one *KEYWORD per chunk."""
    raw_words = [w for w in text.strip().split() if w]
    if not raw_words:
        return ""
    chunks: list[list[str]] = []
    i = 0
    while i < len(raw_words):
        rem = len(raw_words) - i
        take = 2 if rem == 4 else min(3, rem)
        chunks.append(raw_words[i : i + take])
        i += take

    out_chunks = []
    for ch in chunks:
        best_idx = 0
        best_score = -1
        for idx, w in enumerate(ch):
            clean = re.sub(r"[^a-z0-9]", "", w.lower())
            score = len(clean) + (0 if clean in STOPWORDS else 10)
            if score > best_score:
                best_score = score
                best_idx = idx
        formatted = [
            f"*{w.upper()}" if idx == best_idx else w.upper()
            for idx, w in enumerate(ch)
        ]
        out_chunks.append(" ".join(formatted))
    return " | ".join(out_chunks)


def pick_keyword(text: str, line_idx: int | None = None, valid_words: list[str] | None = None) -> str:
    """Pick the most visually/narratively distinct word in a line for Wd(), verified against words.json if present."""
    norm_fn = lambda w: re.sub(r"[^a-z0-9']+", "", str(w).lower())
    raw_tokens = [w for w in text.split() if len(norm_fn(w)) >= 2]

    if valid_words:
        valid_set = set(valid_words)
        # Check raw tokens from the line that actually match Whisper heard words
        matched = [w for w in raw_tokens if norm_fn(w) in valid_set or any(v.startswith(norm_fn(w)) for v in valid_set)]
        if matched:
            content = [w for w in matched if norm_fn(w) not in STOPWORDS]
            pool = content or matched
            return norm_fn(max(pool, key=lambda w: len(norm_fn(w))))
        # Fallback to valid heard words for this line
        valid_content = [v for v in valid_words if v not in STOPWORDS and len(v) >= 3]
        pool = valid_content or valid_words
        if pool:
            return max(pool, key=len)

    words = [norm_fn(w) for w in raw_tokens if len(norm_fn(w)) >= 3]
    if not words:
        first = norm_fn(text.split()[0]) if text.split() else "hit"
        return first or "hit"
    content = [w for w in words if w not in STOPWORDS]
    pool = content or words
    return max(pool, key=len)


def load_script_lines(script_path: Path) -> list[dict]:
    if script_path.suffix.lower() == ".json":
        data = json.loads(script_path.read_text(encoding="utf-8-sig"))
        return data["lines"]
    raw_lines = [ln.strip() for ln in script_path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    return [{"text": ln, "caps": make_caps(ln)} for ln in raw_lines]


# ---------------------------------------------------------------------------
# TTS generation (kokoro_onnx if available, else edge-tts -> 24kHz WAV)
# ---------------------------------------------------------------------------
async def _edge_tts_to_wav(text: str, voice: str, rate_str: str, out_mp3: Path, out_wav: Path, env: dict[str, str]) -> None:
    import edge_tts
    comm = edge_tts.Communicate(text, voice=voice, rate=rate_str)
    await comm.save(str(out_mp3))
    subprocess.run(
        [str(FFMPEG_EXE), "-v", "error", "-y", "-i", str(out_mp3), "-ac", "1", "-ar", "24000", str(out_wav)],
        check=True,
        env=env,
    )


def generate_tts(proj: Path, voice_arg: str | None, speed: float, env: dict[str, str]) -> None:
    """Generate data/narration.wav and data/lines.json."""
    import importlib.util
    import numpy as np
    from scipy.io import wavfile

    # Prefer Kokoro if installed
    if importlib.util.find_spec("kokoro_onnx") is not None:
        cmd = [str(VENV_PY), str(ROOT / "scripts" / "voice.py"), str(proj), "--speed", str(speed)]
        if voice_arg:
            cmd += ["--voice", voice_arg]
        run_cmd(cmd, env=env)
        return

    # Otherwise use edge-tts (already installed in the local venv)
    script = json.loads((proj / "script.json").read_text(encoding="utf-8-sig"))
    edge_voice = voice_arg if (voice_arg and "Neural" in voice_arg) else "en-US-AndrewNeural"
    pct = round((speed - 1.0) * 100)
    rate_str = f"{pct:+d}%"
    sr = 24000

    def trim_audio(x: np.ndarray, thr: float = 0.008) -> np.ndarray:
        idx = np.where(np.abs(x) > thr)[0]
        if not len(idx):
            return x
        a = max(0, idx[0] - int(0.01 * sr))
        b = min(len(x), idx[-1] + int(0.03 * sr))
        return x[a:b]

    def find_silences(x: np.ndarray, thr: float = 0.012, min_len: float = 0.06) -> list[tuple[float, float]]:
        hop = int(0.01 * sr)
        n = len(x) // hop
        if n <= 0:
            return []
        rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1))
        quiet = rms < thr * (np.abs(x).max() + 1e-9)
        out, st = [], None
        for f, q in enumerate(quiet):
            if q and st is None:
                st = f
            if (not q or f == n - 1) and st is not None:
                if (f - st) * 0.01 >= min_len:
                    out.append((st * 0.01, f * 0.01))
                st = None
        return out

    async def synth_array(txt: str, tag: str) -> np.ndarray:
        mp3 = TMP_DIR / f"tts_{tag}.mp3"
        wav = TMP_DIR / f"tts_{tag}.wav"
        await _edge_tts_to_wav(txt, edge_voice, rate_str, mp3, wav, env)
        _, data = wavfile.read(wav)
        arr = data.astype(np.float64) / 32768.0
        mp3.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
        return trim_audio(arr)

    groups: list[list[int]] = []
    cur: list[int] = []
    for i, ln in enumerate(script["lines"]):
        cur.append(i)
        if re.search(r'[.?!]["\')]*$', ln["text"].strip()) or ln.get("break") or i == len(script["lines"]) - 1:
            groups.append(cur)
            cur = []

    lead_s = float(script.get("lead", 0.4))
    out_chunks = [np.zeros(int(lead_s * sr))]
    t = len(out_chunks[0]) / sr
    lines_out: list[dict] = [{}] * len(script["lines"])

    async def build_all() -> None:
        nonlocal t
        for g_idx, g in enumerate(groups):
            full_text = " ".join(script["lines"][i]["text"] for i in g)
            x = await synth_array(full_text, f"g{g_idx}")
            cuts: list[float | tuple[float, float]] = [0.0]
            if len(g) > 1:
                lens = np.array([len(script["lines"][i]["text"]) for i in g], dtype=float)
                pauses = find_silences(x)
                for c in np.cumsum(lens)[:-1] / lens.sum() * (len(x) / sr):
                    near = [p for p in pauses if abs((p[0] + p[1]) / 2 - c) < 0.4]
                    if near:
                        p = min(near, key=lambda p: abs((p[0] + p[1]) / 2 - c))
                        cuts.append((p[0], p[1]))
                    else:
                        cuts.append((c, c))
            n_sec = len(x) / sr
            for j, i in enumerate(g):
                a = 0.0 if j == 0 else cuts[j][1]  # type: ignore[index]
                b = n_sec if j == len(g) - 1 else cuts[j + 1][0]  # type: ignore[index]
                lines_out[i] = {
                    "i": i,
                    "text": script["lines"][i]["text"],
                    "start": round(t + a, 3),
                    "end": round(t + b, 3),
                }
                print(f"{i:2d} {lines_out[i]['start']:6.2f}-{lines_out[i]['end']:6.2f}  {script['lines'][i]['text']}", flush=True)
            gap_s = float(script["lines"][g[-1]].get("gap", script.get("gap", 0.28)))
            gap = np.zeros(int(gap_s * sr))
            out_chunks.extend([x, gap])
            t += (len(x) + len(gap)) / sr

    try:
        asyncio.run(build_all())
    except Exception as exc:
        print(f"[WARN] edge-tts failed ({exc}); falling back to estimate.py timing", flush=True)
        run_cmd([str(VENV_PY), str(ROOT / "scripts" / "estimate.py"), str(proj)], env=env)
        return

    outro = np.zeros(int(float(script.get("outro", 0.9)) * sr))
    out_chunks.append(outro)
    y = np.concatenate(out_chunks)
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    (proj / "data").mkdir(exist_ok=True)
    wavfile.write(proj / "data" / "narration.wav", sr, (y * 32767).astype(np.int16))
    dur = len(y) / sr
    (proj / "data" / "lines.json").write_text(
        json.dumps({"duration": round(dur, 3), "voice": edge_voice, "speed": speed, "lines": lines_out}, indent=1),
        encoding="utf-8",
    )
    print(f"data/narration.wav ({dur:.2f} s, {edge_voice} x{speed}) + data/lines.json")


# ---------------------------------------------------------------------------
# Bespoke beat-synced src/shots.js generator (Clean 9:16 Safe-Zone Rules)
# ---------------------------------------------------------------------------
def build_shots_js(proj: Path, style: str, topic: str) -> None:
    """Generate a clean bespoke beat-synced src/shots.js with zero centerpiece face pills."""
    script = json.loads((proj / "script.json").read_text(encoding="utf-8-sig"))
    lines = script["lines"]

    # Load words.json if present to ensure keywords are verified against actual Whisper detections
    words_by_line: dict[int, list[str]] = {}
    words_file = proj / "data" / "words.json"
    if words_file.is_file():
        try:
            words_data = json.loads(words_file.read_text(encoding="utf-8-sig"))
            norm_fn = lambda w: re.sub(r"[^a-z0-9']+", "", str(w).lower())
            for wd in words_data:
                l_idx = wd.get("line", 0)
                nw = norm_fn(wd.get("w", ""))
                if nw:
                    words_by_line.setdefault(l_idx, []).append(nw)
        except Exception:
            pass

    shot_meta = []
    prev_mod = ""
    for i, ln in enumerate(lines):
        valid_words = words_by_line.get(i)
        kw = pick_keyword(ln["text"], line_idx=i, valid_words=valid_words)
        header_badge = re.sub(r"[^A-Z0-9 ]", "", kw.upper())[:18] or f"STEP {i + 1}"
        vis = analyze_line_visuals(ln["text"], i, len(lines), prev_mod=prev_mod)
        prev_mod = vis["mod"]
        shot_meta.append({
            "i": i,
            "kw": kw,
            "badge": header_badge,
            "text": ln["text"],
            "mod": vis["mod"],
            "val": vis.get("val", ""),
            "labelA": vis.get("labelA", "MYTH"),
            "labelB": vis.get("labelB", "REALITY"),
        })

    meta_json = json.dumps(shot_meta, indent=2)
    topic_esc = json.dumps(topic)

    if style == "stick-story":
        code = f"""// Bespoke beat-synced shot list for {topic_esc} (stick-story)
// Clean 9:16 layout: Title badge in header band (y: 290-340), visual action in center (y: 500-1450),
// captions in bottom band (y: 1690). Never puts text pills over face/mouth.
import {{ ctx, W, H, clamp, lerp, seg, eo, eio, eob, rnd, rr, line, circle, ell }} from './core/lib.js';
import {{ L, Wd, T }} from './core/timing.js';
import * as K from './core/kit.js';

const SHOTS_META = {meta_json};

export function buildShots() {{
  const S = [], CUES = [];
  const add = (o) => (S.push(o), o);
  const cue = (t, type, o = {{}}) => CUES.push({{ t: +t.toFixed(3), type, ...o }});
  const cut = (i) => (i === 0 ? 0 : L(i) - 0.08);
  const safeWd = (kw, i, fallback) => {{
    try {{
      if (!kw) return fallback;
      return Wd(kw, i);
    }} catch {{
      return fallback;
    }}
  }};

  const n = SHOTS_META.length;
  SHOTS_META.forEach((m, i) => {{
    const st = cut(i);
    const end = i < n - 1 ? cut(i + 1) : T.dur;
    const d_shot = end - st;
    const hitT = Math.max(0.12, safeWd(m.kw, i, st + d_shot * 0.45) - st);
    const isLast = i === n - 1;

    add({{
      id: `S${{String(i + 1).padStart(2, '0')}}`,
      at: st,
      cam: [540, 960],
      zoom: i === 0 ? 0.12 : 0.08,
      note: m.text.slice(0, 48),
      draw(lt, d, t) {{
        const loopK = isLast && lt > d - 0.5 ? clamp((lt - (d - 0.5)) / 0.5) : 0;
        const bannerAlpha = isLast ? (1 - loopK) : 1;
        const pop = eob(seg(lt, 0.05, 0.32));
        const hit = lt > hitT ? eob(seg(lt, hitT, hitT + 0.28)) : 0;

        // Base environment
        K.livingRoom({{ night: i % 2 === 1, lampOn: i % 2 === 0 }});

        // Center visual staging area (y: 500-1450)
        if (m.mod === 'counter' || m.mod === 'year') {{
          ctx.save();
          ctx.translate(540, 860);
          ctx.scale(pop, pop);
          rr(-330, -140, 660, 280, 26);
          ctx.fillStyle = '#182030';
          ctx.fill();
          ctx.strokeStyle = hit > 0 ? '#F2B23E' : '#32405A';
          ctx.lineWidth = 6;
          ctx.stroke();

          ctx.font = '900 84px Inter';
          ctx.fillStyle = hit > 0 ? '#F2B23E' : '#FFFFFF';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(m.val || '100%', 0, -22);

          ctx.font = '700 32px Inter';
          ctx.fillStyle = '#A4B4CC';
          ctx.fillText(m.badge, 0, 60);
          ctx.restore();

          K.person({{
            x: 540 + Math.sin(lt * 2) * 8,
            y: K.GROUND,
            h: 700,
            dir: 1,
            mood: hit > 0 ? 'determined' : 'calm',
            look: [0.3, -0.4],
          }});
        }} else if (m.mod === 'comparison') {{
          ctx.save();
          ctx.translate(540, 860);
          ctx.scale(pop, pop);

          // Left Box (Myth/A)
          rr(-420, -140, 380, 280, 20);
          ctx.fillStyle = '#2A181C';
          ctx.fill();
          ctx.strokeStyle = '#E2574C';
          ctx.lineWidth = 5;
          ctx.stroke();
          ctx.font = '900 42px Inter';
          ctx.fillStyle = '#E2574C';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(m.labelA || 'MYTH', -230, -25);
          ctx.font = '700 28px Inter';
          ctx.fillStyle = '#E8A09A';
          ctx.fillText('FAIL', -230, 45);

          // Right Box (Reality/B)
          rr(40, -140, 380, 280, 20);
          ctx.fillStyle = '#182A1C';
          ctx.fill();
          ctx.strokeStyle = '#6DB36A';
          ctx.lineWidth = 5;
          ctx.stroke();
          ctx.font = '900 42px Inter';
          ctx.fillStyle = '#6DB36A';
          ctx.fillText(m.labelB || 'REALITY', 230, -25);
          ctx.font = '700 28px Inter';
          ctx.fillStyle = '#A0E8A8';
          ctx.fillText('WIN', 230, 45);

          // Center VS pill
          circle(0, 0, 54, '#F2B23E');
          ctx.font = '900 38px Inter';
          ctx.fillStyle = '#1C1C22';
          ctx.fillText('VS', 0, 2);
          ctx.restore();

          K.person({{
            x: 540,
            y: K.GROUND,
            h: 680,
            dir: 1,
            mood: hit > 0 ? 'happy' : 'worried',
          }});
        }} else if (m.mod === 'falling') {{
          // Strict upward scroll for falling background markers (-y)
          const scrollSpeed = 460;
          const scrollY = (lt * scrollSpeed) % 240;
          ctx.strokeStyle = '#2A344A';
          ctx.lineWidth = 6;
          for (let fy = -300; fy < H + 300; fy += 240) {{
            const yBeam = fy - scrollY;
            line([[200, yBeam], [880, yBeam]], '#242D40', 6);
          }}

          // Falling elevator cab
          const cabX = 540 + Math.sin(lt * 24) * 3;
          const cabY = 880;
          rr(cabX - 260, cabY - 320, 520, 640, 16);
          ctx.fillStyle = 'rgba(18, 24, 38, 0.9)';
          ctx.fill();
          ctx.strokeStyle = '#5E7094';
          ctx.lineWidth = 8;
          ctx.stroke();

          // Downward velocity arrow
          line([[cabX + 180, cabY - 140], [cabX + 180, cabY + 160]], '#E2574C', 12);
          ctx.beginPath();
          ctx.moveTo(cabX + 155, cabY + 140);
          ctx.lineTo(cabX + 180, cabY + 185);
          ctx.lineTo(cabX + 205, cabY + 140);
          ctx.closePath();
          ctx.fillStyle = '#E2574C';
          ctx.fill();

          K.person({{
            x: cabX - 40,
            y: cabY + 280,
            h: 520,
            dir: 1,
            mood: 'scared',
            blink: (t % 2.5) < 0.15 ? 1 : 0,
          }});
        }} else if (m.mod === 'jumping') {{
          const jumpPhase = seg(lt, hitT, hitT + 0.35);
          const jumpY = jumpPhase > 0 ? Math.sin(jumpPhase * Math.PI) * 220 : 0;
          // Upward velocity vector arrow (+y screen up)
          line([[740, 1080], [740, 750]], '#6DB36A', 12);
          ctx.beginPath();
          ctx.moveTo(715, 770);
          ctx.lineTo(740, 725);
          ctx.lineTo(765, 770);
          ctx.closePath();
          ctx.fillStyle = '#6DB36A';
          ctx.fill();

          K.person({{
            x: 540,
            y: K.GROUND - jumpY,
            h: 740,
            dir: 1,
            mood: jumpPhase > 0 ? 'determined' : 'worried',
          }});
        }} else if (m.mod === 'map') {{
          ctx.save();
          ctx.translate(540, 860);
          ctx.scale(pop, pop);
          circle(0, 0, 260, '#162235');
          ctx.strokeStyle = '#2E4362';
          ctx.lineWidth = 4;
          ctx.stroke();
          line([[-260, 0], [260, 0]], 'rgba(74, 110, 160, 0.4)', 2);
          line([[0, -260], [0, 260]], 'rgba(74, 110, 160, 0.4)', 2);

          const pRing = ((lt * 180) % 260);
          circle(0, 0, pRing, 'transparent');
          ctx.strokeStyle = `rgba(242, 178, 62, ${{1 - pRing / 260}})`;
          ctx.lineWidth = 3;
          ctx.stroke();

          circle(0, 0, 22, '#E2574C');
          ctx.font = '700 36px Inter';
          ctx.fillStyle = '#FFFFFF';
          ctx.textAlign = 'center';
          ctx.fillText(m.badge, 0, 60);
          ctx.restore();

          K.person({{
            x: 280,
            y: K.GROUND,
            h: 700,
            dir: 1,
            mood: 'calm',
          }});
        }} else {{
          // Standard kinetic character action
          const mood = hit > 0 ? (i >= n - 2 ? 'happy' : 'determined') : (i === 0 ? 'scared' : 'calm');
          K.person({{
            glow: true,
            x: 540 + Math.sin(lt * 2) * 12,
            y: K.GROUND,
            h: 820,
            dir: 1,
            mood,
            look: [Math.sin(lt * 2.5) * 0.4, -0.2],
            blink: (t % 3.1) < 0.12 ? 1 : 0,
          }});

          if (hit > 0 && bannerAlpha > 0.01) {{
            if (i >= n - 2) K.check(540, 560, hit);
            else if (i % 3 === 2) K.cross(540, 560, hit);
          }}
        }}

        // Header badge strictly in top band (y: 310), crossfades cleanly on loop
        if (pop > 0 && bannerAlpha > 0.01) {{
          ctx.save();
          ctx.globalAlpha = bannerAlpha;
          K.stepCard(i + 1, m.badge, 540, 310, pop);
          ctx.restore();
        }}

        // Clean loop transition back to Frame 0
        if (loopK > 0) {{
          ctx.save();
          ctx.globalAlpha = loopK;
          K.livingRoom({{ night: false, lampOn: true }});
          K.stepCard(1, SHOTS_META[0].badge, 540, 310, 1.0);
          ctx.restore();
        }}
      }},
    }});

    if (i > 0) cue(st, 'whoosh', {{ gain: 0.8 }});
    cue(st + 0.08, 'pop', {{ gain: 0.6 }});
    cue(st + hitT, i >= n - 2 ? 'boing' : i % 2 === 0 ? 'thud' : 'slam', {{ gain: 0.75 }});
  }});

  return {{ shots: S, cues: CUES }};
}}
"""
    elif style == "paper-atlas":
        code = f"""// Bespoke beat-synced shot list for {topic_esc} (paper-atlas)
import {{ ctx, W, H, TAU, clamp, lerp, seg, eo, eio, eob, rnd, rr, circle, ell, line }} from './core/lib.js';
import {{ L, Wd, T }} from './core/timing.js';
import * as K from './core/kit.js';

const SHOTS_META = {meta_json};

export function buildShots() {{
  const S = [], CUES = [];
  const add = (o) => (S.push(o), o);
  const cue = (t, type, o = {{}}) => CUES.push({{ t: +t.toFixed(3), type, ...o }});
  const cut = (i) => (i === 0 ? 0 : L(i) - 0.08);
  const safeWd = (kw, i, fallback) => {{
    try {{
      if (!kw) return fallback;
      return Wd(kw, i);
    }} catch {{
      return fallback;
    }}
  }};

  const n = SHOTS_META.length;
  SHOTS_META.forEach((m, i) => {{
    const st = cut(i);
    const end = i < n - 1 ? cut(i + 1) : T.dur;
    const d_shot = end - st;
    const hitT = Math.max(0.12, safeWd(m.kw, i, st + d_shot * 0.45) - st);
    const isLast = i === n - 1;

    add({{
      id: `S${{String(i + 1).padStart(2, '0')}}`,
      at: st,
      cam: [540, 960],
      zoom: 0.08,
      note: m.text.slice(0, 48),
      draw(lt, d, t) {{
        const loopK = isLast && lt > d - 0.5 ? clamp((lt - (d - 0.5)) / 0.5) : 0;
        const bannerAlpha = isLast ? (1 - loopK) : 1;
        const pop = eob(seg(lt, 0.05, 0.32));
        const hit = lt > hitT ? eob(seg(lt, hitT, hitT + 0.28)) : 0;

        if (m.mod === 'map') {{
          K.map({{ highlight: i % 3, route: clamp(lt / (d * 0.75)), seed: i + 3 }});
        }} else {{
          K.parchment(i * 3 + 1);

          if (m.mod === 'counter' || m.mod === 'year') {{
            K.seal(540, 840, 1.4, m.val ? String(m.val).slice(0, 4) : '1666');
            K.slip(m.badge, 540, 1080, pop, -0.02, 44);
          }} else if (m.mod === 'comparison') {{
            K.slip(m.labelA || 'OLD WAY', 320, 840, pop, -0.04, 38);
            K.slip(m.labelB || 'NEW ROUTE', 760, 840, pop, 0.04, 38);
            K.seal(540, 840, 0.85, 'VS');
          }} else {{
            K.figure({{
              x: 540,
              y: 1320,
              h: 700,
              role: (i % 2 === 0 ? 'king' : 'merchant'),
              dir: 1,
              walk: lt * 4,
            }});
          }}
        }}

        // Header ribbon strictly in top band (y: 310)
        if (pop > 0 && bannerAlpha > 0.01) {{
          ctx.save();
          ctx.globalAlpha = bannerAlpha;
          K.ribbon(m.badge, 540, 310, pop, 44);
          ctx.restore();
        }}

        // Clean loop transition back to Frame 0
        if (loopK > 0) {{
          ctx.save();
          ctx.globalAlpha = loopK;
          K.parchment(1);
          K.ribbon(SHOTS_META[0].badge, 540, 310, 1.0, 44);
          ctx.restore();
        }}
      }},
    }});

    if (i > 0) cue(st, 'whoosh', {{ gain: 0.8 }});
    cue(st + 0.08, 'pop', {{ gain: 0.6 }});
    cue(st + hitT, 'tock', {{ gain: 0.7 }});
  }});

  return {{ shots: S, cues: CUES }};
}}
"""
    elif style == "tall-tale":
        code = f"""// Bespoke beat-synced shot list for {topic_esc} (tall-tale)
import {{ ctx, W, H, clamp, lerp, seg, eo, eio, eob, rnd, rr, line, circle }} from './core/lib.js';
import {{ L, Wd, T }} from './core/timing.js';

const SHOTS_META = {meta_json};

export function buildShots(E) {{
  const S = [], CUES = [];
  const add = (o) => (S.push(o), o);
  const cue = (t, type, o = {{}}) => CUES.push({{ t: +t.toFixed(3), type, ...o }});
  const cut = (i) => (i === 0 ? 0 : L(i) - 0.08);
  const safeWd = (kw, i, fallback) => {{
    try {{
      if (!kw) return fallback;
      return Wd(kw, i);
    }} catch {{
      return fallback;
    }}
  }};

  const n = SHOTS_META.length;
  SHOTS_META.forEach((m, i) => {{
    const st = cut(i);
    const end = i < n - 1 ? cut(i + 1) : T.dur;
    const d_shot = end - st;
    const hitT = Math.max(0.12, safeWd(m.kw, i, st + d_shot * 0.45) - st);
    const isLast = i === n - 1;

    add({{
      id: `S${{String(i + 1).padStart(2, '0')}}`,
      at: st,
      cam: [540, 960],
      zoom: 0.08,
      note: m.text.slice(0, 48),
      draw(lt, d, t, blit) {{
        const loopK = isLast && lt > d - 0.5 ? clamp((lt - (d - 0.5)) / 0.5) : 0;
        const bannerAlpha = isLast ? (1 - loopK) : 1;
        const pop = eob(seg(lt, 0.05, 0.32));
        const hit = lt > hitT ? eob(seg(lt, hitT, hitT + 0.28)) : 0;

        // Vintage comic paper background
        ctx.fillStyle = '#F5EFEB';
        ctx.fillRect(-300, -300, W + 600, H + 600);

        // Center visual staging area (y: 500-1450)
        if (m.mod === 'counter' || m.mod === 'year') {{
          ctx.save();
          ctx.translate(540, 860);
          ctx.scale(pop, pop);
          rr(-330, -140, 660, 280, 24);
          ctx.fillStyle = '#2A2421';
          ctx.fill();
          ctx.strokeStyle = '#D9A441';
          ctx.lineWidth = 6;
          ctx.stroke();

          ctx.font = '900 82px Inter';
          ctx.fillStyle = '#FFD43B';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(m.val || '$200,000', 0, -20);

          ctx.font = '700 32px Inter';
          ctx.fillStyle = '#F5EFEB';
          ctx.fillText(m.badge, 0, 60);
          ctx.restore();
        }} else if (m.mod === 'comparison') {{
          ctx.save();
          ctx.translate(540, 860);
          ctx.scale(pop, pop);

          rr(-420, -140, 380, 280, 20);
          ctx.fillStyle = '#3E2426';
          ctx.fill();
          ctx.strokeStyle = '#D8343F';
          ctx.lineWidth = 6;
          ctx.stroke();
          ctx.font = '900 42px Inter';
          ctx.fillStyle = '#D8343F';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(m.labelA || 'TRICK', -230, 0);

          rr(40, -140, 380, 280, 20);
          ctx.fillStyle = '#223428';
          ctx.fill();
          ctx.strokeStyle = '#4FB3A9';
          ctx.lineWidth = 6;
          ctx.stroke();
          ctx.font = '900 42px Inter';
          ctx.fillStyle = '#4FB3A9';
          ctx.fillText(m.labelB || 'REALITY', 230, 0);

          circle(0, 0, 54, '#FFD43B');
          ctx.font = '900 38px Inter';
          ctx.fillStyle = '#221C16';
          ctx.fillText('VS', 0, 2);
          ctx.restore();
        }} else {{
          // Cartoon character figure in center
          ctx.save();
          ctx.translate(540, 1100);
          circle(0, -220, 90, '#E8A760');
          // Eyes
          circle(-25, -230, 18, '#FFFFFF');
          circle(25, -230, 18, '#FFFFFF');
          circle(-20, -230, 8, '#1C1C22');
          circle(30, -230, 8, '#1C1C22');
          // Body
          rr(-70, -120, 140, 220, 20);
          ctx.fillStyle = i % 2 === 0 ? '#4FB3A9' : '#D8343F';
          ctx.fill();
          ctx.restore();
        }}

        // Header step badge strictly in top band (y: 310)
        if (pop > 0 && bannerAlpha > 0.01) {{
          ctx.save();
          ctx.globalAlpha = bannerAlpha;
          rr(140, 260, 800, 100, 18);
          ctx.fillStyle = '#221C16';
          ctx.fill();
          ctx.strokeStyle = '#FFD43B';
          ctx.lineWidth = 4;
          ctx.stroke();
          ctx.font = '900 44px Inter';
          ctx.fillStyle = '#FFD43B';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(m.badge, 540, 310);
          ctx.restore();
        }}

        // Clean loop transition back to Frame 0
        if (loopK > 0) {{
          ctx.save();
          ctx.globalAlpha = loopK;
          ctx.fillStyle = '#F5EFEB';
          ctx.fillRect(-300, -300, W + 600, H + 600);
          rr(140, 260, 800, 100, 18);
          ctx.fillStyle = '#221C16';
          ctx.fill();
          ctx.fillStyle = '#FFD43B';
          ctx.font = '900 44px Inter';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(SHOTS_META[0].badge, 540, 310);
          ctx.restore();
        }}
      }},
    }});

    if (i > 0) cue(st, 'whoosh', {{ gain: 0.8 }});
    cue(st + 0.08, 'pop', {{ gain: 0.6 }});
    cue(st + hitT, 'thud', {{ gain: 0.7 }});
  }});

  return {{ shots: S, cues: CUES }};
}}
"""
    else:
        # Universal fallback
        code = f"""// Bespoke beat-synced shot list for {topic_esc} ({style})
import {{ ctx, W, H, clamp, lerp, seg, eo, eio, eob, rnd, rr, line, circle }} from './core/lib.js';
import {{ L, Wd, T }} from './core/timing.js';
import * as K from './core/kit.js';

const SHOTS_META = {meta_json};

export function buildShots(E) {{
  const S = [], CUES = [];
  const add = (o) => (S.push(o), o);
  const cue = (t, type, o = {{}}) => CUES.push({{ t: +t.toFixed(3), type, ...o }});
  const cut = (i) => (i === 0 ? 0 : L(i) - 0.08);
  const safeWd = (kw, i, fallback) => {{
    try {{
      if (!kw) return fallback;
      return Wd(kw, i);
    }} catch {{
      return fallback;
    }}
  }};

  const n = SHOTS_META.length;
  SHOTS_META.forEach((m, i) => {{
    const st = cut(i);
    const end = i < n - 1 ? cut(i + 1) : T.dur;
    const d_shot = end - st;
    const hitT = Math.max(0.12, safeWd(m.kw, i, st + d_shot * 0.45) - st);
    const isLast = i === n - 1;

    add({{
      id: `S${{String(i + 1).padStart(2, '0')}}`,
      at: st,
      cam: [540, 960],
      zoom: 0.1,
      note: m.text.slice(0, 48),
      draw(lt, d, t, blit) {{
        const loopK = isLast && lt > d - 0.5 ? clamp((lt - (d - 0.5)) / 0.5) : 0;
        const bannerAlpha = isLast ? (1 - loopK) : 1;

        ctx.fillStyle = '#0F131D';
        ctx.fillRect(-300, -300, W + 600, H + 600);

        if (bannerAlpha > 0.01) {{
          ctx.save();
          ctx.globalAlpha = bannerAlpha;
          rr(140, 260, 800, 100, 14);
          ctx.fillStyle = '#1A2130';
          ctx.fill();
          ctx.strokeStyle = '#3E4D68';
          ctx.lineWidth = 4;
          ctx.stroke();
          ctx.fillStyle = '#F4E7CE';
          ctx.font = '700 48px Inter';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(m.badge, 540, 310);
          ctx.restore();
        }}

        const hit = lt > hitT ? eob(seg(lt, hitT, hitT + 0.28)) : 0;
        ctx.save();
        circle(540, 960, 240 + hit * 20, '#1E2638');
        ctx.fillStyle = '#E4322B';
        ctx.font = '900 84px Inter';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(i + 1), 540, 960);
        ctx.restore();

        if (loopK > 0) {{
          ctx.save();
          ctx.globalAlpha = loopK;
          ctx.fillStyle = '#0F131D';
          ctx.fillRect(-300, -300, W + 600, H + 600);
          rr(140, 260, 800, 100, 14);
          ctx.fillStyle = '#1A2130';
          ctx.fill();
          ctx.fillStyle = '#F4E7CE';
          ctx.font = '700 48px Inter';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(SHOTS_META[0].badge, 540, 310);
          ctx.restore();
        }}
      }},
    }});

    if (i > 0) cue(st, 'whoosh', {{ gain: 0.7 }});
    cue(st + 0.08, 'pop', {{ gain: 0.5 }});
    cue(st + hitT, 'thud', {{ gain: 0.65 }});
  }});

  return {{ shots: S, cues: CUES }};
}}
"""

    (proj / "src" / "shots.js").write_text(code, encoding="utf-8")


# ---------------------------------------------------------------------------
# create & render
# ---------------------------------------------------------------------------
def cmd_create(args: argparse.Namespace) -> int:
    env = enforce_d_drive_env()

    topic = args.topic.strip()
    script_path = Path(args.script) if args.script else None

    if script_path:
        if not script_path.is_file():
            raise SystemExit(f"Script file not found: {script_path}")
        script_text = script_path.read_text(encoding="utf-8-sig")
        lines = load_script_lines(script_path)
    else:
        print(f"Generating high-retention narration script for: '{topic}'...")
        raw_sentences = generate_script_from_topic(topic)
        script_text = "\n".join(raw_sentences)
        lines = [{"text": s, "caps": make_caps(s)} for s in raw_sentences]
        print(f"Generated {len(lines)} sentences (~35-45s retention structure).")

    style = args.style.strip() if args.style else "auto"
    if style == "auto":
        style = detect_best_style(topic, script_text)
        print(f"Auto-selected base style: '{style}' based on topic and script content.")

    src_example = STYLES_DIR / style / "example"
    if not src_example.is_dir():
        avail = sorted(p.name for p in STYLES_DIR.iterdir() if p.is_dir())
        raise SystemExit(f"Unknown style '{style}'. Available: {', '.join(avail)}")

    date_str = dt.date.today().strftime("%Y-%m-%d")
    base_slug = slugify(topic)
    date_dir = DATA_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)
    proj = date_dir / base_slug
    suffix = 2
    while proj.exists():
        proj = date_dir / f"{base_slug}-{suffix}"
        suffix += 1

    print(f"Creating project: {proj} (base style: {style})")
    shutil.copytree(src_example, proj)

    # Clean stale example media/timing
    for stale in ("narration.wav", "mix.wav", "cues.json", "lines.json", "words.json", "words.txt", "captions.srt", "script.txt"):
        (proj / "data" / stale).unlink(missing_ok=True)
    (proj / "data").mkdir(exist_ok=True)
    (proj / "renders").mkdir(exist_ok=True)
    (proj / "review").mkdir(exist_ok=True)

    # Save narration text to data/script.txt for zero-AI re-renders
    (proj / "data" / "script.txt").write_text(script_text, encoding="utf-8")

    # Copy real world.geojson so projects can render real geographic coastlines
    shared_geo = ROOT / "shared" / "world.geojson"
    if shared_geo.is_file():
        shutil.copy2(shared_geo, proj / "data" / "world.geojson")

    # Patch copied project's capture.mjs & mix.py (D: .tmp + h264_nvenc + +4dB SFX) without touching styles/
    patch_project_capture(proj)
    patch_project_mix(proj)

    # Write script.json
    music_mode = args.music or ("tension" if style in ("deep-dive", "night-file") else "bed")
    script_obj = {
        "title": topic,
        "voice": args.voice or "am_michael",
        "speed": args.speed,
        "lead": 0.4,
        "outro": 0.9,
        "gap": 0.28,
        "music": music_mode,
        "sources": [],
        "lines": lines,
    }
    (proj / "script.json").write_text(json.dumps(script_obj, indent=2), encoding="utf-8")

    # TTS + Whisper word timestamps
    print("Generating TTS narration...")
    generate_tts(proj, args.voice, args.speed, env)

    print("Aligning word timestamps with Whisper...")
    run_cmd([str(VENV_PY), str(ROOT / "scripts" / "words.py"), str(proj)], env=env)

    # Export sidecar captions.srt
    generate_srt(proj)

    # Bespoke beat-synced src/shots.js (clean layout, no mouth-pills)
    print(f"Generating bespoke beat-synced src/shots.js ({style})...")
    build_shots_js(proj, style, topic)

    # Validate with capture.mjs check
    print("Validating project with capture.mjs check...")
    run_cmd(["node", "tools/capture.mjs", "check"], cwd=proj, env=env)

    print(f"\nPROJECT READY: {proj}")
    if args.render:
        return cmd_render(argparse.Namespace(project_dir=str(proj), draft=args.draft, sheet=args.sheet))
    print(f"Next: .\\faceless.ps1 render \"{proj}\"")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    env = enforce_d_drive_env()
    proj = Path(args.project_dir).resolve()
    if not proj.is_dir():
        raise SystemExit(f"Project directory not found: {proj}")

    # Ensure copied project uses D: .tmp, h264_nvenc, and +4dB SFX boost
    patch_project_capture(proj)
    patch_project_mix(proj)

    print(f"Rendering project: {proj}")
    run_cmd(["node", "tools/capture.mjs", "cues"], cwd=proj, env=env)
    run_cmd([str(VENV_PY), "tools/mix.py", "."], cwd=proj, env=env)

    out_mp4 = proj / "renders" / "out.mp4"
    video_cmd = ["node", "tools/capture.mjs", "video", "renders/out.mp4"]
    if getattr(args, "draft", False):
        video_cmd.append("--draft")
    run_cmd(video_cmd, cwd=proj, env=env)

    if getattr(args, "sheet", False):
        run_cmd(["node", "tools/capture.mjs", "sheet", "review/all.jpg", "0.5", "9"], cwd=proj, env=env)

    if out_mp4.is_file():
        size_mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"RENDER COMPLETE: {out_mp4} ({size_mb:.2f} MB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="faceless")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Verify Node, Chrome, FFmpeg, Python venv, Shared SFX, and h264_nvenc")

    p_create = sub.add_parser("create", help="Create a new short project from a script or topic")
    p_create.add_argument("--topic", required=True, help="Short title / topic")
    p_create.add_argument("--script", default=None, help="Path to script .txt or .json (optional, auto-generates if omitted)")
    p_create.add_argument("--style", default="auto", help="Base style (auto | stick-story | paper-atlas | tall-tale)")
    p_create.add_argument("--voice", default=None, help="TTS voice override")
    p_create.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
    p_create.add_argument("--music", default=None, help="Music mode: bed | tension | none | path")
    p_create.add_argument("--render", action="store_true", help="Also render MP4 immediately")
    p_create.add_argument("--draft", action="store_true", help="Fast draft encode when --render is set")
    p_create.add_argument("--sheet", action="store_true", help="Also render contact sheet when --render is set")

    p_render = sub.add_parser("render", help="Render an existing project with NVENC")
    p_render.add_argument("project_dir", help="Path to project directory")
    p_render.add_argument("--draft", action="store_true", help="Fast draft encode")
    p_render.add_argument("--sheet", action="store_true", help="Also generate review/all.jpg contact sheet")

    args = ap.parse_args()
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "create":
        return cmd_create(args)
    if args.cmd == "render":
        return cmd_render(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
