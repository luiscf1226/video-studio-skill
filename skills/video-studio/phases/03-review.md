# Fase 3 — Plan de edición  ← la fase que decide la calidad del video

**Meta:** producir `review.md`, un `segments/segment-NN.md` por segmento y el
`edl.json` definitivo. **Termina en el gate más importante del pipeline.**

Nada se renderiza en esta fase. Solo se decide.

## Paso 1 — Detección automática

```bash
python3 $SKILL/scripts/analyze.py transcript/words.json \
    --emit-edl edl.json --source raw/main.mp4
```

Esto ya elimina el ruido no-léxico (`eh`, `mmm`, `uh`), las repeticiones y el
exceso de silencio. Es un **borrador**, no el edit final.

## Paso 2 — Lee el transcript completo

Lee `transcript/raw.srt` de principio a fin. La detección automática encuentra
ruido; solo tú encuentras lo que sobra. Busca:

- **Tomas repetidas.** Si dice lo mismo dos veces, casi siempre la última es la
  buena — ya se había calentado. Escúchalo por el transcript: la segunda suele
  ser más corta y directa.
- **Relleno estructural.** "Antes de empezar, déjenme decirles que…" —
  fuera. "Como les decía hace un momento" — fuera.
- **Divagaciones.** Un párrafo que no avanza la promesa del outline.
- **Autocorrecciones.** "Le das clic en… bueno, primero abre el menú" — se queda
  solo la versión correcta.
- **Muletillas tier2** (`bueno`, `o sea`, `pues`, `este`). Están en
  `analysis.json` marcadas para revisión. **Decide una por una.** Quitar todos
  los "bueno" deja un audio robótico y entrecortado; quita los que arrancan
  frase, deja los que dan ritmo. Ver `references/filler-words-es.md`.

## Paso 3 — Divide en segmentos

Un segmento = una idea del outline. Para cada uno escribe
`segments/segment-NN.md`:

```markdown
# Segmento 03 — Configurar el micrófono

**Fuente:** 04:12 → 06:30 · **Final estimado:** 1:48

## Transcript editado
> El texto que queda después de los cortes, para leerlo de corrido
> y confirmar que sigue teniendo sentido.

## Cortes
| Fuente | Motivo | Tier |
|---|---|---|
| 04:18.2-04:19.0 | "eh" | auto |
| 04:41.5-04:48.9 | toma repetida, se queda la segunda | manual |
| 05:02.1-05:03.4 | "o sea" que arranca frase | manual |

## B-roll
| Cuándo | Qué | Fuente |
|---|---|---|
| 04:55 | primer plano del micrófono | grabar, o Pexels "microphone studio" |

## Motion graphics
| Cuándo | Qué | Por qué |
|---|---|---|
| 05:20 | diagrama de la cadena de audio | se explica con palabras y no se entiende |

## Zooms
| Cuándo | Escala | Foco |
|---|---|---|
| 05:40-05:47 | 1.3 | el medidor de audio, esquina inferior izquierda |

## Color
Sombras levantadas +6, la cámara sale más fría que la pantalla.
```

## Paso 4 — El teaser

Si el outline marcó `[TEASER: ...]`, localiza ese momento en el transcript y
añade sus segundos al **inicio** del `edl.json`, como el primer bloque `keep` del
primer segmento. Tres a cinco segundos, sin audio explicativo, cortado seco.

## Paso 5 — Escribe `edl.json`

Formato completo en `references/edl-schema.md`. **Todos los tiempos en segundos
del video ORIGINAL.** Nunca tiempos de salida.

## Paso 6 — Escribe `review.md`

El resumen ejecutivo que el usuario aprueba:

```markdown
# Plan de edición

**Original:** 14:32 → **Final estimado:** 9:48 (33% recortado)

## Qué se quita
- 47 muletillas de ruido (automático)
- 3 tomas repetidas → 2:10
- 1 divagación en el segmento 4 → 0:48
- 38 silencios largos → 1:12

## Decisiones que necesito que confirmes
1. Segmento 4 (05:12-06:00): la explicación de códecs no aporta al objetivo.
   **Propongo quitarla entera.** ¿De acuerdo?
2. Hay dos versiones del cierre. Me quedo con la segunda, suena más segura.

## Motion graphics a crear (4)
| # | Segmento | Qué | Duración |
|---|---|---|---|
| 1 | 01 | título animado | 3s |

## B-roll a conseguir (3)
## Estructura final
| # | Segmento | Entra | Sale | Dura |
```

## Gate

Presenta `review.md` y **detente**. Resalta las decisiones que requieren su
criterio, no la lista completa de cortes automáticos.

Cuando apruebe: `state.json` → `phase: 4`, `gates.edl_approved: true`.

Si pide cambios, **edita `edl.json`**, regenera `review.md` y vuelve a preguntar.
