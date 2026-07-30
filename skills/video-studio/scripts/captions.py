#!/usr/bin/env python3
"""Word-by-word animated captions (.ass) from a word-level transcript.

Reads words.json plus build/timemap.json, translates every word from source time
into output time, drops words that landed inside a cut, and writes a styled ASS
subtitle file. Optionally burns it into a video.

Styles
  word    one word at a time, huge and centred          (default)
  group   3-5 words visible, active word highlighted    (better retention)

  python3 captions.py transcript/words.json --timemap build/timemap.json \\
      --out captions/final.ass --style group --burn build/rough.mp4 \\
      --burn-out build/captioned.mp4
"""
import argparse
import json
import pathlib
import sys

import fftool

PRESETS = {
    # name: (font, size, primary, highlight, outline_px, margin_v)
    "tiktok":  ("Arial Black", 96, "&H00FFFFFF", "&H0000E5FF", 6, 180),
    "clean":   ("Avenir Next", 78, "&H00FFFFFF", "&H0000D7FF", 4, 150),
    "impact":  ("Impact", 110, "&H00FFFFFF", "&H004CFF00", 8, 200),
}


def ass_time(seconds):
    seconds = max(0.0, seconds)
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def load_timemap(path):
    if not path:
        return None
    p = pathlib.Path(path)
    if not p.exists():
        sys.exit(f"ERROR: no existe {p} — corre cut.py primero, o usa --no-timemap")
    return json.loads(p.read_text(encoding="utf-8"))


def remap(words, timemap, keep_ratio=0.5):
    """Source time → output time.

    A word is matched to the kept range it OVERLAPS MOST, not the one its start
    happens to land in — otherwise trimming 20 ms off a word's head would delete
    the whole caption. A word is dropped only when less than `keep_ratio` of its
    duration actually survived the cut.
    """
    if timemap is None:
        return list(words)

    out, dropped = [], 0
    for w in words:
        span = max(w["end"] - w["start"], 1e-6)
        best, best_overlap = None, 0.0
        total_kept = 0.0
        for seg in timemap:
            overlap = min(w["end"], seg["src_end"]) - max(w["start"], seg["src_start"])
            if overlap <= 0:
                continue
            total_kept += overlap
            if overlap > best_overlap:
                best, best_overlap = seg, overlap

        if best is None or total_kept / span < keep_ratio:
            dropped += 1
            continue

        offset = best["out_start"] - best["src_start"]
        start = max(w["start"], best["src_start"]) + offset
        end = min(w["end"], best["src_end"]) + offset
        if end - start < 0.08:          # survived, but too brief to read
            end = start + 0.08
        out.append({**w, "start": round(start, 3), "end": round(end, 3)})

    if dropped:
        print(f"  {dropped} palabras cayeron dentro de un corte (correcto)")
    return out


def group_words(words, max_words, max_gap):
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def header(width, height, font, size, primary, outline_px, margin_v):
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{primary},&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,{outline_px},2,2,120,120,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def esc(text):
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def build_word_style(words, upper, pop):
    """One word on screen at a time."""
    lines = []
    for w in words:
        text = esc(w["text"])
        if upper:
            text = text.upper()
        fx = r"{\fscx88\fscy88\t(0,70,\fscx100\fscy100)}" if pop else ""
        lines.append(f"Dialogue: 0,{ass_time(w['start'])},{ass_time(w['end'])},"
                     f"Cap,,0,0,0,,{fx}{text}")
    return lines


def build_group_style(words, upper, pop, highlight, max_words, max_gap):
    """Whole phrase visible, active word tinted — the TikTok/Reels look."""
    lines = []
    for group in group_words(words, max_words, max_gap):
        for i, active in enumerate(group):
            parts = []
            for j, w in enumerate(group):
                text = esc(w["text"])
                if upper:
                    text = text.upper()
                parts.append(f"{{\\c{highlight}}}{text}{{\\c&H00FFFFFF&}}"
                             if i == j else text)
            fx = r"{\fscx96\fscy96\t(0,60,\fscx100\fscy100)}" if pop and i == 0 else ""
            end = active["end"] if i < len(group) - 1 else group[-1]["end"] + 0.12
            lines.append(f"Dialogue: 0,{ass_time(active['start'])},{ass_time(end)},"
                         f"Cap,,0,0,0,,{fx}{' '.join(parts)}")
    return lines


def burn(video, ass_path, dest, ffmpeg_bin):
    fftool.require_filter("subtitles", ffmpeg_bin)
    # libass resolves relative paths oddly inside filtergraphs; feed it an
    # absolute path with the colon escaped.
    safe = str(pathlib.Path(ass_path).resolve()).replace("\\", "/").replace(":", r"\:")
    fftool.run([
        "-i", str(video),
        "-vf", f"subtitles='{safe}'",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "copy", str(dest),
    ], ffmpeg_bin)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words")
    ap.add_argument("--timemap", default="build/timemap.json")
    ap.add_argument("--no-timemap", action="store_true",
                    help="subtitular el video original sin cortes")
    ap.add_argument("--out", default="captions/final.ass")
    ap.add_argument("--style", choices=["word", "group"], default="word")
    ap.add_argument("--preset", choices=list(PRESETS), default="tiktok")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--max-words", type=int, default=4)
    ap.add_argument("--max-gap", type=float, default=0.7)
    ap.add_argument("--no-upper", action="store_true", help="no forzar MAYUSCULAS")
    ap.add_argument("--no-pop", action="store_true", help="sin animacion de escala")
    ap.add_argument("--burn", metavar="VIDEO", help="quemar los subtitulos en este video")
    ap.add_argument("--burn-out", default="build/captioned.mp4")
    args = ap.parse_args()

    words = json.loads(pathlib.Path(args.words).read_text(encoding="utf-8"))
    timemap = None if args.no_timemap else load_timemap(args.timemap)
    words = remap(words, timemap)
    if not words:
        sys.exit("ERROR: no quedaron palabras que subtitular")

    font, size, primary, highlight, outline_px, margin_v = PRESETS[args.preset]
    upper, pop = not args.no_upper, not args.no_pop

    if args.style == "word":
        events = build_word_style(words, upper, pop)
    else:
        events = build_group_style(words, upper, pop, highlight,
                                   args.max_words, args.max_gap)

    dest = pathlib.Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        header(args.width, args.height, font, size, primary, outline_px, margin_v)
        + "\n".join(events) + "\n", encoding="utf-8")

    print(f"OK  {len(events)} eventos · estilo '{args.style}' · preset '{args.preset}'")
    print(f"    fuente {font} {size}px")
    print(f"    -> {dest}")

    if args.burn:
        ffmpeg_bin = fftool.find_bin()
        print(f"\nQuemando subtitulos con {ffmpeg_bin} ...")
        burn(args.burn, dest, args.burn_out, ffmpeg_bin)
        print(f"OK  -> {args.burn_out}")
    elif not fftool.has_filter("subtitles"):
        print(f"\nAviso: el .ass quedo listo, pero este ffmpeg no puede quemarlo.\n"
              f"{fftool.INSTALL_HINT}")


if __name__ == "__main__":
    main()
