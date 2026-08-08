#!/usr/bin/env python3
"""Upscale a local video with Topaz on fal.ai. PASO OPCIONAL, DE PAGO.

Not a genmedia.py model: Topaz takes a *video file* as input, not a text prompt,
so it does not fit the generate-from-a-prompt shape genmedia.py expects. This is
a small dedicated script instead.

Verified pricing (fal-ai/topaz/upscale/video, per fal.ai's own model page — the
$0.02/s figure also matches a real invoice from a 720p->1080p run):

    $0.01/s of SOURCE video for output up to 720p
    $0.02/s of SOURCE video for output 720p -> 1080p   (the common case)
    $0.08/s of SOURCE video for output above 1080p
    price DOUBLES for 60fps output, HALVES for Gaia 2 output

A 26s clip upscaled to 1080p costs ~$0.52. This is usually far cheaper than
generating natively at a higher resolution — generate at 480p or 720p, upscale
at the end, not the other way around. (Exception: if the target is 1080p,
compare against LTX Video 2.0 Fast, which generates natively at 1080p for
$0.04/s with no separate upscale pass — see references/models.json.)

This script assumes the common 720p->1080p case ($0.02/s) for its cost
estimate; pass --rate to override if you know your source/target differs.

    export FAL_KEY='...'

    python3 upscale.py raw.mp4 --factor 1.5 --model Proteus --yes
    python3 upscale.py raw.mp4 --out final/hero_1080p.mp4 --budget 1.00
"""
import argparse
import json
import mimetypes
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

RATE_PER_SEC = 0.02  # fal-ai/topaz/upscale/video, verified
UPLOAD_INITIATE = "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3"
SUBMIT = "https://queue.fal.run/fal-ai/topaz/upscale/video"
ESPERA_MAX = 900
INTERVALO = 5


def curl_json(url, method="GET", headers=None, body=None, timeout=60):
    cmd = ["curl", "-sS", "--max-time", str(timeout), "-X", method, url]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stderr or p.stdout)[:400]
    try:
        return json.loads(p.stdout), None
    except json.JSONDecodeError:
        return None, p.stdout[:400]


def ffprobe_duration(path):
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        sys.exit(f"ERROR: no pude leer la duracion de {path} (ffprobe)")


def upload(path, key):
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    init, err = curl_json(UPLOAD_INITIATE, "POST", {"Authorization": f"Key {key}"},
                           {"content_type": mime, "file_name": path.name})
    if err or not init:
        sys.exit(f"ERROR subiendo a fal storage: {err}")
    put = subprocess.run(
        ["curl", "-sS", "--fail", "-X", "PUT", "-H", f"Content-Type: {mime}",
         "--data-binary", f"@{path}", init["upload_url"]],
        capture_output=True, text=True)
    if put.returncode != 0:
        sys.exit(f"ERROR subiendo el archivo: {put.stderr.strip()}")
    return init["file_url"]


def submit(video_url, factor, model, h264, key):
    body = {"video_url": video_url, "upscale_factor": factor, "model": model,
            "H264_output": h264}
    r, err = curl_json(SUBMIT, "POST", {"Authorization": f"Key {key}"}, body)
    if err or not r:
        sys.exit(f"ERROR enviando a fal.ai: {err}")
    return r["status_url"], r["response_url"]


def wait(status_url, key):
    t0 = time.time()
    while time.time() - t0 < ESPERA_MAX:
        st, err = curl_json(status_url, "GET", {"Authorization": f"Key {key}"})
        if err:
            sys.exit(f"ERROR consultando estado: {err}")
        status = st.get("status")
        if status == "COMPLETED":
            return
        if status in ("FAILED", "CANCELLED", "ERROR"):
            sys.exit(f"ERROR: fal.ai devolvio {status}: {json.dumps(st)[:400]}")
        time.sleep(INTERVALO)
    sys.exit("ERROR: se agoto el tiempo de espera (15 min)")


def download(url, dest):
    p = subprocess.run(["curl", "-sS", "--fail", "-L", "-o", str(dest), url],
                       capture_output=True, text=True)
    if p.returncode != 0 or dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        sys.exit(f"ERROR bajando el resultado: {p.stderr.strip()}")


def registrar(outdir, fila):
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "generations.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="archivo de video local a escalar")
    ap.add_argument("--factor", type=float, default=1.5, help="factor de escalado (def 1.5)")
    ap.add_argument("--model", default="Proteus", choices=["Proteus", "Apollo"],
                    help="Proteus = general purpose; Apollo = mas nitido en detalle fino")
    ap.add_argument("--h264", action="store_true", default=True,
                    help="salida H.264 (compatible con editores); default true")
    ap.add_argument("--out", default=None, help="ruta de salida (def: <video>_upscaled.mp4)")
    ap.add_argument("--outdir", default="generated", help="carpeta para el log de gasto")
    ap.add_argument("--budget", type=float, default=2.00, help="tope de gasto en USD (def 2.00)")
    ap.add_argument("--rate", type=float, default=RATE_PER_SEC,
                    help=f"$/s de fuente (def {RATE_PER_SEC}, el caso 720p->1080p; "
                         "usa 0.01 si tu salida queda en <=720p, 0.08 si es >1080p)")
    ap.add_argument("--yes", action="store_true", help="no preguntar antes de gastar")
    args = ap.parse_args()

    key = os.environ.get("FAL_KEY", "").strip()
    if not key:
        sys.exit("ERROR: FAL_KEY no esta en el entorno. export FAL_KEY='...'")

    src = pathlib.Path(args.video)
    if not src.exists():
        sys.exit(f"ERROR: no existe {src}")

    dur = ffprobe_duration(src)
    costo = round(args.rate * dur, 4)

    print(f"Fuente      {src}  ({dur:.1f}s)")
    print(f"Factor      x{args.factor}  ·  modelo {args.model}")
    print(f"Costo est.  ${costo:.3f}   (${args.rate}/s de fuente, precio verificado en fal.ai)")
    print(f"Tope        ${args.budget:.2f}")

    if costo > args.budget:
        sys.exit(f"\nABORTADO: la estimacion (${costo:.3f}) supera el tope (${args.budget:.2f}).")

    if not args.yes:
        try:
            r = input(f"\nEscalar y gastar ~${costo:.3f}? [s/N] ").strip().lower()
        except EOFError:
            sys.exit("\nABORTADO: hace falta --yes cuando no hay terminal interactiva.")
        if r not in ("s", "si", "sí", "y", "yes"):
            sys.exit("Cancelado. No se gasto nada.")

    dest = pathlib.Path(args.out) if args.out else src.with_name(src.stem + "_upscaled.mp4")

    print("\nSubiendo...")
    video_url = upload(src, key)
    print("Procesando en fal.ai (Topaz)...")
    status_url, response_url = submit(video_url, args.factor, args.model, args.h264, key)
    wait(status_url, key)
    result, err = curl_json(response_url, "GET", {"Authorization": f"Key {key}"})
    if err or not result or not result.get("video", {}).get("url"):
        sys.exit(f"ERROR: no llego un video de vuelta: {err or result}")

    print(f"Bajando -> {dest}")
    download(result["video"]["url"], dest)

    registrar(pathlib.Path(args.outdir), {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modelo": "topaz-upscale",
        "provider": "fal",
        "model_id": "fal-ai/topaz/upscale/video",
        "costo_usd": costo,
        "verificado": True,
        "archivos": [str(dest)],
        "referencia": str(src),
    })

    print(f"\nOK  {dest}  ({dest.stat().st_size/1e6:.1f} MB)  ·  ${costo:.3f} gastado")


if __name__ == "__main__":
    main()
