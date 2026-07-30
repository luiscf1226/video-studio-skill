# Muletillas en español — qué cortar y qué no

`analyze.py` clasifica en dos niveles. La distinción importa: en español la
mayoría de las muletillas son **palabras reales**, y borrarlas todas deja un
audio entrecortado y antinatural.

## Tier 1 — ruido no léxico (corte automático)

No significan nada. Se cortan sin preguntar.

```
eh  ehh  eeh  eee  ee  em  emm  ehm  mmm  mm  mmh  hmm  hm
uh  uhh  uhm  um  ah  ahh  aah  er  err  aja  ajam  mhm
```

También tier 1: la **repetición inmediata** de una palabra (`el el`, `que que`)
cuando el hueco entre ambas es menor a 0.7s. Se corta la primera.

## Tier 2 — palabras reales usadas como muletilla (decisión humana)

```
bueno   entonces   pues   digamos   tipo   verdad   cierto
obviamente   basicamente   literalmente   ok   okey   este   esto
o sea / osea   como que   es decir   por asi decirlo   no se   ya saben
```

Nunca se cortan solas. Criterio para decidir una por una:

| Cortar | Dejar |
|---|---|
| arranca la frase sin aportar: "**Bueno**, entonces abrimos OBS" | conecta ideas: "Listo, **entonces** ya podemos grabar" |
| se repite 3+ veces en el mismo minuto | es la única forma natural de decirlo |
| rellena mientras piensa | marca énfasis real |
| "**o sea**, es lo mismo que dije" | "**es decir**, 1080p" (aclara de verdad) |

Regla práctica: si al leer la frase sin la palabra **sigue significando lo
mismo y suena mejor**, córtala. Si suena telegráfico, déjala.

## Qué no tocar nunca

- **Muletillas dentro de una frase que ya va rápida.** Quitar más ritmo la
  vuelve atropellada.
- **La primera frase del gancho.** Ahí el corte se nota muchísimo. Si el gancho
  tiene muletillas, es mejor regrabarlo que coserlo.
- **Risas, suspiros y pausas expresivas.** Son personalidad, no ruido.

## Ajustar la agresividad

```bash
--min-gap 0.4    # mas agresivo con los silencios (default 0.6)
--min-gap 1.0    # mas conservador, deja respirar
--pad 0.12       # protege mas el ataque de cada palabra
```

`--pad` es un margen de **protección**: los silencios se recortan hasta ahí y no
más, para no comerse la consonante inicial de la siguiente palabra. Subirlo hace
los cortes más conservadores, nunca más agresivos.

## Añadir palabras

Edita `TIER1` y `TIER2_SINGLE` en `$SKILL/scripts/analyze.py`. Las frases de varias
palabras van en `TIER2_PHRASES` como tuplas ya normalizadas — sin tildes, en
minúscula y sin puntuación, porque así es como el script compara.
