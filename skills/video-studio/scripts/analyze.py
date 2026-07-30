#!/usr/bin/env python3
"""Find dead space, filler words and stutters in a transcript.

Reads words.json (from transcribe.py) and writes analysis.json listing every
candidate removal, each tagged with a confidence tier:

  tier1  non-lexical noise (eh, mmm, uhm) — safe to cut automatically
  tier2  real Spanish words used as verbal crutches (bueno, o sea, pues) —
         NEVER cut these without asking; removing them can butcher the meaning
  gap    silence longer than --min-gap
  stutter  the same word repeated back to back

With --emit-edl it also writes a draft edl.json that removes tier1 + gaps only.

  python3 analyze.py transcript/words.json --emit-edl edl.json --source raw/main.mp4
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import unicodedata

# Non-lexical noise. These are never meaningful words in Spanish or English.
TIER1 = {
    "eh", "ehh", "eeh", "eee", "ee", "em", "emm", "ehm", "mmm", "mm", "mmh",
    "hmm", "hm", "uh", "uhh", "uhm", "um", "ah", "ahh", "aah", "er", "err",
    "aja", "ajam", "mhm",
}

# Real words that function as crutches. Flagged for review, never auto-cut.
TIER2_SINGLE = {
    "bueno", "entonces", "pues", "digamos", "tipo", "verdad", "cierto",
    "obviamente", "basicamente", "literalmente", "ok", "okey", "este", "esto",
}
TIER2_PHRASES = [
    ("o", "sea"), ("osea",), ("como", "que"), ("es", "decir"),
    ("por", "asi", "decirlo"), ("no", "se"), ("ya", "saben"),
]


def fold(text):
    """Lowercase, strip accents and punctuation, for robust matching."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", text)


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def find_gaps(words, min_gap):
    gaps = []
    for prev, nxt in zip(words, words[1:]):
        length = nxt["start"] - prev["end"]
        if length >= min_gap:
            gaps.append({
                "kind": "gap", "tier": "gap",
                "start": round(prev["end"], 3), "end": round(nxt["start"], 3),
                "duration": round(length, 3),
                "note": f"silencio de {length:.1f}s despues de \"{prev['text']}\"",
            })
    return gaps


def find_fillers(words):
    hits = []
    folded = [fold(w["text"]) for w in words]

    # Multi-word crutch phrases first, so "o sea" isn't split into two misses.
    consumed = set()
    for i in range(len(words)):
        for phrase in TIER2_PHRASES:
            n = len(phrase)
            if i + n <= len(words) and tuple(folded[i:i + n]) == phrase:
                if any(j in consumed for j in range(i, i + n)):
                    continue
                consumed.update(range(i, i + n))
                hits.append({
                    "kind": "filler", "tier": "tier2",
                    "start": words[i]["start"], "end": words[i + n - 1]["end"],
                    "text": " ".join(w["text"] for w in words[i:i + n]),
                    "note": "muletilla — revisar antes de cortar",
                })

    for i, w in enumerate(words):
        if i in consumed:
            continue
        f = folded[i]
        if f in TIER1:
            hits.append({
                "kind": "filler", "tier": "tier1",
                "start": w["start"], "end": w["end"], "text": w["text"],
                "note": "ruido — corte automatico seguro",
            })
        elif f in TIER2_SINGLE:
            hits.append({
                "kind": "filler", "tier": "tier2",
                "start": w["start"], "end": w["end"], "text": w["text"],
                "note": "muletilla — revisar antes de cortar",
            })
    return hits


def find_stutters(words):
    """Same word twice in a row within a short window = a stumble."""
    out = []
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        if fold(a["text"]) and fold(a["text"]) == fold(b["text"]) \
                and b["start"] - a["end"] < 0.7:
            out.append({
                "kind": "stutter", "tier": "tier1",
                "start": a["start"], "end": a["end"], "text": a["text"],
                "note": f"repeticion de \"{a['text']}\" — cortar la primera",
            })
    return out


def merge(ranges, join_within=0.05):
    """Merge overlapping / near-touching (start, end) ranges."""
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [list(ranges[0])]
    for s, e in ranges[1:]:
        if s <= merged[-1][1] + join_within:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [tuple(r) for r in merged]


