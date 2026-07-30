# Fase 1 — Grabación

**Meta:** que el usuario grabe material que la Fase 3 pueda editar bien.
**Esta fase la ejecuta el humano.** Tu trabajo es la lista y el checklist.

## Escribe `01-shot-list.md`

Del outline aprobado, genera el orden real de grabación — que **no** es el orden
del video. Agrupa por setup para no reconfigurar OBS diez veces:

```markdown
# Lista de grabacion

## Bloque A — camara (mismo encuadre, misma luz)
- [ ] Gancho (0:00-0:15) — 3 tomas
- [ ] Cierre y CTA — 2 tomas

## Bloque B — pantalla
- [ ] Segmento 1: setup de OBS — pantalla + voz
- [ ] Segmento 2: ... 

## Bloque C — planos de recurso
- [ ] Manos escribiendo, 10s
- [ ] Plano general del escritorio, 10s
```

## Reglas que le ahorran horas a la Fase 3

Dile esto al usuario, explícitamente:

1. **Marca los errores con una palmada.** Si te equivocas, aplaude una vez, haz
   una pausa de 2 segundos y repite la frase completa desde el inicio. El pico
   de audio y el silencio son fáciles de encontrar después.
2. **No cortes la grabación entre tomas.** Un archivo largo es más fácil de
   editar que veinte cortos.
3. **Deja 2 segundos de silencio** al principio y al final. Da margen a los cortes.
4. **Repite la frase entera**, no la palabra suelta. Los cortes limpios caen en
   los silencios entre frases.
5. **Graba el gancho al final**, cuando ya sepas de qué va realmente el video.
6. **No arregles nada hablando** ("bueno, en realidad no es así"). Para, y repite.

## Ajustes de OBS

Si el usuario ya tiene una guía de OBS en el proyecto, **remítelo a ella** en vez
de repetirla. Lo mínimo que hay que verificar:

| Ajuste | Valor | Por qué |
|---|---|---|
| Formato | MKV, luego remux a MP4 | un MP4 se corrompe entero si se cae OBS |
| Resolución | 1920x1080 | |
| FPS | 30 | 60 solo si hay movimiento rápido |
| Audio | -18 a -10 dB, nunca 0 | headroom para normalizar después |
| Cámara | esquina, tamaño fijo | si se mueve, `reframe --preset stack` falla |

**Anota dónde queda la webcam en el encuadre** (x, y, ancho, alto en píxeles).
La Fase 7 lo necesita para el short vertical.

## Cierre de fase

Cuando el usuario diga que ya grabó:

1. Confirma que los archivos están en `raw/`.
2. Verifica que cada uno tiene pista de audio:
   `ffprobe -v error -show_streams raw/main.mp4 | grep codec_type`
3. Si grabó MKV, remuxea: `ffmpeg -i raw/x.mkv -c copy raw/x.mp4`
4. `state.json` → `phase: 2`
