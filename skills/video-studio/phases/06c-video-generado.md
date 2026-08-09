# Fase 6c — Video 100% generado (marca / sizzle, OPCIONAL, de pago)

**Meta:** un video corto (15-60s) armado enteramente con IA — sin metraje real —
para piezas de marca, anuncios, o "sizzle reels" donde no hay nada que grabar.
**Opt-in:** solo corre si el usuario la pide explícitamente, igual que 6b —
esa parte del nombre "fase" es lo único que comparte con el resto del pipeline.

**Independiente del pipeline de 9 fases.** Esto NO es como las fases 0-8: no
necesita `state.json`, no necesita `init.sh`, no necesita una carpeta de
proyecto con la estructura de `raw/`/`segments/`/`build/`, y no depende de que
ninguna otra fase haya corrido antes. Los tres scripts de esta fase
(`genmedia.py` para generar, `splice_insert.py` para arreglar/extender,
`upscale.py` para escalar, más `labels_overlay.py` para texto) son
herramientas de linea de comandos normales: les das archivos, te dan archivos.
Puedes usarlos:

- **Para armar un video desde cero** — un storyboard, sin grabación, sin
  proyecto de video-studio de por medio.
- **Para agregar una escena o arreglar un tramo de un video que ya existe**,
  sea de este skill, de otro pipeline, o un archivo que alguien te mando.
- **Uno a la vez, en cualquier orden, sin las demas.** Si solo necesitas
  `splice_insert.py` para empalmar un clip, usalo solo. No hace falta pasar
  por generacion, ni por escalado, ni por rotulos, ni por ninguna fase
  anterior del pipeline.

Distinta de 6b: 6b genera **assets sueltos** (una miniatura, un fondo) para
insertar en un video ya editado a partir de metraje real, dentro del pipeline
de 9 fases. 6c (y sus scripts) sirven igual de bien sueltos, para cualquier
video generado o existente, adentro o afuera de este skill.

## La lección más cara: nunca regeneres la toma completa para arreglar un tramo

Un modelo de texto-a-video que narra varias escenas en una sola toma continua
de 20-30s cuesta $10-15+ por corrida. Si un tramo de 3-4 segundos sale mal
(una cara rara, un objeto raro, lo que sea), la tentación es volver a correr
todo el prompt con una palabra cambiada. **No hagas eso.** Genera un clip corto
e independiente SOLO para ese tramo (unos 4s, a menudo menos de $2), y
empálmalo con un crossfade usando `splice_insert.py` — ver más abajo. Esto es
lo que de verdad reduce el gasto en este tipo de proyecto, más que cualquier
elección de modelo.

## Guía de costos — qué modelo usar y cuándo

Precios completos con notas de "verificado sí/no" viven en
`references/models.json` (es lo que lee `genmedia.py --list`). Resumen:

| Necesitas | Modelo | Costo | Por qué |
|---|---|---|---|
| Toma continua larga, texto a video, narra varias escenas sin cortes | `seedance-2.5` | $0.473/s @720p, $0.2205/s @480p | El único de esta lista pensado para "una sola toma que recorre varias escenas". Tope 720p — escala después si necesitas 1080p. |
| Video corto de una sola escena, 1080p, sin escalar después | `ltx-fast` | $0.04/s @1080p nativo | Bastante más barato en total que generar 720p + escalar, **si** el estilo te sirve (no probado para look cinematográfico fotorrealista — probar barato antes de comprometerse). |
| Animar una imagen ya buena (foto, ilustración) | `kling` (2.5) o `kling-3` | ~$0.07/s · ~$0.11/s | `kling-3` es más nuevo, reportado con mejor calidad a 720p y más caro; ninguno de los dos está verificado en fal.ai directamente. |
| B-roll corto y desechable | `seedance` (v1, no 2.5) | ~$0.06/s | Imagen a video, rápido y barato. |
| Explorar barato antes de comprometerte a un modelo caro | `wan`, `hunyuan` | ~$0.05/s · ~$0.075/s | Sin verificar en fal.ai directamente (precios de agregador). Buenos candidatos para una prueba de $0.20-0.30 antes de decidir con qué modelo hacer la toma final. |
| 1080p nativo, más calidad que `ltx-fast` | `ltx-pro` | ~$0.10/s | Sin verificar; `ltx-fast` SÍ está verificado en fal.ai — probar esa primero. |
| La mejor calidad posible, presupuesto no es problema | `veo` | ~$0.40/s | El más caro con diferencia; resérvalo para el hero shot final si todo lo demás ya está aprobado. |
| Escalar cualquier cosa a 1080p después de generarla más barata | `upscale.py` (Topaz) | $0.01-0.02/s de la FUENTE | Casi siempre más barato que generar nativo en alta resolución — genera barato, escala al final. |
| Música de fondo / SFX | la skill `media-use` si está instalada | **$0** | Catálogo gratis de HeyGen (login OAuth, sin tarjeta). Ver "Audio" más abajo — nunca pagues por esto si esa skill está disponible. |

