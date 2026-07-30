# Fase 4 — Ensamblado

**Meta:** ejecutar el `edl.json` aprobado y producir el corte base. Sin gate.

## Ejecutar

```bash
python3 $SKILL/scripts/cut.py edl.json --outdir build
```

Antes de renderizar de verdad, con un EDL largo conviene:

```bash
python3 $SKILL/scripts/cut.py edl.json --dry-run
```

que imprime el mapa de tiempos sin codificar nada.

Produce `build/rough.mp4` y `build/timemap.json`.

## Cómo funciona (importante para depurar)

Cada bloque `keep` se codifica por separado y luego se concatenan con copia de
streams, así el material se codifica **una sola vez**. Cada parte lleva un fade
de audio de 25 ms en los extremos: sin eso, cada muletilla eliminada deja un
clic audible.

`timemap.json` es el traductor entre el tiempo del original y el tiempo del
video final. Las Fases 5, 6 y 7 lo usan para colocar todo en su sitio. **Si
vuelves a correr `cut.py`, hay que regenerar los subtítulos y recomponer los
overlays**, porque el mapa cambió.

## Verificación

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 build/rough.mp4
```

1. ¿La duración coincide con lo estimado en `review.md`? Si no, el `edl.json`
   tiene bloques solapados o invertidos.
2. Mira 20 segundos alrededor de los tres cortes manuales más grandes. Los
   cortes de silencio nunca fallan; los de "toma repetida" a veces cortan una
   sílaba.
3. Escucha un corte de muletilla. Si hay clic, sube `FADE` en `cut.py`.

## Si un corte quedó mal

No re-hagas la fase entera. Ajusta ese bloque `keep` en `edl.json` y vuelve a
correr `cut.py` — son segundos por parte.

`state.json` → `phase: 5`.
