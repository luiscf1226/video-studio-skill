# Estilos de subtítulos

## Los dos modos

### `--style word`
Una palabra a la vez, enorme, centrada. Máxima atención por palabra, ritmo muy
marcado. Es lo que pide el formato vertical corto.

### `--style group`
3-5 palabras visibles, la activa resaltada en color. Se lee mejor porque el ojo
anticipa la frase; suele retener más en video horizontal. Ajustable con
`--max-words` y `--max-gap`.

Ante la duda: `word` para shorts, `group` para YouTube.

## Presets

| Preset | Fuente | Tamaño | Resaltado | Para |
|---|---|---|---|---|
| `tiktok` | Arial Black | 96 | ámbar | vertical, alto contraste |
| `clean` | Avenir Next | 78 | dorado | tutorial horizontal, más sobrio |
| `impact` | Impact | 110 | verde | ganchos, máxima agresividad |

Las tres fuentes están instaladas en macOS. Si cambias a una que no lo esté,
libass la sustituye en silencio y el render sale distinto sin avisar — verifica
siempre con un frame.

## Opciones

```bash
--no-upper        respeta mayusculas y minusculas (default: TODO EN MAYUSCULAS)
--no-pop          quita la animacion de escala al aparecer
--max-words 3     grupos mas cortos (solo style group)
--width / --height   1080 / 1920 para la version vertical
```

## Posición y zona segura

`margin_v` en el preset es la distancia al borde inferior: 180px en `tiktok`
sobre 1080p. En vertical, **súbelo a 300+**: TikTok e Instagram tapan los
últimos ~250px con la UI de descripción y botones.

En horizontal, cuidado con la barra de progreso de YouTube al hacer hover.

## Editar el `.ass` a mano

Es texto plano. Cada línea `Dialogue:` es un evento:

```
Dialogue: 0,0:00:03.24,0:00:03.61,Cap,,0,0,0,,{\fscx88\fscy88\t(0,70,\fscx100\fscy100)}HOLA
```

`inicio,fin,estilo,,,,,,efecto+texto`. Las llaves son etiquetas de override:
`\fscx`/`\fscy` escalan, `\t(...)` anima, `\c&H00BBGGRR&` cambia color.

Los colores van en **&HAABBGGRR** — azul y rojo invertidos respecto a HTML.
Blanco `&H00FFFFFF`, ámbar `&H0000E5FF`, verde `&H004CFF00`.

Para corregir una palabra mal transcrita en todo el video, es más limpio
arreglarla en `transcript/words.json` y regenerar que editar el `.ass`.

## Quemar

Requiere `ffmpeg-full` (el ffmpeg normal de Homebrew ya no trae libass):

```bash
brew install ffmpeg-full
python3 $SKILL/scripts/fftool.py        # confirma que 'subtitles' aparece como OK
```

`captions.py` genera el `.ass` igual sin libass; solo no puede incrustarlo. Ese
`.ass` también se puede importar en DaVinci Resolve o CapCut.