Catálogo completo (16 modelos a la fecha) en `references/models.json` —
`genmedia.py --list` lo imprime con precio y si tiene la API key puesta. Cada
entrada dice `verified: true` solo si el precio viene confirmado directo de
la página del modelo en fal.ai; todo lo demás es estimación de un agregador
de terceros y puede estar desactualizado — revísalo antes de una tanda grande.

**Catálogo completo y actualizado de fal.ai (no solo lo que está en
`models.json`):** [fal.ai/explore/search?categories=text-to-video](https://fal.ai/explore/search?categories=text-to-video).
Ahí aparecen modelos nuevos antes de que alguien los agregue aquí, y el precio
mostrado ahí siempre es el real — es la fuente de verdad para confirmar
cualquier cifra de esta tabla o de `models.json`, y el primer lugar donde
buscar si necesitas algo que no está en el catálogo (otro estilo, otra
relación de aspecto, un modelo más nuevo). Si agregas uno al catálogo,
verifica el precio ahí mismo antes de poner `verified: true`.

**Regla práctica de ahorro:** arranca SIEMPRE con una prueba de 4-5s en 480p
($1-2) antes de comprometerte a la toma completa en 720p. Un prompt mal
calibrado a $12 es un prompt mal calibrado a $2 que puedes iterar tres veces
por el mismo dinero.

## Flujo

Los pasos de abajo se leen en orden porque asi se armo el proyecto donde nacio
esta fase, no porque cada uno dependa del anterior. `splice_insert.py`,
`labels_overlay.py` y `upscale.py` funcionan sobre CUALQUIER archivo de video
— generado con `genmedia.py`, grabado, descargado, o de otro pipeline
completamente distinto. Si lo unico que necesitas es empalmar dos clips que ya
tienes, saltate directo al paso 2 y usa `splice_insert.py` solo.

### 1. Genera la toma base

```bash
export FAL_KEY='...'
python3 $SKILL/scripts/genmedia.py \
  "tu prompt cinematografico completo aqui" \
  --model seedance-2.5 --seconds 26 --budget 15.00 --outdir generated
```

Escribe el prompt completo en un archivo de proyecto (no solo en la terminal)
— lo vas a necesitar de nuevo si algo sale mal y decides regenerar solo un
tramo con una variante del mismo prompt.

**Nunca mandes logos ni capturas de marca como imagen de referencia** al
generar. Los filtros de copyright de los modelos (ByteDance, entre otros)
rechazan la salida si reconocen una marca — no se cobra el rechazo, pero
perdiste tiempo. Todo lo que necesite ser exacto (logo, texto de UI, colores
de marca) se compone DESPUÉS, sobre metraje generado que es solo geometría
abstracta. Ve el punto 3.

### 2. Si un tramo salió mal: clip corto + `splice_insert.py`, no regenerar todo

```bash
# genera solo el reemplazo (4s, mismo estilo, prompt mas especifico para ese tramo)
python3 $SKILL/scripts/genmedia.py "..." --model seedance-2.5 --seconds 4 \
  --budget 2.00 --outdir generated

# empalmalo con un crossfade, reemplazando el tramo malo
python3 $SKILL/scripts/splice_insert.py \
  generated/toma-base.mp4 generated/reemplazo.mp4 \
  --at 3.75 --until 4.35 --crossfade 0.5 \
  --out generated/toma-arreglada.mp4
```

El mismo script sirve para **añadir** una escena nueva en vez de reemplazar
una mala — omite `--until` y el clip se inserta extendiendo la duración total
en lugar de sustituir un tramo. Lee el docstring de `splice_insert.py` para la
matemática exacta de duración (por qué el punto de corte y el offset del
crossfade deben coincidir para que no se repita ni se pierda contenido).

### 3. Compón la marca real encima de la geometría abstracta

Si le pediste al modelo una pantalla de teléfono / laptop como "solo
geometría abstracta, sin texto, sin logos" (que es lo que hay que pedirle,
ver punto 1), el resultado tiene un rectángulo o tarjeta en blanco donde debe
ir tu UI real. Dos formas de resolverlo, de más a menos esfuerzo:

