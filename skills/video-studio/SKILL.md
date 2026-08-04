---
name: video-studio
description: End-to-end YouTube + TikTok video pipeline — plan, record, transcribe, plan the edit, cut, animate, caption and render a finished MP4. Nine resumable phases driven by state.json and edl.json. Use when the user wants to plan a video, script an outline, transcribe a recording, plan cuts, remove filler words and dead space, add motion graphics or b-roll, add word-by-word captions, reframe to 9:16, or render a final video. Triggers — "video-studio", "editar video", "plan de video", "cortar el video", "quitar silencios", "subtitulos palabra por palabra", "hacer un short", "reframe 9:16", "b-roll", "motion graphics", "render final", "edit my video", "make a short".
---

# Video Studio

Nine-phase pipeline that takes a video idea to a rendered MP4. Every phase reads and
writes one project folder. Phases resume — stop after any gate, come back days later.

**All user-facing output (`.md` files, captions, on-screen text) is written in Spanish.**
Code, JSON keys, filenames and directory names stay in English.

## Non-negotiables

1. **Never skip a gate.** Phases 0, 3 and 7 end by presenting work and stopping.
   Do not advance past a gate without the user saying yes.
2. **`edl.json` is the single source of truth for the edit.** Markdown is for the human;
   JSON is what ffmpeg executes. If they disagree, fix the JSON and regenerate the markdown.
3. **All times in `edl.json` are SOURCE time** (timestamps in the original recording).
   `cut.py` produces `build/timemap.json` which maps source time → output time.
   Never hand-author output time.
4. **Never delete `raw/`.** Every phase is reproducible from the raw recording + `edl.json`.
5. **Never auto-remove ambiguous filler words.** See `references/filler-words-es.md` —
   only tier-1 fillers are cut without asking.

## Resolving `$SKILL` in the commands below

Phase files write script paths as `$SKILL/scripts/...`. `$SKILL` is **this
skill's own directory**, which differs by install scope:

| Install | Path |
|---|---|
| global | `~/.claude/skills/video-studio` |
| project | `./.claude/skills/video-studio` |
| other agents | `.agents/skills/video-studio`, `.cursor/skills/…` |

Resolve it once at the start of a session and reuse it:

```bash
SKILL=$(ls -d ./.claude/skills/video-studio ~/.claude/skills/video-studio 2>/dev/null | head -1)
```

Never hardcode an absolute path into a project file — the project folder and the
skill folder are different things and the user may move either.

## Requirements

Run this before Phase 2 and tell the user plainly what is missing:

```bash
python3 $SKILL/scripts/fftool.py
```

| Need | Check | Fix |
|---|---|---|
| ffmpeg with libass | `fftool.py` reports `subtitles OK` | `brew install ffmpeg-full` (bottled, keg-only) |
| Python 3.9+ | `python3 -V` | preinstalled on macOS |
| Node 22+ | `node -v` | only needed for Phase 5 |
| Transcription | `$ELEVENLABS_API_KEY` | elevenlabs.io → API keys |
| B-roll (optional) | `$PEXELS_API_KEY`, `$PIXABAY_API_KEY` | free, no card |

Plain Homebrew `ffmpeg` v8+ **cannot burn captions** — it ships without libass,
so the `subtitles` filter does not exist. Phases 1-6 work fine without
`ffmpeg-full`; only Phase 7 caption burning needs it.

Scripts use only the Python standard library plus `ffmpeg` and `curl`. There is
nothing to `pip install`.

## Routing

Read `state.json` in the working directory (or the project folder the user names).

| Situation | Do this |
|---|---|
| No `state.json` | Run `bash $SKILL/scripts/init.sh <nombre>`, then Phase 0 |
| `state.json` exists, no args | Read `phase` field, resume that phase |
| User names a phase | Jump there, but warn if prerequisites are missing |
| User gives a bare video file, no project | Offer: full pipeline from Phase 0, or fast path (`2 → 3 → 4 → 7 → 8`) |

Load **only** the phase file you are running. Do not read all nine.

| # | Phase | File | Gate |
|---|---|---|---|
| 0 | Idea & outline | `phases/00-idea.md` | ✋ approve outline |
| 1 | Record | `phases/01-record.md` | ✋ user records |
| 2 | Transcribe | `phases/02-transcribe.md` | — |
| 3 | Edit plan | `phases/03-review.md` | ✋ approve `review.md` + `edl.json` |
| 4 | Assemble | `phases/04-assemble.md` | — |
| 5 | Motion graphics | `phases/05-graphics.md` | — |
| 6 | B-roll | `phases/06-broll.md` | — |
| 6b | Generative media | `phases/06b-generativo.md` | **opt-in only** |
| 7 | Polish | `phases/07-polish.md` | ✋ approve `check.md` |
| 8 | Final render | `phases/08-final.md` | — |

Phase 6b is **optional and costs money**. Never run it unless the user asks for
it by name. Motion graphics stay in HyperFrames (free, exact, unlimited); 6b is
for thumbnails, short covers, and shots that neither stock nor HTML can produce.

## Project layout

```
<project>/
├── state.json            phase pointer + config
├── edl.json              THE EDIT — source-time cuts and overlays
├── 00-outline.md         hook, beats, CTA, TikTok short plan
├── 01-shot-list.md       what to record, in order
├── 03-review.md          the edit proposal you approve
├── 07-check.md           what to verify before final render
├── raw/                  original recordings (never modified)
├── audio/                extracted audio for transcription
├── transcript/           raw.json, words.json, raw.srt
├── segments/             segment-01.md … per-segment edit plans
├── graphics/             HyperFrames projects + rendered overlays
├── broll/                downloaded stock clips
├── build/                rough.mp4, timemap.json, intermediates
├── captions/             final.ass
└── final/                the deliverable
```

## Tooling (verified available)

| Need | Tool | Cost |
|---|---|---|
| Cut, composite, caption, render | `ffmpeg` 8.1.2 | free |
| Transcription | ElevenLabs Scribe v2 | $0.22/hr (~4¢ per 10-min video) |
| Motion graphics | HyperFrames (HTML→MP4) | free |
| B-roll | Pexels + Pixabay APIs | free |

`ELEVENLABS_API_KEY` is required for Phase 2. `PEXELS_API_KEY` / `PIXABAY_API_KEY` are
optional — Phase 6 degrades to "shoot this yourself" suggestions without them.
Never print an API key into a file, a log, or the transcript.

## Scripts

Run with `python3 scripts/<name>.py --help`. All are dependency-free (stdlib + `ffmpeg` + `curl`).

| Script | Purpose |
|---|---|
| `init.sh` | Scaffold a project folder |
| `transcribe.py` | Video → ElevenLabs Scribe → `words.json` + `.srt` |
| `analyze.py` | `words.json` → dead space, fillers, stutters → `analysis.json` |
| `cut.py` | `edl.json` → `build/rough.mp4` + `build/timemap.json` |
| `captions.py` | `words.json` + `timemap.json` → word-by-word uppercase `.ass` |
| `overlay.py` | Composite graphics, b-roll and zooms onto the cut |
| `broll.py` | Search + download from Pexels/Pixabay |
| `genmedia.py` | **Optional, paid.** Generate images/video via kie.ai, fal.ai, wavespeed |
| `reframe.py` | 16:9 → 9:16 for TikTok/Shorts |
| `render.py` | Final encode, loudness normalize, validate |
