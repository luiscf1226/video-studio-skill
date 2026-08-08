#!/usr/bin/env python3
"""Splice a clip into a base video with a crossfade — insert new content, or
replace a bad span, without re-generating anything. Free, local, ffmpeg only.

This is the fix for the single most expensive mistake in AI video generation:
re-rolling an entire multi-shot take (which can cost $10-15+) because one 3-4
second section came out wrong. Generate a short, cheap standalone replacement
for JUST that section instead, and splice it in here.

Two shapes, same underlying operation (concat with a crossfade on each side):

  INSERT  (extends total duration) — add new content at a point:

      python3 splice_insert.py base.mp4 insert.mp4 --at 20.0 --out out.mp4

      base[0:20] --xfade--> insert --xfade--> base[20:end]

  REPLACE (a bad span becomes new content) — cut out [start, end), splice the
  insert in its place. If your insert's own duration minus the two crossfades
  equals (end - start), total duration is unchanged:

      python3 splice_insert.py base.mp4 fixed.mp4 --at 3.75 --until 4.0 \\
          --crossfade 0.6 --out out.mp4

      base[0:3.75] --xfade--> fixed --xfade--> base[4.0:end]

Both inputs must share resolution and framerate (this script does not
normalize them — see references/models.json / your generation script's output
settings; mismatched fps between two AI-generated clips is a common gotcha).

Duration math (why this works, so you don't have to re-derive it under
deadline): xfade(A, B, duration=d, offset=o) plays A up to `o`, crossfades for
`d` seconds, then continues B from ITS OWN local time `d` onward — meaning
B's local clock and the output clock are IDENTICAL for output-time >= offset
whenever offset equals the point B is "supposed" to start from. This script
sets offset = len(preceding segment) - crossfade automatically; you should
never need to compute it by hand.

  --at 20.0                 insertion/cut point, in seconds of BASE
  --until 24.0               (replace only) end of the span being cut, in
                              seconds of BASE — omit for pure insert
  --crossfade 0.4            seconds of crossfade on EACH side (def 0.4)
  --transition fade          any ffmpeg xfade transition name (fade, wipeleft,
                              dissolve, ...) — see `ffmpeg -h filter=xfade`
"""
import argparse
import pathlib
import subprocess
import sys


