#!/usr/bin/env python3
"""Composite motion graphics, b-roll and punch-in zooms onto the rough cut.

Reads the `overlays` array of every segment in edl.json. Times are authored in
SOURCE seconds and translated to output time through build/timemap.json, so the
plan you approved in Phase 3 stays valid no matter how the cut changed.

Overlay types
  graphic  an asset rendered by HyperFrames (mp4 / webm with alpha / png)
  broll    stock footage that covers the speaker; original audio is preserved
  zoom     punch-in on the main footage (scale up, centre-crop back)

  python3 overlay.py edl.json --video build/rough.mp4 --out build/composited.mp4
"""
import argparse
import json
import pathlib
import sys

import fftool

POSITIONS = {
    "full":         ("0", "0"),
    "center":       ("(W-w)/2", "(H-h)/2"),
    "top-left":     ("60", "60"),
    "top-right":    ("W-w-60", "60"),
    "bottom-left":  ("60", "H-h-60"),
    "bottom-right": ("W-w-60", "H-h-60"),
    "lower-third":  ("(W-w)/2", "H-h-140"),
}


def map_range(start, end, timemap):
    """Source range → output range, clamped to whatever survived the cut.

    An overlay is dropped only when its ENTIRE range was removed. If just one
    endpoint fell inside a cut, it is snapped to the nearest surviving frame —
    losing a whole lower-third because its tail landed in a trimmed pause would
    be far worse than shortening it by a few frames.
    """
    if timemap is None:
        return start, end

    touched = [s for s in timemap
               if min(end, s["src_end"]) - max(start, s["src_start"]) > 0]
    if not touched:
        return None, None

    first, last = touched[0], touched[-1]
    out_start = first["out_start"] + (max(start, first["src_start"]) - first["src_start"])
    out_end = last["out_start"] + (min(end, last["src_end"]) - last["src_start"])
    return out_start, out_end


def collect(edl, timemap):
    """Flatten and time-translate every overlay, skipping ones fully cut."""
    items, skipped = [], []
    for seg in edl.get("segments", []):
        for ov in seg.get("overlays", []):
            src_start, src_end = float(ov["start"]), float(ov["end"])
            start, end = map_range(src_start, src_end, timemap)
            if start is None or end - start < 0.05:
                skipped.append(f"{seg.get('id','S??')} {ov.get('type')} "
                               f"@{src_start}s")
                continue
            if timemap and (end - start) < (src_end - src_start) - 0.05:
                print(f"  ajustado: {seg.get('id','S??')} {ov.get('type')} "
                      f"@{src_start}s dura {end-start:.2f}s en vez de "
                      f"{src_end-src_start:.2f}s (parte cayo en un corte)")
            items.append({**ov, "out_start": round(start, 3),
                          "out_end": round(end, 3), "segment": seg.get("id", "S??")})
    return sorted(items, key=lambda x: x["out_start"]), skipped


