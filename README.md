# video-studio

An agent skill that takes a video from idea to a finished, rendered MP4 — outline,
transcript, edit plan, cuts, motion graphics, b-roll, word-by-word captions, a 9:16
short, and the final render.

Built for [Claude Code](https://claude.com/claude-code) and any agent that reads
`SKILL.md`.

```bash
npx skills add luiscf1226/video-studio-skill
```

Then, in your agent: `/video-studio`

> **Deliverables are written in Spanish** — `review.md`, segment plans, captions
> and on-screen text. Scripts, JSON keys and filenames are English. To switch
> languages, edit the language rule near the top of `SKILL.md` and the word lists
> in `references/filler-words-es.md`.

## Why

Most "AI video editors" are a subscription that owns your footage. This is a
pipeline of small scripts you can read, running on ffmpeg locally. The only
recurring cost is transcription — about **4 cents per video**.

| Tool | Role | Cost |
|---|---|---|
| ffmpeg | cuts, compositing, captions, render | free |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | motion graphics from HTML | free |
| [Pexels](https://www.pexels.com/api/) + [Pixabay](https://pixabay.com/api/docs/) | b-roll | free |
| [ElevenLabs Scribe](https://elevenlabs.io/speech-to-text-api) | word-level transcript | $0.22/hr |

Swap Scribe for local `whisper-cpp` and the whole thing is free.

## The nine phases

Each phase reads and writes one project folder, and the pipeline resumes from
`state.json` — stop after any gate and come back days later.

| # | Phase | Output | Gate |
|---|---|---|---|
| 0 | Idea | outline, hook, TikTok short plan | ✋ you approve |
| 1 | Record | shot list grouped by setup | ✋ you record |
| 2 | Transcribe | word-level timestamps | |
| 3 | Edit plan | `review.md`, per-segment plans, `edl.json` | ✋ you approve |
| 4 | Assemble | rough cut | |
| 5 | Graphics | rendered motion graphics | |
| 6 | B-roll | downloaded clips, composited | |
| 6b | *Generative media* | *AI images/video for an existing edit — **optional, costs money*** | *opt-in only* |
| 6c | *Fully-generated video* | *no real footage at all, built from a prompt — **optional, costs money*** | *opt-in only* |
| 7 | Polish | captions, color, music, 9:16 short | ✋ you approve |
| 8 | Final | render, loudness, validate | |

Already have footage? Run `2 → 3 → 4 → 7 → 8`.

### Phase 6b — generative media (optional)

Everything above is free except transcription. Phase 6b is the one paid step,
and it never runs unless you ask for it by name.

It exists for what neither free stock nor HTML can produce — **thumbnails, short
covers, and photographic shots too specific for stock**. It routes to the
cheapest pay-per-use aggregator that has the model (kie.ai → fal.ai →
wavespeed), so there is no subscription: you pay per image.

```bash
python3 skills/video-studio/scripts/genmedia.py --list

python3 skills/video-studio/scripts/genmedia.py \
  "YouTube thumbnail: laptop showing a dark 3D presentation, amber glow" \
  --model nano-banana-pro --n 3 --budget 0.30
```

Four guards keep it from draining an account:

- **`--budget` is checked before every call**, not just at the start. Ask for 20
  images with a $0.30 cap and it aborts before spending a cent.
- **Explicit confirmation.** It prints the estimated cost and waits.
- **Immediate download.** On kie.ai the output URLs expire after 24 hours.
- **Full log.** Every prompt, model, provider, cost and path lands in
  `generations.jsonl`, plus an HTML gallery — because you cannot judge an image
  from a terminal.

Prices live in `references/models.json` and are flagged `verified: true/false`;
the script warns before spending on an unverified price. Adding a model is a
JSON edit, not a code change.

**Motion graphics deliberately stay in HyperFrames.** It is free, unlimited, and
gives exact text, exact timing and exact brand colours — an animated counter
from 0 to 10 in your own typeface is not something an image model can produce.
Phase 6b is for photographic work only.

### Phase 6c — fully-generated video (optional, standalone)

For when there's no `raw/` at all — a brand or sizzle video built entirely
from a prompt, no real footage. **Its scripts don't need the rest of this
skill.** `genmedia.py`, `splice_insert.py`, `upscale.py` and
`labels_overlay.py` are plain CLI tools — no `state.json`, no project folder,
no other phase has to run first. Generate a video from scratch, fix or extend
a clip you already have (from anywhere, not just this skill), upscale one
file, or add labels — one script at a time, in any order. Full workflow in
[`phases/06c-video-generado.md`](skills/video-studio/phases/06c-video-generado.md);
headline numbers, so you don't have to open it just to pick a model:

| Need | Model | Cost | Notes |
|---|---|---|---|
| Long continuous take, narrates several scenes, no cuts | `seedance-2.5` | $0.473/s @720p, $0.2205/s @480p | No native 1080p — upscale after |
| Single short scene, native 1080p, no upscale needed | `ltx-fast` | $0.04/s @1080p | Often cheaper *in total* than 720p-gen + upscale, if the style fits |
| Animate an existing still image | `kling` | ~$0.07/s | Most reliable image-to-video |
| Upscale anything to 1080p after generating it cheap | `upscale.py` (Topaz) | $0.01–0.02/s of source | Usually cheaper than generating natively at high res |
| Music / SFX | the `media-use` skill, if installed | **$0** | Free HeyGen catalog — check this before any paid audio model |

Full prices (with verified/unverified flags) in `references/models.json`,
same file phase 6b reads.

**The expensive mistake this phase exists to prevent:** re-generating an
entire 20-30s continuous take (often $10-15+) to fix one 3-4 second section
that came out wrong. Generate a short, cheap replacement for just that span
instead (`genmedia.py --seconds 4`, often under $2) and crossfade-splice it in
with `splice_insert.py` — free, local, no re-generation. Same script also adds
a *new* scene without touching what already works, and `labels_overlay.py`
adds timed on-screen text (era cards, dates, section titles) even on a plain
Homebrew `ffmpeg` that lacks `drawtext`.

### Quickstart — generating a video from scratch, no recording involved

This walks through phase 6c end to end: no `state.json`, no project folder,
no other phase. Just the four scripts, called directly, on plain files.

**1. How it fits together.** The skill is just files Claude reads: `SKILL.md`
tells it which phase file to open for a given request; the phase file
(`phases/06c-video-generado.md`) is the how-to in plain language;
`references/models.json` is the price catalog; `scripts/*.py` are the actual
tools that do the work. Nothing here is a service or a server — every script
takes file paths in and writes file paths out.

**2. How the scripts use Python.** All four are dependency-free — standard
library only (`argparse`, `json`, `subprocess`), no `pip install` anything.
The actual work is delegated to `curl` (talking to fal.ai) and `ffmpeg`
(everything video/audio). That's why they run on any machine with Python 3 +
ffmpeg, with nothing extra to set up.

**3. The example flow.**

```bash
export FAL_KEY='...'   # from fal.ai/dashboard/keys

# a) generate a base clip. --budget is a hard cap, and it asks for
#    confirmation before spending anything.
python3 skills/video-studio/scripts/genmedia.py \
  "cinematic shot of hands warming over a campfire, dark cave at night" \
  --model seedance-2.5 --seconds 8 --budget 5.00 --outdir generated

# b) not happy with 3-4 seconds of it? don't re-run (a) and pay again for the
#    whole clip -- generate a short, cheap replacement for just that span...
python3 skills/video-studio/scripts/genmedia.py \
  "same shot, but no face visible, hands and fire only" \
  --model seedance-2.5 --seconds 4 --budget 2.00 --outdir generated

# ...and splice it in with a crossfade. free, local, no API call.
python3 skills/video-studio/scripts/splice_insert.py \
  generated/20260101-000000-seedance-2.5-1.mp4 \
  generated/20260101-000100-seedance-2.5-1.mp4 \
  --at 0 --until 3.75 --crossfade 0.6 \
  --out generated/fixed.mp4

# c) add on-screen text -- works even if this machine's ffmpeg lacks
#    drawtext (falls back automatically, see labels_overlay.py --check)
cat > cues.json <<'JSON'
[{"text": "~10,000 BCE", "start": 0, "end": 4}]
JSON
python3 skills/video-studio/scripts/labels_overlay.py \
  generated/fixed.mp4 cues.json --out generated/labeled.mp4

# d) upscale at the end, not the start -- cheaper than generating high-res
#    natively (see the cost table above)
python3 skills/video-studio/scripts/upscale.py \
  generated/labeled.mp4 --factor 1.5 --model Proteus \
  --out final/video_1080p.mp4 --budget 1.00
```

Every generation call logs its prompt, model, provider, cost and output path
to `generated/generations.jsonl` — open `generated/index.html` any time to
see everything you've made so far, with running total spent.

**In an agent session** (Claude Code or similar), you don't type these
commands yourself — you just describe what you want ("make me a 20s brand
video about X", "that middle section looks wrong, fix just that part", "add a
year label in the corner") and the agent reads `06c-video-generado.md`, picks
the right script and flags, and shows you the cost estimate before spending
anything.

## How the edit is represented

`edl.json` holds the whole edit, with **all times in seconds of the original
recording**:

```json
{
  "source": "raw/main.mp4",
  "segments": [{
    "id": "S01",
    "keep": [{ "start": 412.5, "end": 416.0 }, { "start": 1.2, "end": 24.8 }],
    "overlays": [
      { "type": "zoom", "start": 18.0, "end": 22.0, "scale": 1.3, "y": 0.35 },
      { "type": "broll", "asset": "broll/x.mp4", "start": 12.0, "end": 16.0 }
    ]
  }]
}
```

`cut.py` emits `build/timemap.json`, which translates original time to final time.
That indirection is the point: change your mind about a cut, re-run the cut, and
your graphics and captions still land in the right place — nothing to re-author.

The first `keep` block above starts at 412s: that's the teaser, lifted from the
end of the recording and montaged onto the front.

## Filler-word handling

Spanish filler words are mostly *real words*, so they are split into two tiers:

- **tier 1** — non-lexical noise (`eh`, `mmm`, `uh`) and stutters. Cut automatically.
- **tier 2** — real words used as crutches (`bueno`, `pues`, `o sea`, `este`).
  Flagged for a human decision, **never** cut automatically.

Deleting every `bueno` leaves audio that sounds chopped and robotic. See
[`references/filler-words-es.md`](skills/video-studio/references/filler-words-es.md).

## Requirements

```bash
python3 skills/video-studio/scripts/fftool.py   # capability report
```

- **ffmpeg with libass.** On macOS, Homebrew's `ffmpeg` v8+ is a slim build with
  no libass, so the `subtitles` filter does not exist and captions cannot be
  burned. Fix with `brew install ffmpeg-full` (bottled, keg-only — it does not
  replace your existing ffmpeg; the scripts detect it automatically).
- **Python 3.9+.** Standard library only — nothing to `pip install`.
- **Node 22+** for Phase 5 only.
- `ELEVENLABS_API_KEY` for Phase 2. `PEXELS_API_KEY` / `PIXABAY_API_KEY` optional.

## What the scripts do

Installed skills run with full agent permissions, so here is the honest list.
Every script is standard-library Python that shells out to `ffmpeg`/`ffprobe`/`curl`:

| Script | Behavior |
|---|---|
| `init.sh` | creates a project folder; refuses to overwrite |
| `transcribe.py` | uploads extracted audio to ElevenLabs; reads `ELEVENLABS_API_KEY` |
| `analyze.py` | reads the transcript; writes JSON. No network |
| `cut.py` | reads source video, writes to `build/`. No network |
| `captions.py` | writes `.ass`, optionally burns it. No network |
| `overlay.py` | composites local assets. No network |
| `broll.py` | queries Pexels/Pixabay and downloads to `broll/` |
| `genmedia.py` | **optional, paid** — posts prompts to kie.ai / fal.ai / wavespeed; reads `KIE_API_KEY`, `FAL_KEY`, `WAVESPEED_API_KEY`; enforces a spend cap |
| `upscale.py` | **optional, paid** — upscales a local video via Topaz on fal.ai; reads `FAL_KEY`; enforces a spend cap |
| `splice_insert.py` | crossfade-splices a clip into a base video (insert or replace-a-bad-span). Free, local, no network |
| `labels_overlay.py` | timed on-screen text labels; `drawtext` if available, PNG-overlay fallback otherwise. No network |
| `reframe.py`, `render.py` | local ffmpeg only |
| `fftool.py` | capability detection; no writes |

Nothing writes outside the project folder, nothing deletes `raw/`, and no key is
ever written to a file or logged.

## License

MIT