def ffprobe_duration(path):
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        sys.exit(f"ERROR: no pude leer la duracion de {path} (ffprobe)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="video base")
    ap.add_argument("insert", help="clip a insertar/reemplazar")
    ap.add_argument("--at", type=float, required=True, help="punto de corte en BASE (segundos)")
    ap.add_argument("--until", type=float, default=None,
                    help="fin del tramo a reemplazar en BASE (segundos). Omitir = insertar puro")
    ap.add_argument("--crossfade", type=float, default=0.4, help="segundos de crossfade por lado")
    ap.add_argument("--transition", default="fade", help="tipo de xfade (def: fade)")
    ap.add_argument("--insert-start", type=float, default=None,
                    help="recortar el clip a insertar: inicio en segundos (def: 0)")
    ap.add_argument("--insert-end", type=float, default=None,
                    help="recortar el clip a insertar: fin en segundos (def: duracion completa)")
    ap.add_argument("--out", required=True, help="archivo de salida")
    ap.add_argument("--preset", default="medium", help="x264 preset (def: medium)")
    ap.add_argument("--crf", type=int, default=18, help="x264 crf (def: 18)")
    ap.add_argument("--dry-run", action="store_true", help="solo mostrar el comando, no correrlo")
    args = ap.parse_args()

    base, insert = pathlib.Path(args.base), pathlib.Path(args.insert)
    for p in (base, insert):
        if not p.exists():
            sys.exit(f"ERROR: no existe {p}")

    base_dur = ffprobe_duration(base)
    insert_full_dur = ffprobe_duration(insert)
    ins_start = args.insert_start if args.insert_start is not None else 0.0
    ins_end = args.insert_end if args.insert_end is not None else insert_full_dur
    if ins_start < 0 or ins_end > insert_full_dur or ins_start >= ins_end:
        sys.exit(f"ERROR: recorte de insert invalido [{ins_start}, {ins_end}] "
                 f"(duracion del clip: {insert_full_dur:.2f}s)")
    insert_dur = ins_end - ins_start
    until = args.until if args.until is not None else args.at
    cf = args.crossfade

    if args.at < 0 or until > base_dur or args.at > until:
        sys.exit(f"ERROR: rango invalido --at {args.at} --until {until} "
                 f"(duracion de base: {base_dur:.2f}s)")
    if insert_dur <= 2 * cf:
        sys.exit(f"ERROR: el clip a insertar ({insert_dur:.2f}s) es mas corto que "
                 f"2x el crossfade ({2*cf:.2f}s). Baja --crossfade o usa un clip mas largo.")

    seg_a_dur = args.at
    tail_start = until  # where the surviving tail of `base` resumes

    # xfade(A, B, duration=d, offset=o) plays A to `o`, crossfades `d`s, then B
    # continues from ITS OWN local time `d` onward — so the stage's total
    # output length is simply offset + len(B). Chaining two stages is just
    # applying that twice; get this right and duration math never needs
    # trial and error again.
    offset1 = seg_a_dur - cf if seg_a_dur > 0 else 0.0
    len_after_1 = offset1 + insert_dur if seg_a_dur > 0 else insert_dur
    offset2 = len_after_1 - cf

    has_tail = tail_start < base_dur
    result_dur = (offset2 + (base_dur - tail_start)) if has_tail else len_after_1

    print(f"base           {base}  ({base_dur:.2f}s)")
    print(f"insert         {insert}  ({insert_dur:.2f}s)")
    print(f"modo           {'reemplazo' if args.until is not None else 'insercion'}")
    print(f"tramo cortado  [{args.at:.2f}, {until:.2f}]  ({until - args.at:.2f}s de base)")
    print(f"crossfade      {cf}s x2  ·  transicion: {args.transition}")
    print(f"duracion final ~{result_dur:.2f}s  (base era {base_dur:.2f}s)")

    filt = []
    if seg_a_dur > 0:
        filt.append(f"[0:v]trim=0:{seg_a_dur},setpts=PTS-STARTPTS,setsar=1[segA]")
        filt.append(f"[1:v]trim={ins_start}:{ins_end},setpts=PTS-STARTPTS,setsar=1[ins]")
        filt.append(f"[segA][ins]xfade=transition={args.transition}:duration={cf}:offset={offset1}[mid]")
        left_label = "mid"
    else:
        # cut point is at t=0: nothing precedes the insert, no first crossfade needed
        filt.append(f"[1:v]trim={ins_start}:{ins_end},setpts=PTS-STARTPTS,setsar=1[mid]")
        left_label = "mid"

    if has_tail:
        filt.append(f"[0:v]trim={tail_start}:{base_dur},setpts=PTS-STARTPTS,setsar=1[tail]")
        filt.append(f"[{left_label}][tail]xfade=transition={args.transition}:duration={cf}:offset={offset2}[outv]")
        out_label = "outv"
    else:
        out_label = left_label  # nothing survives after the cut; insert is the new ending

    filter_complex = ";\n".join(filt)

    cmd = ["ffmpeg", "-y", "-loglevel", "warning",
           "-i", str(base), "-i", str(insert),
           "-filter_complex", filter_complex,
           "-map", f"[{out_label}]",
           "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
           "-pix_fmt", "yuv420p",
           str(args.out)]

    print("\n" + " \\\n  ".join(cmd))
    if args.dry_run:
        return

    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"ERROR: ffmpeg fallo (codigo {r.returncode})")

    actual = ffprobe_duration(pathlib.Path(args.out))
    print(f"\nOK  {args.out}  ({actual:.2f}s)")


if __name__ == "__main__":
    main()
