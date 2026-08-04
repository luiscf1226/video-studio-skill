#!/usr/bin/env python3
"""Genera imagenes y videos con modelos de pago por uso. PASO OPCIONAL.

Rutea al proveedor mas barato que tenga el modelo (kie.ai -> fal.ai -> wavespeed),
baja el resultado al disco de inmediato, y deja registro de cada prompt y cada
centavo gastado.

NUNCA gasta sin confirmacion: siempre imprime el costo estimado y exige --yes.
El tope de --budget se comprueba ANTES de cada llamada.

  python3 genmedia.py --list
  python3 genmedia.py "miniatura: laptop con presentacion 3D naranja" --model gpt-image-2 --n 3 --budget 0.30
  python3 genmedia.py "camara acercandose al grafico" --model kling --seconds 5 --image ref.png --budget 0.50
  python3 genmedia.py --gallery
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone

AQUI = pathlib.Path(__file__).resolve().parent
CATALOGO = AQUI.parent / "references/models.json"
ESPERA_MAX = 900          # segundos antes de rendirse con una tarea
INTERVALO = 4


# ----------------------------------------------------------------- utilidades
def curl(url, metodo="GET", headers=None, body=None, timeout=60):
    cmd = ["curl", "-sS", "--max-time", str(timeout), "-X", metodo, url]
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


def cargar_catalogo():
    if not CATALOGO.exists():
        sys.exit(f"ERROR: falta el catalogo {CATALOGO}")
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def buscar(cat, alias):
    for m in cat["modelos"]:
        if m["alias"] == alias:
            return m
    disponibles = ", ".join(m["alias"] for m in cat["modelos"])
    sys.exit(f"ERROR: modelo '{alias}' desconocido.\n  Disponibles: {disponibles}")


def opciones_ordenadas(cat, modelo):
    """Opciones del modelo que tienen su API key puesta, de mas barata a mas cara."""
    listas, sin_key = [], []
    for o in modelo["opciones"]:
        prov = cat["providers"][o["provider"]]
        if os.environ.get(prov["env"]):
            listas.append(o)
        else:
            sin_key.append((o["provider"], prov["env"]))
    listas.sort(key=lambda o: o["cost_usd"])
    return listas, sin_key


# ------------------------------------------------------------------ llamadas
def enviar_kie(prov, opcion, entrada, key):
    r, err = curl(prov["submit"], "POST",
                  {"Authorization": f"Bearer {key}"},
                  {"model": opcion["id"], "input": entrada})
    if err:
        return None, err
    tid = (r.get("data") or {}).get("taskId") or r.get("taskId")
    if not tid:
        return None, f"sin taskId: {str(r)[:220]}"
    return tid, None


def esperar_kie(prov, tid, key):
    t0 = time.time()
    while time.time() - t0 < ESPERA_MAX:
        r, err = curl(prov["poll"] + urllib.parse.quote(tid), "GET",
                      {"Authorization": f"Bearer {key}"})
        if err:
            return None, err
        d = r.get("data") or {}
        estado = (d.get("state") or "").lower()
        if estado in ("success", "succeeded", "completed"):
            res = d.get("resultJson") or d.get("result") or {}
            if isinstance(res, str):
                try:
                    res = json.loads(res)
                except json.JSONDecodeError:
                    pass
            urls = res.get("resultUrls") or res.get("urls") or []
            if isinstance(urls, str):
                urls = [urls]
            return urls, None
        if estado in ("fail", "failed", "error"):
            return None, d.get("failMsg") or "la tarea fallo"
        time.sleep(INTERVALO)
    return None, "tiempo de espera agotado"


def enviar_fal(prov, opcion, entrada, key):
    r, err = curl(prov["submit"] + opcion["id"], "POST",
                  {"Authorization": f"Key {key}"}, entrada)
    if err:
        return None, err
    rid = r.get("request_id")
    if not rid:
        return None, f"sin request_id: {str(r)[:220]}"
    return rid, None


def esperar_fal(prov, opcion, rid, key):
    base = f"{prov['poll']}{opcion['id']}/requests/{rid}"
    t0 = time.time()
    while time.time() - t0 < ESPERA_MAX:
        r, err = curl(base + "/status", "GET", {"Authorization": f"Key {key}"})
        if err:
            return None, err
        estado = (r.get("status") or "").upper()
        if estado == "COMPLETED":
            res, err = curl(base, "GET", {"Authorization": f"Key {key}"})
            if err:
                return None, err
            urls = []
            for clave in ("images", "video", "videos", "image"):
                v = res.get(clave)
                if isinstance(v, dict) and v.get("url"):
                    urls.append(v["url"])
                elif isinstance(v, list):
                    urls += [x["url"] for x in v if isinstance(x, dict) and x.get("url")]
            return urls, (None if urls else f"sin salida: {str(res)[:220]}")
        if estado in ("FAILED", "ERROR"):
            return None, "la tarea fallo"
        time.sleep(INTERVALO)
    return None, "tiempo de espera agotado"


def descargar(url, destino):
    """Se baja de inmediato: en kie.ai las URLs expiran a las 24 horas."""
    p = subprocess.run(["curl", "-sS", "--fail", "-L", "-o", str(destino), url],
                       capture_output=True, text=True)
    if p.returncode != 0:
        destino.unlink(missing_ok=True)
        return False
    return destino.stat().st_size > 0


# -------------------------------------------------------------------- salida
def registrar(outdir, fila):
    with open(outdir / "generations.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def gastado(outdir):
    log = outdir / "generations.jsonl"
    if not log.exists():
        return 0.0
    total = 0.0
    for linea in log.read_text(encoding="utf-8").splitlines():
        try:
            total += float(json.loads(linea).get("costo_usd", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return total


def galeria(outdir):
    """Contacto visual. Juzgar imagenes desde la terminal no funciona."""
    log = outdir / "generations.jsonl"
    filas = []
    if log.exists():
        for linea in log.read_text(encoding="utf-8").splitlines():
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    filas.reverse()

    tarjetas = []
    for f in filas:
        for ruta in f.get("archivos", []):
            nombre = pathlib.Path(ruta).name
            es_video = pathlib.Path(ruta).suffix.lower() in (".mp4", ".webm", ".mov")
            medio = (f'<video src="{nombre}" controls loop muted></video>' if es_video
                     else f'<img src="{nombre}" loading="lazy">')
            tarjetas.append(f"""<figure>
  {medio}
  <figcaption>
    <b>{f.get('modelo','?')}</b> · {f.get('provider','?')} · ${f.get('costo_usd',0):.3f}
    <p>{(f.get('prompt') or '')[:260]}</p>
    <small>{f.get('fecha','')}</small>
  </figcaption>