def invert(removals, total, min_keep=0.15):
    """Turn removal ranges into keep ranges over [0, total].

    Every bound is clamped into [0, total]. Without this, a transcript that runs
    longer than the video — a truncated upload, or `--source` pointing at a
    different file — silently produces keep ranges past the end of the footage,
    and the EDL claims a longer output than the input.
    """
    keeps, cursor = [], 0.0
    for s, e in removals:
        s = min(max(0.0, s), total)
        e = min(max(0.0, e), total)
        if e <= s:
            continue
        if s > cursor:
            keeps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total:
        keeps.append((cursor, total))
    return [(round(s, 3), round(e, 3)) for s, e in keeps
            if e - s >= min_keep and s < total]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", help="transcript/words.json")
    ap.add_argument("--min-gap", type=float, default=0.6,
                    help="silencio minimo a marcar, en segundos (def 0.6)")
    ap.add_argument("--pad", type=float, default=0.08,
                    help="respiro que se PROTEGE antes de cada palabra, en "
                         "segundos: los silencios se recortan hasta aqui y no "
                         "mas, para no cortar el ataque de la siguiente "
                         "palabra (def 0.08)")
    ap.add_argument("--out", default="analysis.json")
    ap.add_argument("--emit-edl", metavar="PATH",
                    help="escribir tambien un edl.json borrador")
    ap.add_argument("--source", help="video original (necesario para --emit-edl)")
    args = ap.parse_args()

    words = json.loads(pathlib.Path(args.words).read_text(encoding="utf-8"))
    if not words:
        sys.exit("ERROR: words.json esta vacio")

    gaps = find_gaps(words, args.min_gap)
    fillers = find_fillers(words)
    stutters = find_stutters(words)
    findings = sorted(gaps + fillers + stutters, key=lambda x: x["start"])

    spoken = words[-1]["end"]
    tier1 = [f for f in findings if f["tier"] == "tier1"]
    tier2 = [f for f in findings if f["tier"] == "tier2"]
    auto_cut = sum(f["end"] - f["start"] for f in tier1) \
        + sum(f["duration"] - args.min_gap * 0.5 for f in gaps)

    analysis = {
        "source_words": len(words),
        "spoken_duration": round(spoken, 2),
        "summary": {
            "gaps": len(gaps),
            "tier1_fillers": len(tier1),
            "tier2_fillers": len(tier2),
            "stutters": len(stutters),
            "auto_removable_seconds": round(auto_cut, 1),
        },
        "findings": findings,
    }
    pathlib.Path(args.out).write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Palabras        {len(words)}")
    print(f"Duracion        {spoken/60:.1f} min")
    print(f"Silencios       {len(gaps)}  (>{args.min_gap}s)")
    print(f"Ruido tier1     {len(tier1)}  -> corte automatico")
    print(f"Muletillas t2   {len(tier2)}  -> requieren tu decision")
    print(f"Repeticiones    {len(stutters)}")
    print(f"Recorte auto    ~{auto_cut:.0f}s ({auto_cut/spoken*100:.0f}% del video)")
    print(f"-> {args.out}")

    if not args.emit_edl:
        return

    if not args.source:
        sys.exit("ERROR: --emit-edl necesita --source <video>")
    total = probe_duration(args.source) or spoken

    if spoken > total + 1.0:
        print(f"\n*** AVISO: el transcript llega a {spoken/60:.1f} min pero "
              f"{args.source} dura {total/60:.1f} min.")
        print("    Casi siempre significa que --source no es el video que se "
              "transcribio,")
        print("    o que la subida a la API se corto. Los cortes se limitan a "
              "la duracion real,")
        print("    pero revisa esto antes de aprobar el EDL en la Fase 3.")

    # Draft removes tier1 noise + stutters + the *excess* of each silence.
    #
    # Filler words use the ASR word boundaries as-is — those are already tight.
    # Silences are trimmed conservatively: keep half a beat of natural pause at
    # the front, and stop `pad` short of the next word so its consonant attack
    # is never clipped. Padding CONTRACTS a removal; it never widens it.
    removals = [(f["start"], f["end"]) for f in findings if f["tier"] == "tier1"]
    for g in gaps:
        start = g["start"] + args.min_gap * 0.5
        end = g["end"] - args.pad
        if end - start > 0.05:
            removals.append((start, end))

    keeps = invert(merge(removals), total)
    edl = {
        "project": pathlib.Path(args.source).stem,
        "source": args.source,
        "fps": 30,
        "output": {"width": 1920, "height": 1080},
        "_comment": "Todos los tiempos son en SEGUNDOS del video ORIGINAL.",
        "segments": [{
            "id": "S01",
            "title": "Sin titulo — dividir en segmentos en la Fase 3",
            "keep": [{"start": s, "end": e} for s, e in keeps],
            "overlays": [],
        }],
    }
    pathlib.Path(args.emit_edl).write_text(
        json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8")

    kept = sum(e - s for s, e in keeps)
    print(f"\nBorrador EDL: {len(keeps)} tomas · {kept/60:.1f} min de {total/60:.1f} min "
          f"({(1-kept/total)*100:.0f}% recortado)")
    print(f"-> {args.emit_edl}   (revisar en la Fase 3 antes de cortar)")


if __name__ == "__main__":
    main()
