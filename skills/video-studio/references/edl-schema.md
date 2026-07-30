# Esquema de `edl.json`

La única fuente de verdad del edit. `review.md` y los `segment-NN.md` son para
que el humano lo entienda; **esto** es lo que se ejecuta.

## Regla de oro

**Todos los tiempos están en segundos del video ORIGINAL.** Nunca del video
cortado. `cut.py` genera `build/timemap.json` para traducir, y las fases
posteriores lo usan solas.

Consecuencia práctica: puedes reordenar cortes, quitar un segmento entero o
cambiar de opinión, y los overlays siguen apuntando al momento correcto del
material grabado.

## Estructura

```json
{
  "project": "tutorial-obs",
  "source": "raw/main.mp4",
  "fps": 30,
  "output": { "width": 1920, "height": 1080 },

  "segments": [
    {
      "id": "S01",
      "title": "Gancho",
      "keep": [
        { "start": 412.5, "end": 416.0 },
        { "start": 1.2,   "end": 24.8  }
      ],
      "overlays": [
        {
          "type": "graphic",
          "asset": "graphics/g01-titulo.mp4",
          "start": 3.0, "end": 7.5,
          "position": "lower-third",
          "width": 900,
          "fade": 0.3
        },
        {
          "type": "broll",
          "asset": "broll/pexels-123456.mp4",
          "start": 12.0, "end": 16.0,
          "fade": 0.25
        },
        {
          "type": "zoom",
          "start": 18.0, "end": 22.0,
          "scale": 1.3, "x": 0.5, "y": 0.35
        }
      ]
    }
  ]
}
```

## `keep`

Los bloques se concatenan **en el orden en que aparecen**, no en orden temporal.
Por eso el ejemplo empieza en el segundo 412: es el teaser del final, montado al
principio del video.

Bloques de menos de 0.10s se descartan con un aviso.

## `overlays`

| Campo | Tipos | Descripción |
|---|---|---|
| `type` | todos | `graphic` \| `broll` \| `zoom` |
| `start`, `end` | todos | segundos del ORIGINAL |
| `asset` | graphic, broll | ruta al archivo; debe existir o el script aborta |
| `fade` | graphic, broll | segundos de entrada/salida (def 0.25) |
| `position` | graphic | ver tabla abajo (def `full`) |
| `width` | graphic | ancho en px; la altura se calcula sola |
| `scale` | zoom | 1.2 = 20% de acercamiento |
| `x`, `y` | zoom | punto de foco, 0-1. `0.5,0.5` es el centro |

### Posiciones

`full` · `center` · `top-left` · `top-right` · `bottom-left` · `bottom-right` ·
`lower-third`

### Formatos de asset

| Formato | Uso |
|---|---|
| `.mp4` | opaco, pantalla completa |
| `.webm` (VP9 yuva420p) | con transparencia — soportado por este ffmpeg |
| `.png` / `.jpg` / `.webp` | estático; el script lo extiende a la duración pedida |

## Overlays que caen en un corte

Si el rango de un overlay se solapa parcialmente con material eliminado, se
**recorta** al fragmento que sobrevivió y se avisa. Solo se descarta si su rango
completo desapareció. Perder un lower-third entero porque su final cayó en una
pausa recortada sería peor que acortarlo unos frames.

## Errores frecuentes

| Síntoma | Causa |
|---|---|
| el video final dura de más | bloques `keep` solapados |
| un overlay no aparece | su rango cayó entero en un corte — revisa los avisos |
| `falta el archivo del overlay` | ruta relativa mal, o el gráfico no se renderizó |
| todo desincronizado | se re-corrió `cut.py` sin regenerar subtítulos y overlays |
