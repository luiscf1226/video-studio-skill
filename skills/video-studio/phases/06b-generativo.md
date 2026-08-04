# Fase 6b — Media generativa (OPCIONAL, de pago)

**Meta:** generar lo que ni el stock gratis ni HyperFrames pueden dar.
**No corre sola.** Solo si el usuario la pide explícitamente.

Pago por uso, sin suscripción: kie.ai → fal.ai → wavespeed, en ese orden de
precio. El script rutea al más barato que tenga API key y cae al siguiente si
ese proveedor falla.

## Cuándo SÍ vale la pena

| Uso | Por qué | Costo típico |
|---|---|---|
| **Miniatura de YouTube** | Necesitas una imagen que no existe en stock y que no es diseño plano | $0.05 |
| **Portadas de shorts** | 3 variantes para elegir | $0.15 |
| **Fondos para animaciones** | Una textura generada detrás de un gráfico de HyperFrames | $0.05 |
| **Planos conceptuales** | Lo específico que el stock genérico no cubre | $0.05 |
| **Animar una imagen fija** | Convertir una imagen buena en 5s de movimiento | $0.35 |

## Cuándo NO

- **Motion graphics.** HyperFrames es gratis, ilimitado, y da texto exacto,
  tiempos exactos y colores de marca. Ningún modelo generativo hace un contador
  animado de 0 a 10 con tu tipografía. Usar generación aquí es un downgrade.
- **B-roll común.** Pexels y Pixabay cubren la mayoría, gratis.
- **Cualquier cosa que ya funcione.** Esta fase es la excepción, no el default.

## Uso

```bash
python3 $SKILL/scripts/genmedia.py --list          # que modelos hay y a que precio
```

```bash
python3 $SKILL/scripts/genmedia.py \
  "miniatura: laptop mostrando una presentación 3D naranja, fondo oscuro, dramático" \
  --model gpt-image-2 --n 3 --budget 0.30 --outdir generated
```

Animar una imagen ya generada:

```bash
python3 $SKILL/scripts/genmedia.py \
  "la cámara se acerca lentamente, partículas flotando" \
  --model kling --seconds 5 --image generated/20260801-...png \
  --budget 0.50 --outdir generated
```

Ver todo lo generado:

```bash
python3 $SKILL/scripts/genmedia.py --gallery --outdir generated
open generated/index.html
```

## Los cuatro guardas

Son lo que evita que un prompt mal escrito vacíe la cuenta:

1. **`--budget` es obligatorio en la práctica** (def $1.00) y se comprueba
   **antes de cada llamada**, no solo al inicio. Si pides 20 imágenes con tope
   de $0.30, aborta antes de gastar el primer centavo.
2. **Confirmación explícita.** Imprime el costo estimado y espera respuesta.
   `--yes` la salta, pero solo úsalo cuando ya validaste el prompt.
3. **Descarga inmediata.** En kie.ai las URLs de salida **expiran a las 24
   horas**. El script baja el archivo al disco antes de dar nada por hecho.
4. **Registro de todo.** Cada generación deja fecha, prompt, modelo, proveedor,
   costo y rutas en `generated/generations.jsonl`. Los prompts son tuyos y
   quedan en tu disco.

## Precios sin verificar

El catálogo (`references/models.json`) marca cada precio con `verified`. Solo
GPT-Image-2 en kie.ai está confirmado ($0.05 a 2K). El resto son estimaciones y
el script lo advierte antes de gastar:

```
Costo est.  $1.400   (precio SIN VERIFICAR, puede variar)
```

**Confirma el precio en la web del proveedor antes de una tanda grande.** Los
precios de estos modelos cambian seguido.

## Añadir un modelo

Se edita `references/models.json`, no el código:

```json
{
  "alias": "mi-modelo",
  "tipo": "imagen",
  "descripcion": "para que sirve",
  "opciones": [
    { "provider": "fal", "id": "fal-ai/loquesea", "cost_usd": 0.03, "verified": false }
  ]
}
```

## API keys

```bash
export KIE_API_KEY='...'        # kie.ai — el mas barato
export FAL_KEY='...'            # fal.ai — el mas confiable
export WAVESPEED_API_KEY='...'  # wavespeed.ai — modelos raros
```

Basta con una. El script solo ofrece los modelos de los proveedores cuya key
esté puesta.

## Integrar el resultado

Las imágenes y videos generados entran al pipeline como cualquier otro asset:

```json
{ "type": "broll", "asset": "generated/20260801-kling-1.mp4",
  "start": 120.0, "end": 125.0, "fade": 0.3 }
```

Para miniaturas no hace falta EDL: el archivo se sube directo a YouTube.
