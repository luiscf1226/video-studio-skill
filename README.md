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
| 7 | Polish | captions, color, music, 9:16 short | ✋ you approve |
| 8 | Final | render, loudness, validate | |

Already have footage? Run `2 → 3 → 4 → 7 → 8`.

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
| `reframe.py`, `render.py` | local ffmpeg only |
| `fftool.py` | capability detection; no writes |

Nothing writes outside the project folder, nothing deletes `raw/`, and no key is
ever written to a file or logged.

## License

MIT
