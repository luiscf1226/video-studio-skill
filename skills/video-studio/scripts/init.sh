#!/usr/bin/env bash
# Scaffold a video-studio project folder.
# Usage: init.sh <project-name> [parent-dir]
set -euo pipefail

NAME="${1:?uso: init.sh <nombre-proyecto> [directorio-padre]}"
PARENT="${2:-.}"
DIR="$PARENT/$NAME"

if [ -e "$DIR" ]; then
  echo "ERROR: '$DIR' ya existe. Elige otro nombre o continua ese proyecto." >&2
  exit 1
fi

mkdir -p "$DIR"/{raw,audio,transcript,segments,graphics,broll,build,captions,final}

cat > "$DIR/state.json" <<JSON
{
  "project": "$NAME",
  "phase": 0,
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "language": "es",
  "config": {
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "transcribe_model": "scribe_v2",
    "min_gap": 0.6,
    "keep_pad": 0.08,
    "caption_style": "word-by-word-upper"
  },
  "gates": {
    "outline_approved": false,
    "edl_approved": false,
    "polish_approved": false
  }
}
JSON

echo "Proyecto creado: $DIR"
echo "Siguiente paso: Fase 0 — idea y outline."
