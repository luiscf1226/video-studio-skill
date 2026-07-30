# Fase 2 — Transcripción

**Meta:** convertir el audio en un transcript con timestamp por palabra. Todo lo
que hace la Fase 3 depende de la precisión de estos tiempos.

Sin gate — corre y pasa a la Fase 3.

## Ejecutar

```bash
export ELEVENLABS_API_KEY='...'      # si aun no esta en el entorno
python3 $SKILL/scripts/transcribe.py raw/main.mp4 --outdir transcript --lang es
```

Con varias personas en cámara añade `--diarize`.

Produce:

| Archivo | Uso |
|---|---|
| `transcript/raw.json` | respuesta cruda de la API, por si hay que reprocesar |
| `transcript/words.json` | **el que usan todas las fases siguientes** |
| `transcript/raw.srt` | para leer el transcript de corrido |

## Costo

$0.22/hora. Un video de 12 minutos cuesta **$0.044**. El script imprime el costo
real al terminar. Si el usuario va a iterar, no re-transcribas: `words.json` no
cambia aunque cambie el edit.

## Si falla

| Síntoma | Causa | Solución |
|---|---|---|
| `falta ELEVENLABS_API_KEY` | no exportada | `export ELEVENLABS_API_KEY='...'` |
| 401 | key inválida o sin saldo | revisar en elevenlabs.io |
| 413 | archivo enorme | el script ya comprime a mono 16 kHz; si aún falla, parte el video |
| palabras en inglés | autodetección | forzar `--lang es` |

**Alternativa gratis y local** (sin API, más lenta, algo menos precisa en
español acentuado):

```bash
brew install ffmpeg-full          # incluye whisper-cpp
```

Luego transcribe con whisper-cpp y convierte su JSON al formato de `words.json`:
una lista de `{text, start, end, speaker}` con tiempos en segundos. Ese es el
único contrato que el resto del pipeline necesita.

## Verificación antes de seguir

1. Lee `transcript/raw.srt` por encima. ¿Los nombres técnicos salen bien escritos?
   Si dice "obs estudio" en vez de "OBS Studio", corrígelo en `words.json` —
   los subtítulos salen de ahí.
2. Confirma que el último timestamp se parece a la duración real del video.
   Si el transcript termina en 3:20 y el video dura 11:00, la subida se truncó.

Luego `state.json` → `phase: 3`.
