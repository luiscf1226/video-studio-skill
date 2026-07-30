# Fase 0 — Idea y outline

**Meta:** convertir una idea vaga en un guion grabable, para YouTube largo y para
un short vertical. **Termina en un gate: el usuario aprueba antes de grabar.**

## Antes de escribir

Pregunta solo lo que no puedas deducir:

1. ¿Tema y qué aprende el espectador exactamente?
2. ¿Duración objetivo del video largo? (8-12 min es lo normal para tutorial)
3. ¿Nivel del público — principiante total o ya sabe lo básico?
4. ¿Hay algo que mostrar en pantalla (código, una app, un proceso)?

Si el usuario ya tiene un guion o notas en el directorio, **léelas primero** y
propón mejoras en vez de empezar de cero.

## Escribe `00-outline.md`

```markdown
# <Titulo de trabajo>

## Promesa
Una frase: que sabra hacer el espectador al terminar.

## Gancho (0:00-0:15)
El texto exacto de las primeras 3 frases. Sin "hola, bienvenidos a mi canal".
Empieza por el resultado o por el problema.

## Teaser (0:15-0:25)
Que plano del final se muestra aqui para enganchar. Marcalo como
`[TEASER: <descripcion>]` — la Fase 3 lo convierte en un corte real.

## Segmentos
| # | Titulo | Min | Que se muestra | Grafico / b-roll |
|---|--------|-----|----------------|------------------|
| 1 | Setup  | 1.5 | pantalla OBS   | diagrama de flujo |

## Cierre y CTA
Una sola llamada a la accion. No tres.

## Short vertical (30-45s)
Que segmento se recorta, el gancho reescrito para 9:16, y el texto en pantalla.
El short NO es el video largo acortado: es una idea completa por si sola.

## Titulos candidatos
Cinco. Marca tu favorito.

## Miniatura
Que se ve, que texto lleva (maximo 4 palabras).
```

## Reglas de guion

- El gancho promete un resultado concreto, no un tema.
- Un segmento = una idea. Si un segmento necesita "y también", pártelo.
- Marca `[MOSTRAR: ...]` donde haya que enseñar pantalla, y `[GRAFICO: ...]`
  donde un dibujo explique mejor que las palabras. La Fase 5 los renderiza.
- Escribe como se habla. Frases cortas. Si no lo puedes decir en voz alta de
  corrido, reescríbelo.

## Gate

Presenta el outline y **detente**. Pregunta explícitamente si lo aprueba o qué
cambiaría. Solo cuando diga que sí:

- `state.json` → `phase: 1`, `gates.outline_approved: true`