- **Tracking cuadro por cuadro** (OpenCV): detecta la región (color, contraste)
  en cada frame, sigue su movimiento/perspectiva, deforma tu captura de
  pantalla real dentro de esa región. Esto es trabajo a medida por proyecto —
  no hay un script genérico aquí porque la heurística de detección cambia
  según qué tan predecible sea la escena (una pantalla fija es fácil; una
  pantalla que gira en 3D con la mano es mucho más trabajo). Si tu escena es
  razonablemente estable, esto vale la pena: el resultado es indistinguible
  de metraje real con tu marca.
- **Tarjeta final compuesta** (`overlay.py`, ya en este skill): en vez de
  intentar que la marca aparezca DENTRO de la toma generada, la toma generada
  termina en un plano neutro (por ejemplo, la cámara entra a la pantalla hasta
  que todo el cuadro es un color sólido), y ahí empalmas un cierre 100%
  compuesto con tus assets reales — logo, capturas, texto — sin nada generado
  de por medio. Mucho menos trabajo, y es donde SÍ importa que el texto/logo
  salga exacto.

### 4. Rótulos en pantalla (año, época, nombre de sección, lo que sea)

```bash
python3 $SKILL/scripts/labels_overlay.py video.mp4 cues.json --out labeled.mp4
```

Intenta `drawtext` primero (rápido, con fundido animado); si tu `ffmpeg` no
trae freetype (común en el `ffmpeg` de Homebrew — mismo problema que impide
quemar subtítulos, ver Requirements en `SKILL.md`), cae automáticamente a
componer las etiquetas como PNG y hacer un solo `overlay` — más lento de
programar pero sigue siendo rápido de renderizar SI compones una vez, nunca
si encadenas un overlay por etiqueta (encadenar N overlays con fundido tomó
20+ minutos en un clip de 49s en pruebas reales; la version de un solo pase
tomó menos de un minuto). El script ya hace esto bien; no lo reimplementes
peor.

### 5. Audio

Si tienes la skill `media-use` instalada, úsala — su catálogo gratis de
HeyGen (OAuth, sin tarjeta) da música y SFX reales sin costo, y ya sabe
mezclar capas (cama musical + SFX por escena) con `ffmpeg`. Es virtualmente
siempre la opción correcta antes de considerar generación de audio de pago.

Solo si esa skill no está disponible y necesitas algo muy específico que su
catálogo no tenga, `minimax-music` en `models.json` es la opción de pago más
barata encontrada (~$0.03/generación) — pero es la excepción, no el punto de
partida.

### 6. Sube la resolución al final, no al principio

```bash
python3 $SKILL/scripts/upscale.py generated/toma-final.mp4 \
  --factor 1.5 --model Proteus --out final/hero_1080p.mp4 --budget 1.00
```

## Gotchas de generación paralela

Si vas a generar varios clips (por ejemplo uno por escena) y te tienta
lanzarlos en paralelo para ahorrar tiempo de espera: **cuidado con scripts que
escriben a una ruta de salida fija.** Si dos llamadas paralelas descargan a
`salida.mp4` sin importar cuál escena están generando, la segunda sobreescribe
a la primera antes de que cada una renombre su propio resultado, y terminas
con contenido mezclado bajo el nombre equivocado (pasó en producción — costó
tiempo recuperar los clips correctos). `genmedia.py` ya usa nombres con sello
de tiempo por generación y no tiene este problema; si escribes tu propio
script de generación, dale a cada llamada un nombre de salida único desde el
principio, o simplemente corre las generaciones una por una.

## Los mismos cuatro guardas de la fase 6b aplican aquí

`--budget` por corrida, confirmación explícita, descarga inmediata, y
registro completo en `generations.jsonl`. Ve `06b-generativo.md` si no los
has leído.