def build_graph(items, width, height, fps):
    """Return (filtergraph, extra_inputs, final_label).

    `extra_inputs` is a list of full ffmpeg input argument lists, because a still
    image needs `-loop 1 -framerate N -t D` supplied as INPUT options — a single
    PNG decodes to exactly one frame, and no amount of filtering after the fact
    can stretch one frame across a duration.
    """
    parts, inputs = [], []
    label = "base"
    parts.append(f"[0:v]scale={width}:{height},setsar=1[{label}]")

    for i, ov in enumerate(items):
        kind = ov.get("type")
        start, end = ov["out_start"], ov["out_end"]
        dur = end - start
        nxt = f"v{i}"

        if kind == "zoom":
            scale = float(ov.get("scale", 1.2))
            zw, zh = int(width * scale) // 2 * 2, int(height * scale) // 2 * 2
            # Focus point, 0..1 across the frame; 0.5,0.5 is dead centre.
            fx, fy = float(ov.get("x", 0.5)), float(ov.get("y", 0.5))
            ox = int((zw - width) * fx)
            oy = int((zh - height) * fy)
            parts.append(
                f"[{label}]split[{label}a][{label}b];"
                f"[{label}b]scale={zw}:{zh},crop={width}:{height}:{ox}:{oy}[z{i}];"
                f"[{label}a][z{i}]overlay=0:0:enable='between(t,{start},{end})'[{nxt}]")

        elif kind in ("broll", "graphic"):
            asset = ov.get("asset")
            if not asset or not pathlib.Path(asset).exists():
                sys.exit(f"ERROR: falta el archivo del overlay: {asset}")
            idx = len(inputs) + 1
            is_still = pathlib.Path(asset).suffix.lower() in (
                ".png", ".jpg", ".jpeg", ".webp")

            if is_still:
                inputs.append(["-loop", "1", "-framerate", str(fps),
                               "-t", f"{dur:.3f}", "-i", asset])
            elif pathlib.Path(asset).suffix.lower() == ".webm":
                # El decodificador nativo de VP9 DESCARTA el canal alfa: el
                # overlay se compondria como un rectangulo opaco. libvpx-vp9 si
                # lo lee, y hay que pedirlo antes del -i.
                inputs.append(["-c:v", "libvpx-vp9", "-i", asset])
            else:
                inputs.append(["-i", asset])

            chain = f"[{idx}:v]trim=0:{dur:.3f},setpts=PTS-STARTPTS+{start:.3f}/TB,"

            if kind == "broll":
                # Cover the frame completely — crop rather than letterbox.
                chain += (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                          f"crop={width}:{height},setsar=1")
                pos_x, pos_y = "0", "0"
            else:
                w = ov.get("width")
                chain += (f"scale={w}:-1,setsar=1" if w
                          else f"scale={width}:{height}:"
                               f"force_original_aspect_ratio=decrease,setsar=1")
                pos_x, pos_y = POSITIONS.get(ov.get("position", "full"),
                                             POSITIONS["full"])

            fade = float(ov.get("fade", 0.25))
            if fade > 0 and dur > fade * 2:
                chain += (f",format=yuva420p,"
                          f"fade=t=in:st={start:.3f}:d={fade}:alpha=1,"
                          f"fade=t=out:st={end - fade:.3f}:d={fade}:alpha=1")

            parts.append(f"{chain}[o{i}]")
            parts.append(
                f"[{label}][o{i}]overlay={pos_x}:{pos_y}:format=auto:"
                f"enable='between(t,{start},{end})'[{nxt}]")
        else:
            sys.exit(f"ERROR: tipo de overlay desconocido: '{kind}'")

        label = nxt

    return ";".join(parts), inputs, label


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl", nargs="?", default="edl.json")
    ap.add_argument("--video", default="build/rough.mp4")
    ap.add_argument("--timemap", default="build/timemap.json")
    ap.add_argument("--out", default="build/composited.mp4")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    edl = json.loads(pathlib.Path(args.edl).read_text(encoding="utf-8"))
    tm_path = pathlib.Path(args.timemap)
    timemap = json.loads(tm_path.read_text(encoding="utf-8")) if tm_path.exists() else None
    if timemap is None:
        print("aviso: sin timemap.json — se asume que los tiempos ya son de salida")

    out_cfg = edl.get("output", {})
    width, height = out_cfg.get("width", 1920), out_cfg.get("height", 1080)

    items, skipped = collect(edl, timemap)
    for s in skipped:
        print(f"  omitido (cayo en un corte): {s}")

    if not items:
        print("No hay overlays. Copiando el video tal cual.")
        fftool.run(["-i", args.video, "-c", "copy", args.out])
        print(f"OK  -> {args.out}")
        return

    for ov in items:
        print(f"  {ov['segment']:<5} {ov['type']:<8} "
              f"{ov['out_start']:7.2f}→{ov['out_end']:7.2f}  "
              f"{ov.get('asset', ov.get('scale',''))}")

    fps = edl.get("fps", 30)
    graph, inputs, final = build_graph(items, width, height, fps)
    if args.dry_run:
        print(f"\nfiltergraph ({len(graph)} chars):\n{graph}")
        return

    cmd = ["-i", args.video]
    for input_args in inputs:
        cmd += input_args
    cmd += ["-filter_complex", graph, "-map", f"[{final}]", "-map", "0:a?",
            "-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
            "-pix_fmt", "yuv420p", "-c:a", "copy",
            "-movflags", "+faststart", args.out]

    print(f"\nComponiendo {len(items)} overlays ...")
    fftool.run(cmd)
    print(f"OK  -> {args.out}")


if __name__ == "__main__":
    main()
