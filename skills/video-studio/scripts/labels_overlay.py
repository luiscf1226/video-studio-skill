#!/usr/bin/env python3
"""Timed on-screen text labels (corner captions, lower-thirds, era/date cards) — free,
local. Tries ffmpeg's `drawtext` first; falls back to a PNG-overlay technique if
this machine's ffmpeg was built without freetype (common with plain Homebrew
`ffmpeg`, same gap documented in SKILL.md for caption burning).

    python3 labels_overlay.py video.mp4 cues.json --out labeled.mp4

cues.json is a list of cues:

    [
      {"text": "FUEGO  ·  ~10,000 A.C.", "start": 0,   "end": 7.0},
      {"text": "ROMA  ·  ~2,000 A.C.",   "start": 7.6, "end": 13.4}
    ]

--position: one of top-right (default), top-left, bottom-right, bottom-left.

## Which path you get, and why it matters

**drawtext (default, tries first):** one filter pass, animated fade in/out,
cheap. Needs `ffmpeg -filters | grep drawtext` to list it — if Homebrew's
`ffmpeg` was built without libfreetype (check with `--check`), this fails with
`No such filter: 'drawtext'`. Fix: `brew install ffmpeg-full` (bottled,
keg-only, does not replace your existing ffmpeg — same fix as burning
captions, see SKILL.md Requirements).

**PNG fallback (--force-png, or automatic if drawtext is missing):** renders
each label with Pillow onto a full-frame transparent canvas, concatenates
those frames (+ blank filler) into ONE label track, and does a SINGLE overlay
pass. Needs `pip install pillow` (the one place this skill needs something
outside stdlib — everywhere else stays dependency-free on purpose).

**Do NOT chain N separate `overlay+fade` filters for N labels** — that was
tried first and took 20+ minutes on a 49s 1080p clip that the single-pass
version below rendered in under a minute. Sequential per-frame alpha
compositing across many filter nodes is the trap; pre-composite once, overlay
once. If you're tempted to "just add one more overlay node" for a new label,
add it to the cues list instead — the concat approach scales to any number of
labels in roughly the same render time.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

POSITIONS = {
    "top-right": ("W-w-40", "40", "1920-{w}-40", "40"),
    "top-left": ("40", "40", "40", "40"),
    "bottom-right": ("W-w-40", "H-h-40", "1920-{w}-40", "1080-{h}-40"),
    "bottom-left": ("40", "H-h-40", "40", "1080-{h}-40"),
}


def ffprobe_duration(path):
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        sys.exit(f"ERROR: no pude leer la duracion de {path} (ffprobe)")


def ffprobe_size(path):
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        w, h = p.stdout.strip().split(",")
        return int(w), int(h)
    except ValueError:
        sys.exit(f"ERROR: no pude leer el tamano de {path} (ffprobe)")


def has_drawtext():
    p = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
    return " drawtext " in p.stdout or p.stdout.find("drawtext") != -1


def find_font():
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",   # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if pathlib.Path(candidate).exists():
            return candidate
    return None


# ------------------------------------------------------------- drawtext path
def run_drawtext(video, cues, position, out, fontsize, fade):
    font = find_font()
    if not font:
        sys.exit("ERROR: no encontre una fuente bold del sistema. Pasa --font "
                 "o usa --force-png (necesita Pillow).")
    x_expr, y_expr, _, _ = POSITIONS[position]

    parts = []
    for i, cue in enumerate(cues):
        text = cue["text"].replace("\\", "\\\\").replace("'", "’").replace(":", "\\:")
        s, e = float(cue["start"]), float(cue["end"])
        alpha = (
            f"if(lt(t\\,{s})\\,0\\,"
            f"if(lt(t\\,{s+fade})\\,(t-{s})/{fade}\\,"
            f"if(lt(t\\,{e-fade})\\,1\\,"
            f"if(lt(t\\,{e})\\,({e}-t)/{fade}\\,0))))"
        )
        parts.append(
            f"drawtext=fontfile='{font}':text='{text}':fontsize={fontsize}:"
            f"fontcolor=white:box=1:boxcolor=black@0.35:boxborderw=12:"
            f"x={x_expr}:y={y_expr}:alpha='{alpha}':enable='between(t,{s},{e})'"
        )
    vf = ",".join(parts)

    cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-i", str(video),
           "-vf", vf, "-map", "0:v", "-map", "0:a?",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"ERROR: ffmpeg (drawtext) fallo (codigo {r.returncode})")


# ------------------------------------------------------------------ png path
def run_png(video, cues, position, out, fontsize):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        sys.exit("ERROR: --force-png necesita Pillow. pip install pillow "
                 "(o instala ffmpeg-full para usar drawtext en vez de esto).")

    font_path = find_font()
    if not font_path:
        sys.exit("ERROR: no encontre una fuente bold del sistema. Pasa --font.")
    font = ImageFont.truetype(font_path, fontsize)

    w, h = ffprobe_size(video)
    dur = ffprobe_duration(video)
    tmpdir = pathlib.Path(out).parent / (pathlib.Path(out).stem + "_labels_tmp")
    tmpdir.mkdir(parents=True, exist_ok=True)

    def render_label(text):
        dummy = Image.new("RGBA", (10, 10))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 22, 14
        img = Image.new("RGBA", (tw + pad_x * 2, th + pad_y * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=10,
                               fill=(0, 0, 0, 110))
        draw.text((pad_x - bbox[0], pad_y - bbox[1]), text, font=font, fill=(255, 255, 255, 255))
        return img

    margin = 40
    blank = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    blank_path = tmpdir / "_blank.png"
    blank.save(blank_path)

    cues = sorted(cues, key=lambda c: c["start"])
    segments = []  # (path, duration)
    cursor = 0.0
    for cue in cues:
        s, e = float(cue["start"]), float(cue["end"])
        if s > cursor:
            segments.append((blank_path, s - cursor))
        label = render_label(cue["text"])
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if "right" in position:
            x = w - label.width - margin
        else:
            x = margin
        y = margin if "top" in position else h - label.height - margin
        canvas.paste(label, (x, y), label)
        label_path = tmpdir / f"label_{len(segments)}.png"
        canvas.save(label_path)
        segments.append((label_path, e - s))
        cursor = e
    if cursor < dur:
        segments.append((blank_path, dur - cursor))

    inputs, filt = [], []
    for i, (path, seg_dur) in enumerate(segments):
        inputs += ["-loop", "1", "-framerate", "24", "-t", f"{seg_dur:.3f}", "-i", str(path)]
        filt.append(f"[{i+1}:v]setpts=PTS-STARTPTS[s{i}]")
    concat_in = "".join(f"[s{i}]" for i in range(len(segments)))
    filt.append(f"{concat_in}concat=n={len(segments)}:v=1:a=0[ovl]")
    filt.append("[0:v][ovl]overlay=0:0:format=auto[outv]")

    cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-i", str(video), *inputs,
           "-filter_complex", ";\n".join(filt),
           "-map", "[outv]", "-map", "0:a?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
    r = subprocess.run(cmd)
    shutil.rmtree(tmpdir, ignore_errors=True)
    if r.returncode != 0:
        sys.exit(f"ERROR: ffmpeg (concat+overlay) fallo (codigo {r.returncode})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("cues", help="archivo JSON: [{text, start, end}, ...]")
    ap.add_argument("--out", required=True)
    ap.add_argument("--position", default="top-right", choices=list(POSITIONS))
    ap.add_argument("--fontsize", type=int, default=34)
    ap.add_argument("--fade", type=float, default=0.3, help="fundido in/out en segundos (solo drawtext)")
    ap.add_argument("--font", default=None, help="ruta a un .ttf, si no quieres el default del sistema")
    ap.add_argument("--force-png", action="store_true",
                    help="usar el camino PNG aunque drawtext este disponible")
    ap.add_argument("--check", action="store_true", help="solo decir que camino se usaria, y salir")
    args = ap.parse_args()

    global find_font
    if args.font:
        _font_override = args.font
        find_font = lambda: _font_override  # noqa: E731

    drawtext_ok = has_drawtext() and not args.force_png

    if args.check:
        print(f"drawtext disponible: {has_drawtext()}")
        print(f"camino a usar:       {'drawtext' if drawtext_ok else 'PNG (concat + un solo overlay)'}")
        return

    video = pathlib.Path(args.video)
    if not video.exists():
        sys.exit(f"ERROR: no existe {video}")
    cues = json.loads(pathlib.Path(args.cues).read_text(encoding="utf-8"))
    if not cues:
        sys.exit("ERROR: cues.json esta vacio")

    if drawtext_ok:
        print("Usando drawtext (un solo pase, con fundido animado)...")
        run_drawtext(video, cues, args.position, args.out, args.fontsize, args.fade)
    else:
        if not has_drawtext():
            print("drawtext no esta disponible en este ffmpeg (falta freetype) -> "
                 "usando el camino PNG. Para el camino rapido con fundido animado: "
                 "brew install ffmpeg-full")
        print("Componiendo etiquetas como PNG + un solo overlay (sin fundido)...")
        run_png(video, cues, args.position, args.out, args.fontsize)

    print(f"\nOK  {args.out}")


if __name__ == "__main__":
    main()
