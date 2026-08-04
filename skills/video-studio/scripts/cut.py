#!/usr/bin/env python3
"""Execute edl.json — render the rough cut and the source→output time map.

Every keep-range in every segment becomes one re-encoded part; the parts are then
concatenated with stream copy, so the footage is encoded exactly once. Each part
gets a 25 ms audio fade at both ends, which is what stops filler-word removal from
producing audible clicks.

Writes:
  build/rough.mp4      the assembled cut
  build/timemap.json   [{src_start, src_end, out_start, out_end, segment}]

Everything downstream (captions, overlays) uses timemap.json to translate the
source timestamps you authored in edl.json into output timestamps.

  python3 cut.py edl.json --outdir build
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

MIN_PART = 0.10   # discard keep-ranges shorter than this
FADE = 0.025      # audio de-click fade, seconds


def ffmpeg(args_list):
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args_list],
                       capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ERROR ffmpeg:\n{p.stderr.strip()}")


def load_ranges(edl):
    """Flatten segments → ordered list of (segment_id, start, end)."""
    ranges = []
    for seg in edl.get("segments", []):
        sid = seg.get("id", "S??")
        for k in seg.get("keep", []):
            start, end = float(k["start"]), float(k["end"])
            if end - start < MIN_PART:
                print(f"  aviso: {sid} descarta toma de {end-start:.2f}s (muy corta)")
                continue
            ranges.append((sid, start, end))
    return ranges


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl", nargs="?", default="edl.json")
    ap.add_argument("--outdir", default="build")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--pad-mode", choices=["black", "blur"], default="black",
                    help="con que rellenar cuando la fuente no es 16:9. "
                         "'blur' usa una copia desenfocada del propio plano en "
                         "vez de barras negras (def black)")
    ap.add_argument("--dry-run", action="store_true",
                    help="mostrar el plan sin renderizar")
    args = ap.parse_args()

    edl = json.loads(pathlib.Path(args.edl).read_text(encoding="utf-8"))
    source = pathlib.Path(edl["source"])
    if not source.exists():
        sys.exit(f"ERROR: no existe el video fuente {source}")

    fps = edl.get("fps", 30)
    out = edl.get("output", {})
    width, height = out.get("width", 1920), out.get("height", 1080)

    ranges = load_ranges(edl)
    if not ranges:
        sys.exit("ERROR: edl.json no tiene ninguna toma que conservar")

    # Build the time map before touching ffmpeg — it is pure arithmetic.
    timemap, cursor = [], 0.0
    for sid, start, end in ranges:
        dur = end - start
        timemap.append({
            "segment": sid,
            "src_start": round(start, 3), "src_end": round(end, 3),
            "out_start": round(cursor, 3), "out_end": round(cursor + dur, 3),
        })
        cursor += dur

    print(f"Fuente     {source}")
    print(f"Tomas      {len(ranges)}")
    print(f"Salida     {cursor/60:.2f} min · {width}x{height} @ {fps}fps")

    if args.dry_run:
        for t in timemap:
            print(f"  {t['segment']}  {t['src_start']:8.2f}→{t['src_end']:8.2f}   "
                  f"out {t['out_start']:8.2f}→{t['out_end']:8.2f}")
        return

    outdir = pathlib.Path(args.outdir)
    parts_dir = outdir / "parts"
    if parts_dir.exists():
        shutil.rmtree(parts_dir)
    parts_dir.mkdir(parents=True)

    part_files = []
    for i, (sid, start, end) in enumerate(ranges):
        dur = end - start
        part = parts_dir / f"p{i:04d}.mp4"
        fade_out = max(0.0, dur - FADE)
        if args.pad_mode == "blur":
            # Relleno con una copia desenfocada del propio plano. Para material
            # que no es 16:9, esto se ve intencional; las barras negras se ven
            # como un error de encuadre.
            vf = (f"split=2[bg][fg];"
                  f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
                  f"crop={width}:{height},boxblur=luma_radius=42:luma_power=2,"
                  f"eq=brightness=-0.13[bgb];"
                  f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fgs];"
                  f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps}")
        else:
            vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                  f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}")

        ffmpeg([
            "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{dur:.3f}",
            "-vf", vf,
            "-af", f"afade=t=in:st=0:d={FADE},afade=t=out:st={fade_out:.3f}:d={FADE}",
            "-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-video_track_timescale", "90000",
            str(part),
        ])
        part_files.append(part)
        print(f"\r  parte {i+1}/{len(ranges)} ({sid})", end="", flush=True)
    print()

    listing = parts_dir / "concat.txt"
    listing.write_text(
        "".join(f"file '{p.name}'\n" for p in part_files), encoding="utf-8")

    rough = outdir / "rough.mp4"
    print("  concatenando ...")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", "-movflags", "+faststart", str(rough)])

    (outdir / "timemap.json").write_text(
        json.dumps(timemap, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nOK  {rough}  ({rough.stat().st_size/1e6:.1f} MB)")
    print(f"    {outdir}/timemap.json")


if __name__ == "__main__":
    main()
