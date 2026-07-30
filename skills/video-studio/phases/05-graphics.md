# Fase 5 — Motion graphics con HyperFrames

**Meta:** renderizar cada gráfico que la Fase 3 pidió. Sin gate, pero se revisa
visualmente antes de componer.

HyperFrames renderiza HTML/CSS animado a MP4 con un navegador headless. Es
Apache 2.0, gratis, sin límite de renders y sin API key. Requiere Node 22+ y
ffmpeg, ambos ya presentes.

## Instalación (una sola vez)

```bash
npx skills add heygen-com/hyperframes --full-depth
```

Instala 19 skills que enseñan el flujo completo: planear, escribir el HTML,
animar, lintear, previsualizar y renderizar.

**Cuando esas skills estén instaladas, úsalas.** No inventes la API de
HyperFrames desde este archivo: invoca `/hyperframes` y deja que su router te
guíe. Lo de abajo es solo el contexto que ese router no tiene.

## Un proyecto por gráfico

```bash
cd graphics && npx hyperframes init g01-titulo
```

Convención: `graphics/gNN-<slug>/`, y el render final copiado a
`graphics/gNN-<slug>.mp4` — que es la ruta que va en el campo `asset` del
overlay en `edl.json`.

## Qué hacer con gráficos y qué no

| Sí | No |
|---|---|
| diagramas, flujos, arquitectura | cualquier cosa fotorrealista |
| comparativas antes/después | caras o personas |
| listas que aparecen punto por punto | video generativo |
| resaltar una parte de la UI | reemplazar un plano de pantalla real |
| títulos de sección, lower-thirds | rellenar porque sí |

Un gráfico existe para explicar algo que las palabras no explican bien. Si el
segmento se entiende sin él, no lo hagas.

## Reglas de diseño

- **Duración = lo que dura la frase que acompaña.** Sácalo de `words.json`, no
  lo adivines.
- **Entra en 0.3s, sale en 0.3s.** El compositor ya aplica el fade; no lo
  dupliques dentro del HTML.
- **Legible a 360px de ancho.** La mitad lo verá en el móvil. Texto mínimo
  equivalente a 32px sobre 1080p.
- **Fondo transparente** para lower-thirds y resaltados; **fondo completo** solo
  para títulos de sección.
- Máximo 7 palabras en pantalla a la vez.
- Reutiliza una paleta y una tipografía en todos los gráficos del video. Si el
  usuario tiene marca, úsala; si no, defínela una vez y anótala en
  `graphics/style.md` para los próximos videos.

## Formatos

| Necesidad | Formato |
|---|---|
| pantalla completa, opaco | MP4 (H.264) |
| encima del video, con transparencia | WebM VP9 con alfa (`-pix_fmt yuva420p`) |
| estático | PNG con canal alfa |

El compositor acepta los tres. Este ffmpeg **sí** soporta alfa en WebM VP9 —
verificado.

## Revisión antes de componer

Para cada gráfico, saca un frame y míralo de verdad:

```bash
ffmpeg -ss 1 -i graphics/g01-titulo.mp4 -frames:v 1 /tmp/g01.png
```

Comprueba: ¿se lee?, ¿está cortado?, ¿tiene el fondo correcto?, ¿la duración
coincide con el overlay del `edl.json`?

Anota en `edl.json` la ruta de cada gráfico en su overlay. Luego `phase: 6`.
