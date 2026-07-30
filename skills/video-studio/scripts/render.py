#!/usr/bin/env python3
"""Final encode: burn captions, normalise loudness, mix music, validate.

Loudness is normalised to -14 LUFS, the target YouTube, TikTok and Instagram all
converge on — deliver louder and the platform turns you down anyway, quieter and
you sound weak next to everyone else.

  python3 render.py build/composited.mp4 --captions captions/final.ass \\
      --music assets/track.mp3 --music-db -22 --out final/video.mp4
"""
import argparse
import json
import pathlib
import subprocess
import sys

import fftool

LUFS_TARGET = -14.0


def probe(path):
    ffprobe = fftool.find_bin("ffprobe")
    p = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate",
         "-of", "json", str(path)], capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--captions", help="archivo .ass a quemar")
    ap.add_argument("--music", help="pista de fondo")
    ap.add_argument("--music-db", type=float, default=-22.0,
                    help="volumen de la musica respecto a la voz (def -22 dB)")
    ap.add_argument("--out", default="final/video.mp4")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--no-loudnorm", action="store_true")
    args = ap.parse_args()

    src = pathlib.Path(args.video)
    if not src.exists():
        sys.exit(f"ERROR: no existe {src}")

    ffmpeg_bin = fftool.find_bin()
    dest = pathlib.Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["-i", str(src)]
    if args.music:
        if not pathlib.Path(args.music).exists():
            sys.exit(f"ERROR: no existe la musica {args.music}")
        cmd += ["-stream_loop", "-1", "-i", args.music]

    # ---- video chain ----
    vf = []
    if args.captions:
        fftool.require_filter("subtitles", ffmpeg_bin)
        safe = str(pathlib.Path(args.captions).resolve()).replace(":", r"\:")
        vf.append(f"subtitles='{safe}'")

    # ---- audio chain ----
    af = []
    if args.music:
        # Music is ducked well under the voice, then the mix is normalised as a
        # whole so the final loudness target still lands.
        filter_complex = (
            f"[1:a]volume={args.music_db}dB,afade=t=in:st=0:d=1.5[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[mix]"
        )
        if not args.no_loudnorm:
            filter_complex += f";[mix]loudnorm=I={LUFS_TARGET}:TP=-1.5:LRA=11[aout]"
            audio_label = "[aout]"
        else:
            audio_label = "[mix]"
        if vf:
            filter_complex += f";[0:v]{','.join(vf)}[vout]"
            video_map = "[vout]"
        else:
            video_map = "0:v"
        cmd += ["-filter_complex", filter_complex,
                "-map", video_map, "-map", audio_label]
    else:
        if vf:
            cmd += ["-vf", ",".join(vf)]
        if not args.no_loudnorm:
            af.append(f"loudnorm=I={LUFS_TARGET}:TP=-1.5:LRA=11")
        if af:
            cmd += ["-af", ",".join(af)]

    cmd += ["-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(dest)]

    print(f"Entrada    {src}")
    if args.captions:
        print(f"Subtitulos {args.captions}")
    if args.music:
        print(f"Musica     {args.music} @ {args.music_db} dB")
    print(f"Loudness   {'sin normalizar' if args.no_loudnorm else f'{LUFS_TARGET} LUFS'}")
    print("Renderizando (puede tardar) ...")

    fftool.run(cmd, ffmpeg_bin)

    # ---- validate ----
    info = probe(dest)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    print(f"\nOK  {dest}")
    print(f"    {fmt.get('duration','?')[:6]}s · "
          f"{int(fmt.get('size', 0))/1e6:.1f} MB")
    problems = []
    if video:
        print(f"    video {video['codec_name']} {video['width']}x{video['height']} "
              f"@ {video.get('r_frame_rate','?')}")
    else:
        problems.append("no hay pista de video")
    if audio:
        print(f"    audio {audio['codec_name']}")
    else:
        problems.append("NO HAY PISTA DE AUDIO")

    if problems:
        print("\nPROBLEMAS:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)


if __name__ == "__main__":
    main()
