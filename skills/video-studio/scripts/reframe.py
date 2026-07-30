#!/usr/bin/env python3
"""Reframe a 16:9 video to 9:16 for TikTok / Reels / Shorts.

Presets
  blur    video centred over a blurred, zoomed copy of itself — safest default,
          nothing is ever cropped away
  crop    centre crop with an adjustable horizontal focus point; use when the
          speaker holds one side of the frame
  stack   screen recording on top, webcam below — the tutorial layout; needs
          --cam-rect to say where the webcam sits in the source frame

  python3 reframe.py build/final.mp4 --preset blur --out final/short.mp4
  python3 reframe.py build/final.mp4 --preset crop --focus 0.35
  python3 reframe.py build/final.mp4 --preset stack --cam-rect 1420,780,480,270
"""
import argparse
import pathlib
import sys

import fftool

W, H = 1080, 1920


def graph_blur(src_w, src_h):
    scaled_h = int(W * src_h / src_w) // 2 * 2
    return (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},boxblur=luma_radius=40:luma_power=2,eq=brightness=-0.12[bgb];"
        f"[fg]scale={W}:{scaled_h}[fgs];"
        f"[bgb][fgs]overlay=0:(H-h)/2:format=auto,setsar=1[v]"
    )


def graph_crop(focus):
    focus = min(max(focus, 0.0), 1.0)
    # Crop a 9:16 window out of the full-height frame, positioned by `focus`.
    return (
        f"[0:v]crop=ih*9/16:ih:(iw-ih*9/16)*{focus:.4f}:0,"
        f"scale={W}:{H},setsar=1[v]"
    )


def graph_stack(cam_rect, cam_scale=1.0):
    """Screen on top, webcam below, both fitted to full width.

    Nothing is cropped from the screen recording — losing half the width of a
    terminal or an IDE would defeat the point of a tutorial. Both bands keep
    their natural aspect ratio, are stacked, and the leftover vertical space is
    filled with a blurred copy of the frame rather than black bars.
    """
    cx, cy, cw, ch = cam_rect
    cam_w = int(W * min(max(cam_scale, 0.2), 1.0)) // 2 * 2
    cam_pad = "" if cam_w == W else f",pad={W}:ih:(ow-iw)/2:0:color=black@0"
    return (
        f"[0:v]split=3[bg][s][c];"
        f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},boxblur=luma_radius=40:luma_power=2,"
        f"eq=brightness=-0.15[bgb];"
        f"[s]scale={W}:-2,setsar=1[stop];"
        f"[c]crop={cw}:{ch}:{cx}:{cy},scale={cam_w}:-2,setsar=1{cam_pad}[cbot];"
        f"[stop][cbot]vstack=inputs=2[stk];"
        f"[bgb][stk]overlay=0:(H-h)/2:format=auto,setsar=1[v]"
    )


def probe_size(path):
    ffprobe = fftool.find_bin("ffprobe")
    import subprocess
    p = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True)
    try:
        w, h = p.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except ValueError:
        sys.exit(f"ERROR: no pude leer las dimensiones de {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--preset", choices=["blur", "crop", "stack"], default="blur")
    ap.add_argument("--out", default="final/short.mp4")
    ap.add_argument("--focus", type=float, default=0.5,
                    help="preset crop: 0=izquierda, 0.5=centro, 1=derecha")
    ap.add_argument("--cam-rect", help="preset stack: x,y,w,h de la webcam en el original")
    ap.add_argument("--cam-scale", type=float, default=1.0,
                    help="preset stack: ancho de la webcam, 0.2-1.0 (def 1.0)")
    ap.add_argument("--start", type=float, help="recortar desde este segundo")
    ap.add_argument("--duration", type=float, help="duracion del short en segundos")
    ap.add_argument("--crf", type=int, default=19)
    args = ap.parse_args()

    src = pathlib.Path(args.video)
    if not src.exists():
        sys.exit(f"ERROR: no existe {src}")
    src_w, src_h = probe_size(src)

    if args.preset == "blur":
        graph = graph_blur(src_w, src_h)
    elif args.preset == "crop":
        graph = graph_crop(args.focus)
    else:
        if not args.cam_rect:
            sys.exit("ERROR: el preset 'stack' necesita --cam-rect x,y,w,h\n"
                     "  Saca un frame y mide donde esta la webcam:\n"
                     "    ffmpeg -ss 5 -i video.mp4 -frames:v 1 frame.png")
        try:
            rect = [int(v) for v in args.cam_rect.split(",")]
            assert len(rect) == 4
        except (ValueError, AssertionError):
            sys.exit("ERROR: --cam-rect debe ser 'x,y,w,h' con enteros")
        graph = graph_stack(rect, args.cam_scale)

    dest = pathlib.Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = []
    if args.start is not None:
        cmd += ["-ss", str(args.start)]
    cmd += ["-i", str(src)]
    if args.duration is not None:
        cmd += ["-t", str(args.duration)]
    cmd += ["-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
            "-c:v", "libx264", "-crf", str(args.crf), "-preset", "medium",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(dest)]

    print(f"Origen   {src_w}x{src_h}")
    print(f"Preset   {args.preset}")
    print(f"Salida   {W}x{H}")
    fftool.run(cmd)
    print(f"OK  -> {dest} ({dest.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