</figure>""")

    total = sum(float(f.get("costo_usd", 0)) for f in filas)
    html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Generaciones</title><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0A0A0F;color:#E8ECF1;font-family:system-ui,-apple-system,sans-serif;padding:36px}}
h1{{font-size:30px;margin-bottom:6px}}
.meta{{color:#8B94A1;margin-bottom:30px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:22px}}
figure{{background:#14141C;border:1px solid #262b36;border-radius:16px;overflow:hidden}}
img,video{{width:100%;display:block;background:#000}}
figcaption{{padding:16px 18px;font-size:14px}}
figcaption b{{color:#FF9500}}
figcaption p{{color:#AEB6C2;margin:10px 0;line-height:1.45}}
small{{color:#6B7280}}
</style></head><body>
<h1>Generaciones</h1>
<div class="meta">{len(tarjetas)} archivos · ${total:.2f} gastado en total</div>
<div class="g">{''.join(tarjetas) or '<p>Todavia no hay nada.</p>'}</div>
</body></html>"""
    destino = outdir / "index.html"
    destino.write_text(html, encoding="utf-8")
    return destino, len(tarjetas), total


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--n", type=int, default=1, help="cuantas variantes")
    ap.add_argument("--seconds", type=int, default=5, help="duracion, solo video")
    ap.add_argument("--image", help="imagen de referencia (imagen-a-imagen o imagen-a-video)")
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--outdir", default="generated")
    ap.add_argument("--budget", type=float, default=1.00,
                    help="tope de gasto en USD para ESTA corrida (def 1.00)")
    ap.add_argument("--yes", action="store_true", help="no preguntar antes de gastar")
    ap.add_argument("--list", action="store_true", help="ver el catalogo y salir")
    ap.add_argument("--gallery", action="store_true", help="regenerar la galeria y salir")
    args = ap.parse_args()

    cat = cargar_catalogo()
    outdir = pathlib.Path(args.outdir)

    if args.list:
        print("Modelos disponibles:\n")
        for m in cat["modelos"]:
            listas, sin_key = opciones_ordenadas(cat, m)
            estado = (f"${listas[0]['cost_usd']:.3f} via {listas[0]['provider']}"
                      if listas else "SIN API KEY")
            marca = "" if not listas or listas[0].get("verified") else "  (precio sin verificar)"
            print(f"  {m['alias']:<18} {m['tipo']:<7} {estado}{marca}")
            print(f"  {'':<18} {m['descripcion']}")
            if not listas and sin_key:
                print(f"  {'':<18} falta exportar: {', '.join(e for _, e in sin_key)}")
            print()
        return

    if args.gallery:
        outdir.mkdir(parents=True, exist_ok=True)
        destino, n, total = galeria(outdir)
        print(f"OK  {n} archivos · ${total:.2f} · -> {destino}")
        return

    if not args.prompt:
        sys.exit("ERROR: falta el prompt. Usa --list para ver los modelos.")

    modelo = buscar(cat, args.model)
    listas, sin_key = opciones_ordenadas(cat, modelo)
    if not listas:
        print(f"ERROR: no hay API key para ningun proveedor de '{args.model}'.", file=sys.stderr)
        for prov, env in sin_key:
            print(f"  {prov:<12} export {env}='...'", file=sys.stderr)
        sys.exit(1)

    es_video = modelo["tipo"] == "video"
    unidades = args.seconds if es_video else 1
    mejor = listas[0]
    costo_unit = mejor["cost_usd"] * unidades
    costo_total = costo_unit * args.n

    outdir.mkdir(parents=True, exist_ok=True)
    ya = gastado(outdir)

    print(f"Modelo      {modelo['alias']}  ({modelo['tipo']})")
    print(f"Proveedor   {mejor['provider']}  ->  {mejor['id']}")
    if len(listas) > 1:
        print(f"Respaldo    {', '.join(o['provider'] for o in listas[1:])}")
    print(f"Cantidad    {args.n}" + (f" x {args.seconds}s" if es_video else ""))
    print(f"Costo est.  ${costo_total:.3f}" +
          ("" if mejor.get("verified") else "   (precio SIN VERIFICAR, puede variar)"))
    print(f"Tope        ${args.budget:.2f}   ·   ya gastado en {outdir}/: ${ya:.2f}")

    if costo_total > args.budget:
        sys.exit(f"\nABORTADO: la estimacion (${costo_total:.3f}) supera el tope "
                 f"(${args.budget:.2f}).\n  Sube --budget o baja --n.")

    if not args.yes:
        try:
            r = input(f"\nGenerar y gastar ~${costo_total:.3f}? [s/N] ").strip().lower()
        except EOFError:
            sys.exit("\nABORTADO: hace falta --yes cuando no hay terminal interactiva.")
        if r not in ("s", "si", "sí", "y", "yes"):
            sys.exit("Cancelado. No se gasto nada.")

    sello = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ext = ".mp4" if es_video else ".png"
    creados, gasto_real = [], 0.0

    for i in range(args.n):
        # El tope se revisa ANTES de CADA llamada, no solo al inicio.
        if gasto_real + costo_unit > args.budget + 1e-9:
            print(f"\n  tope alcanzado tras {i} generacion(es); no se pide mas")
            break

        print(f"\n[{i+1}/{args.n}] generando ...")
        salida_urls, usado, error = None, None, None

        for opcion in listas:
            prov = cat["providers"][opcion["provider"]]
            key = os.environ[prov["env"]]

            entrada = dict(opcion.get("input") or {})
            entrada["prompt"] = args.prompt
            if es_video:
                entrada["duration"] = args.seconds
            else:
                entrada.setdefault("aspect_ratio", args.aspect)
            if args.image:
                ruta = pathlib.Path(args.image)
                if ruta.exists():
                    entrada["image_url"] = ruta.resolve().as_uri()
                else:
                    entrada["image_url"] = args.image

            if opcion["provider"] == "kie":
                tid, error = enviar_kie(prov, opcion, entrada, key)
                if tid:
                    salida_urls, error = esperar_kie(prov, tid, key)
            else:
                rid, error = enviar_fal(prov, opcion, entrada, key)
                if rid:
                    salida_urls, error = esperar_fal(prov, opcion, rid, key)

            if salida_urls:
                usado = opcion
                break
            print(f"     {opcion['provider']} fallo: {error}; probando el siguiente")

        if not salida_urls:
            print(f"     ERROR: ningun proveedor respondio. Ultimo: {error}")
            continue

        archivos = []
        for k, url in enumerate(salida_urls):
            nombre = f"{sello}-{modelo['alias']}-{i+1}{'' if k == 0 else f'-{k}'}{ext}"
            destino = outdir / nombre
            if descargar(url, destino):
                archivos.append(str(destino))
                print(f"     -> {destino}  ({destino.stat().st_size/1e6:.2f} MB)")
            else:
                print(f"     ERROR bajando {url[:70]}")

        if archivos:
            costo = usado["cost_usd"] * unidades
            gasto_real += costo
            creados += archivos
            registrar(outdir, {
                "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "prompt": args.prompt,
                "modelo": modelo["alias"],
                "provider": usado["provider"],
                "model_id": usado["id"],
                "costo_usd": round(costo, 4),
                "verificado": bool(usado.get("verified")),
                "archivos": archivos,
                "referencia": args.image,
            })

    destino, n, total = galeria(outdir)
    print(f"\n{'='*54}")
    print(f"Generados     {len(creados)} archivo(s)")
    print(f"Gasto real    ${gasto_real:.3f}   (acumulado en {outdir}/: ${total:.2f})")
    print(f"Galeria       {destino}")
    print(f"Registro      {outdir}/generations.jsonl")


if __name__ == "__main__":
    main()
