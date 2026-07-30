# Fase 8 — Render final

**Meta:** el archivo que se sube. Sin gate — pero valida antes de declarar listo.

## Render

```bash
python3 $SKILL/scripts/render.py build/composited.mp4 \
    --captions captions/final.ass \
    --out final/<nombre>-youtube.mp4
```

Con música: `--music assets/track.mp3 --music-db -22`.
Con color: añade los filtros de `references/color-grading.md`.

Normaliza a **-14 LUFS**, que es a donde convergen YouTube, TikTok e Instagram.
Más alto y la plataforma lo baja igual; más bajo y suenas débil al lado del resto.

## Short

```bash
python3 $SKILL/scripts/reframe.py final/<nombre>-youtube.mp4 \
    --preset stack --cam-rect <x,y,w,h> --start <s> --duration 40 \
    --out final/<nombre>-short.mp4
```

Los subtítulos del short van con `--width 1080 --height 1920`; los del video
horizontal no sirven, se salen del cuadro.

## Transcript final

El transcript original ya no describe el video editado. Genera el nuevo:

```bash
python3 $SKILL/scripts/captions.py transcript/words.json \
    --timemap build/timemap.json --out transcript/final.srt
```

Sirve para la descripción de YouTube, los capítulos y el SEO. Si `captions.py`
solo emite `.ass`, convierte con ffmpeg: `ffmpeg -i final.ass final.srt`.

## Validar

`render.py` ya comprueba que existan pista de video y de audio, y falla si no.
Además, a mano:

```bash
ffprobe -v error -show_format -show_streams final/<nombre>-youtube.mp4
```

- [ ] Duración = la de `review.md` ±5s
- [ ] H.264 High, yuv420p, `+faststart`
- [ ] AAC 48 kHz, presente
- [ ] Se abre en QuickTime
- [ ] Los primeros 3 segundos tienen imagen y sonido (el fallo más común)

## Nombres

```
final/
├── <slug>-youtube.mp4
├── <slug>-short.mp4
├── <slug>.srt
└── <slug>-metadata.md      titulo, descripcion, tags, capitulos
```

Capítulos para la descripción, sacados de `timemap.json` y de los segmentos:

```
00:00 Intro
01:12 Configurar OBS
```

## Limpieza

Borra solo intermedios reproducibles:

```bash
rm -rf build/parts build/rough.mp4 build/composited.mp4
```

**Nunca borres** `raw/`, `edl.json`, `transcript/`, `graphics/` ni `final/`. Con
`raw/` y `edl.json` se reconstruye todo; sin ellos, no hay vuelta atrás.

## Cierre

`state.json` → `phase: 9` (terminado). Reporta al usuario:

- rutas finales y tamaños
- duración original vs final
- costo real de la transcripción
- qué quedó pendiente, si algo

Si algo no se pudo hacer (faltó una API key, un gráfico no salió bien), **dilo
explícitamente**. No lo reportes como completo.
