#!/usr/bin/env python3
"""Search and download free stock b-roll from Pexels and Pixabay.

Both APIs are free, allow commercial use and require no attribution. Get keys at
https://www.pexels.com/api/ and https://pixabay.com/api/docs/ then:

    export PEXELS_API_KEY='...'
    export PIXABAY_API_KEY='...'

  python3 broll.py "programador escribiendo codigo" --n 3 --orientation landscape
  python3 broll.py "teclado macro" --download --outdir broll
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse

PEXELS_URL = "https://api.pexels.com/videos/search"
PIXABAY_URL = "https://pixabay.com/api/videos/"


def fetch(url, headers=None):
    cmd = ["curl", "-sS", "--fail-with-body", "-L", url]
    for key, value in (headers or {}).items():
        cmd += ["-H", f"{key}: {value}"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, p.stderr.strip() or p.stdout.strip()
    try:
        return json.loads(p.stdout), None
    except json.JSONDecodeError:
        return None, p.stdout[:300]


def search_pexels(query, count, orientation):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return [], "PEXELS_API_KEY no configurada"
    params = {"query": query, "per_page": count, "orientation": orientation}
    data, err = fetch(f"{PEXELS_URL}?{urllib.parse.urlencode(params)}",
                      {"Authorization": key})
    if err:
        return [], f"Pexels: {err}"

    out = []
    for video in data.get("videos", []):
        # Best file at or below 1080p — 4K stock is wasted on a 1080p timeline.
        files = sorted(
            (f for f in video.get("video_files", []) if f.get("height")),
            key=lambda f: (f["height"] > 1080, -f["height"]))
        if not files:
            continue
        best = files[0]
        out.append({
            "source": "pexels", "id": video["id"],
            "url": best["link"], "width": best["width"], "height": best["height"],
            "duration": video.get("duration"),
            "credit": video.get("user", {}).get("name", "?"),
            "page": video.get("url"),
        })
    return out, None


def search_pixabay(query, count, orientation):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return [], "PIXABAY_API_KEY no configurada"
    params = {"key": key, "q": query, "per_page": max(3, count),
              "video_type": "film"}
    data, err = fetch(f"{PIXABAY_URL}?{urllib.parse.urlencode(params)}")
    if err:
        return [], f"Pixabay: {err}"

    out = []
    for hit in data.get("hits", [])[:count]:
        streams = hit.get("videos", {})
        pick = streams.get("large") or streams.get("medium") or streams.get("small")
        if not pick or not pick.get("url"):
            continue
        wide = pick.get("width", 0) >= pick.get("height", 0)
        if orientation == "landscape" and not wide:
            continue
        if orientation == "portrait" and wide:
            continue
        out.append({
            "source": "pixabay", "id": hit["id"],
            "url": pick["url"], "width": pick.get("width"), "height": pick.get("height"),
            "duration": hit.get("duration"),
            "credit": hit.get("user", "?"), "page": hit.get("pageURL"),
        })
    return out, None


def download(item, outdir):
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    dest = outdir / f"{item['source']}-{item['id']}.mp4"
    if dest.exists():
        print(f"    ya existe: {dest}")
        return dest
    p = subprocess.run(["curl", "-sS", "--fail", "-L", "-o", str(dest), item["url"]],
                       capture_output=True, text=True)
    if p.returncode != 0:
        print(f"    ERROR bajando {item['url']}: {p.stderr.strip()}")
        dest.unlink(missing_ok=True)
        return None
    print(f"    -> {dest} ({dest.stat().st_size/1e6:.1f} MB)")
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--orientation", default="landscape",
                    choices=["landscape", "portrait", "square"])
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--outdir", default="broll")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args()

    results, problems = [], []
    for search in (search_pexels, search_pixabay):
        found, err = search(args.query, args.n, args.orientation)
        results.extend(found)
        if err:
            problems.append(err)

    if not results:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        sys.exit(f"\nSin resultados para '{args.query}'.\n"
                 "Si faltan las API keys, graba este plano tu mismo o usa una "
                 "animacion de HyperFrames en su lugar.")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for problem in problems:
            print(f"  aviso: {problem}")
        print(f"\n{len(results)} clips para '{args.query}':")
        for item in results:
            print(f"  [{item['source']:<7}] {item['width']}x{item['height']} "
                  f"{item.get('duration','?')}s  por {item['credit']}")
            print(f"            {item['page']}")

    if args.download:
        print(f"\nDescargando a {args.outdir}/ ...")
        for item in results:
            download(item, args.outdir)


if __name__ == "__main__":
    main()
