#!/usr/bin/env python3
"""Shared ffmpeg helpers: binary resolution and capability detection.

Homebrew's `ffmpeg` formula is a SLIM build — as of v8 it ships without libass,
freetype or fontconfig, so the `subtitles`, `ass` and `drawtext` filters do not
exist. Burning captions needs the batteries-included `ffmpeg-full` formula, which
is keg-only and therefore not on PATH.

This module prefers ffmpeg-full when it is installed and falls back to whatever
`ffmpeg` is on PATH, so cutting and rendering keep working either way.

Run directly for a capability report:  python3 fftool.py
"""
import os
import shutil
import subprocess
import sys

FULL_PREFIXES = (
    "/opt/homebrew/opt/ffmpeg-full/bin",   # Apple Silicon
    "/usr/local/opt/ffmpeg-full/bin",      # Intel
)

INSTALL_HINT = (
    "Los subtitulos necesitan libass, que el ffmpeg normal de Homebrew ya no trae.\n"
    "  Solucion (bottled, sin compilar, ~2 min):\n"
    "      brew install ffmpeg-full\n"
    "  Es keg-only: no reemplaza tu ffmpeg actual, estos scripts lo detectan solos."
)


def find_bin(name="ffmpeg"):
    """ffmpeg-full first, then PATH."""
    for prefix in FULL_PREFIXES:
        candidate = os.path.join(prefix, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    found = shutil.which(name)
    if not found:
        sys.exit(f"ERROR: no se encontro '{name}'. Instala con: brew install ffmpeg")
    return found


def filters(ffmpeg_bin=None):
    """Set of available filter names."""
    ffmpeg_bin = ffmpeg_bin or find_bin()
    p = subprocess.run([ffmpeg_bin, "-hide_banner", "-filters"],
                       capture_output=True, text=True)
    names = set()
    for line in p.stdout.splitlines():
        parts = line.split()
        # Format: "TSC name  in->out  description"
        if len(parts) >= 3 and not line.startswith(" Filters") and "=" not in parts[0]:
            names.add(parts[1] if len(parts[0]) <= 3 else parts[0])
    return names


def has_filter(name, ffmpeg_bin=None):
    return name in filters(ffmpeg_bin)


def require_filter(name, ffmpeg_bin=None):
    if not has_filter(name, ffmpeg_bin):
        sys.exit(f"ERROR: este ffmpeg no tiene el filtro '{name}'.\n{INSTALL_HINT}")


def run(args, ffmpeg_bin=None, quiet=True):
    ffmpeg_bin = ffmpeg_bin or find_bin()
    cmd = [ffmpeg_bin, "-y"] + (["-loglevel", "error"] if quiet else []) + args
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ERROR ffmpeg:\n{p.stderr.strip()}")
    return p.stdout


def probe_duration(path):
    ffprobe = find_bin("ffprobe")
    p = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except (ValueError, AttributeError):
        return None


def report():
    ffmpeg_bin = find_bin()
    available = filters(ffmpeg_bin)
    print(f"ffmpeg   {ffmpeg_bin}")
    is_full = "ffmpeg-full" in ffmpeg_bin
    print(f"build    {'ffmpeg-full (completo)' if is_full else 'slim (Homebrew core)'}")
    print()
    checks = {
        "subtitles": "quemar subtitulos .ass/.srt",
        "ass": "subtitulos con estilos avanzados",
        "drawtext": "texto dinamico sobre video",
        "overlay": "componer graficos y b-roll",
        "scale": "reescalar / reencuadrar",
        "loudnorm": "normalizar volumen",
        "zoompan": "zooms tipo Ken Burns",
        "colorchannelmixer": "canal alfa",
    }
    for name, desc in checks.items():
        mark = "OK " if name in available else "NO "
        print(f"  [{mark}] {name:<18} {desc}")
    if "subtitles" not in available:
        print(f"\n{INSTALL_HINT}")
    return "subtitles" in available


if __name__ == "__main__":
    sys.exit(0 if report() else 1)
