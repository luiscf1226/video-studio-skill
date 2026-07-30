# Fase 6 — B-roll

**Meta:** conseguir el metraje de recurso que la Fase 3 pidió y componer todo
sobre el corte base. Sin gate.

## Buscar y descargar

```bash
python3 $SKILL/scripts/broll.py "programador escribiendo codigo" --n 4
python3 $SKILL/scripts/broll.py "microfono de estudio" --download --outdir broll
```

Busca en Pexels y Pixabay a la vez. Ambas son gratis, uso comercial permitido y
sin atribución obligatoria. Las keys son opcionales:

```bash
export PEXELS_API_KEY='...'      # pexels.com/api
export PIXABAY_API_KEY='...'     # pixabay.com/api/docs
```

Sin keys el script falla con un mensaje claro. En ese caso: o el usuario graba
el plano él mismo, o se sustituye por un gráfico de HyperFrames. **No inventes
rutas de archivos que no existen** — el compositor aborta si falta un asset.

## Buscar en inglés

Los catálogos están indexados en inglés. Traduce la consulta aunque el video sea
en español: `"manos escribiendo"` → `typing hands keyboard`.

## Elegir bien

- **3 a 5 segundos.** Más que eso y el espectador se pregunta por qué sigue ahí.
- Que **coincida con lo que se está diciendo** en ese momento exacto.
- Prefiere planos con movimiento lento. El b-roll no compite con la voz.
- Descarta lo que se vea a "stock genérico": gente en traje señalando pantallas.
- Resolución ≥ 1080p. El script ya prioriza el archivo más cercano a 1080p.

## Dónde poner b-roll

| Sí | No |
|---|---|
| mientras explica un concepto abstracto | mientras muestra un paso concreto en pantalla |
| para tapar un corte que quedó brusco | sobre la cara en el gancho |
| en la transición entre segmentos | porque un hueco "se ve vacío" |

Un tutorial vive de la pantalla real. El b-roll es la excepción, no el relleno.

## Componer

Añade cada clip como overlay en `edl.json` (tiempos en segundos del original) y:

```bash
python3 $SKILL/scripts/overlay.py edl.json \
    --video build/rough.mp4 --out build/composited.mp4
```

Esto aplica en una sola pasada los tres tipos: `graphic`, `broll` y `zoom`.
El audio original se conserva intacto — el b-roll solo cubre la imagen.

Si un overlay cayó dentro de un corte, el script lo avisa y lo recorta o lo
omite; revisa esos avisos antes de seguir.

## Verificar

```bash
ffmpeg -ss <segundo> -i build/composited.mp4 -frames:v 1 /tmp/check.png
```

Saca un frame en medio de cada overlay y míralo. Luego `phase: 7`.
