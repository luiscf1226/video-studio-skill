#!/usr/bin/env python3
"""Transcribe a video with ElevenLabs Scribe.

Extracts a compact mono audio track with ffmpeg, uploads it via curl, and writes
three files into the transcript directory:

  raw.json    the untouched API response
  words.json  normalised word list  [{text, start, end, speaker}]
  raw.srt     a plain subtitle file for eyeballing the transcript

Dependency-free: stdlib + ffmpeg + curl. Requires ELEVENLABS_API_KEY.

  python3 transcribe.py raw/main.mp4 --outdir transcript --lang es
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"


def run(cmd, **kw):
    """Run a command, raising with stderr attached on failure."""
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        sys.exit(f"ERROR: {cmd[0]} failed\n{p.stderr.strip()}")
    return p.stdout


def extract_audio(video, dest):
    """Mono 16 kHz 64 kbps MP3 — plenty for ASR, ~30 MB per hour."""
    run(["ffmpeg", "-y", "-i", str(video), "-vn",
         "-ac", "1", "-ar", "16000", "-b:a", "64k", str(dest)])


def transcribe(audio, model, lang, diarize):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ERROR: falta ELEVENLABS_API_KEY.\n"
                 "  export ELEVENLABS_API_KEY='...'  (o anadelo a ~/.zshrc)")

    cmd = ["curl", "-sS", "--fail-with-body", "-X", "POST", API_URL,
           "-H", f"xi-api-key: {key}",
           "-F", f"model_id={model}",
           "-F", f"file=@{audio}"]
    if lang:
        cmd += ["-F", f"language_code={lang}"]
    if diarize:
        cmd += ["-F", "diarize=true"]

    out = run(cmd)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f"ERROR: respuesta no-JSON de ElevenLabs:\n{out[:800]}")


def normalise(payload):
    """Keep only real words; drop spacing/audio-event tokens."""
    words = []
    for w in payload.get("words", []):
        if w.get("type") not in (None, "word"):
            continue
        text = (w.get("text") or "").strip()
        if not text:
            continue
        words.append({
            "text": text,
            "start": round(float(w["start"]), 3),
            "end": round(float(w["end"]), 3),
            "speaker": w.get("speaker_id") or "speaker_0",
        })
    return words


def ts(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(words, dest, max_chars=42, max_gap=0.8):
    """Group words into readable caption lines for review purposes."""
    lines, cur = [], []
    for w in words:
        too_long = cur and len(" ".join(x["text"] for x in cur) + " " + w["text"]) > max_chars
        big_gap = cur and (w["start"] - cur[-1]["end"]) > max_gap
        if too_long or big_gap:
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)

    with open(dest, "w", encoding="utf-8") as f:
        for i, group in enumerate(lines, 1):
            f.write(f"{i}\n{ts(group[0]['start'])} --> {ts(group[-1]['end'])}\n"
                    f"{' '.join(x['text'] for x in group)}\n\n")
    return len(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--outdir", default="transcript")
    ap.add_argument("--model", default="scribe_v2", choices=["scribe_v2", "scribe_v1"])
    ap.add_argument("--lang", default="es", help="codigo ISO, o '' para autodetectar")
    ap.add_argument("--diarize", action="store_true", help="separar hablantes")
    args = ap.parse_args()

    video = pathlib.Path(args.video)
    if not video.exists():
        sys.exit(f"ERROR: no existe {video}")

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        audio = pathlib.Path(tmp) / "audio.mp3"
        print(f"[1/3] Extrayendo audio de {video.name} ...")
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / 1e6
        print(f"      {size_mb:.1f} MB")

        print(f"[2/3] Transcribiendo con {args.model} ...")
        payload = transcribe(audio, args.model, args.lang, args.diarize)

    print("[3/3] Escribiendo archivos ...")
    (outdir / "raw.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    words = normalise(payload)
    if not words:
        sys.exit("ERROR: la API no devolvio palabras con timestamps.")
    (outdir / "words.json").write_text(
        json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")

    n_lines = write_srt(words, outdir / "raw.srt")

    dur = words[-1]["end"]
    speakers = sorted({w["speaker"] for w in words})
    print(f"\nOK  {len(words)} palabras · {dur/60:.1f} min · {n_lines} lineas · "
          f"{len(speakers)} hablante(s)")
    print(f"    idioma detectado: {payload.get('language_code', '?')} "
          f"(confianza {payload.get('language_probability', 0):.2f})")
    print(f"    costo aprox: ${dur/3600*0.22:.3f}")
    print(f"    -> {outdir}/words.json")


if __name__ == "__main__":
    main()
