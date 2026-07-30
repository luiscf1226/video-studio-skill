# Fase 7 — Pulido

**Meta:** subtítulos, color, música y versión vertical. **Termina en gate:**
escribes `07-check.md` diciendo exactamente qué debe revisar el usuario.

## Subtítulos palabra por palabra

```bash
python3 $SKILL/scripts/captions.py transcript/words.json \
    --timemap build/timemap.json --out captions/final.ass \
    --style word --preset tiktok
```

`--style word` muestra una palabra a la vez. `--style group` muestra 3-5
palabras con la activa resaltada — se lee mejor y suele retener más; ofrécelo.
Presets: `tiktok` (Arial Black 96), `clean` (Avenir Next 78), `impact`
(Impact 110). Detalles en `references/caption-styles.md`.

Las palabras que cayeron en un corte se descartan solas. Una palabra solo se
descarta si perdió más de la mitad de su duración, así que un recorte de 20 ms
no borra el subtítulo.

**Requiere `ffmpeg-full`** para quemarlos:

```bash
brew install ffmpeg-full
```

El ffmpeg normal de Homebrew ya no trae libass, así que no tiene el filtro
`subtitles`. `ffmpeg-full` es bottled (no compila), es keg-only (no reemplaza tu
ffmpeg) y los scripts lo detectan solos. Verifica con:

```bash
python3 $SKILL/scripts/fftool.py
```

## Color

Este ffmpeg no tiene LUTs 3D, pero `eq` y `curves` cubren lo que un tutorial
necesita. Ver `references/color-grading.md`. Regla práctica: la cámara casi
siempre sale más fría y más plana que la captura de pantalla; iguala la cámara a
la pantalla, no al revés.

Aplícalo como un `-vf` extra en la Fase 8, no como un render aparte.

## Música

Solo si el video la pide. En un tutorial hablado suele estorbar. Si va:

- Debajo de la voz, `--music-db -22` o menos.
- Sin percusión marcada.
- `render.py` la mezcla, la loopea y normaliza el conjunto.

## Versión vertical

```bash
python3 $SKILL/scripts/reframe.py final/video.mp4 --preset stack \
    --cam-rect 1420,780,480,270 --start 132 --duration 40 --out final/short.mp4
```

| Preset | Cuándo |
|---|---|
| `stack` | tutorial con pantalla + webcam — pantalla arriba, cámara abajo |
| `blur` | solo cámara, o cuando no quieres perder nada del encuadre |
| `crop` | la persona ocupa un lado fijo del cuadro; ajusta `--focus` |

`--cam-rect` es dónde está la webcam en el frame original. Mídelo:

```bash
ffmpeg -ss 5 -i raw/main.mp4 -frames:v 1 /tmp/frame.png
```

Los subtítulos del short se generan aparte, con `--width 1080 --height 1920`.

## Escribe `07-check.md`

No pongas "revisa el video". Sé específico y da el segundo exacto:

```markdown
# Qué revisar

## Cortes que pueden haber quedado justos
- [ ] 02:14 — corte entre tomas repetidas, ¿se oye natural?
- [ ] 05:47 — se quitó "o sea", ¿falta aire?

## Gráficos
- [ ] 01:20 — diagrama: ¿se lee en el móvil?
- [ ] 04:03 — lower-third: ¿tapa algo importante?

## Subtítulos
- [ ] 03:12 — "OBS Studio", ¿bien escrito?
- [ ] ¿Van sincronizados en todo el video? Revisa 00:30, 04:00 y 08:00.

## Audio
- [ ] ¿Hay algún clic en un corte?
- [ ] ¿El volumen es parejo entre la parte de cámara y la de pantalla?

## Short
- [ ] ¿Se entiende solo, sin el video largo?
- [ ] ¿El texto queda dentro de la zona segura (lejos del borde inferior)?
```

## Gate

Presenta `07-check.md` y **detente**. Cuando apruebe:
`gates.polish_approved: true`, `phase: 8`.
