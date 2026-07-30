# Color

Este ffmpeg no trae LUTs 3D, pero `eq`, `curves` y `colorbalance` cubren de
sobra lo que un tutorial necesita. El objetivo no es "cine": es que la imagen se
vea limpia y **que la cámara y la captura de pantalla parezcan el mismo video**.

## El problema real

En un tutorial grabado con OBS hay dos fuentes muy distintas:

- **Captura de pantalla** — contraste alto, saturación alta, blancos puros.
- **Webcam** — más plana, más fría, con ruido en las sombras.

El corte entre ambas canta. **Ajusta la cámara para que se parezca a la
pantalla**, nunca al revés: degradar la captura hace ilegible el texto, que es
justo lo que el espectador vino a ver.

## Recetas

Aplícalas como `-vf` extra en la Fase 8.

### Cámara plana y fría (el caso más común)
```
eq=contrast=1.08:brightness=0.02:saturation=1.12,colorbalance=rs=0.04:bs=-0.04
```

### Levantar sombras sin lavar la imagen
```
curves=all='0/0.04 0.5/0.5 1/1'
```

### Piel apagada con poca luz
```
eq=brightness=0.05:saturation=1.15:gamma=1.06
```

### Captura de pantalla demasiado saturada
```
eq=saturation=0.94
```

### Quitar ruido de sombras en webcam barata
```
hqdn3d=2:1:2:3
```
Cuesta tiempo de render. Solo si el ruido se nota de verdad.

## Aplicar solo a una parte del video

Con `enable`, igual que los overlays:

```
eq=contrast=1.08:enable='between(t,0,45)'
```

Útil cuando el bloque de cámara y el de pantalla están en tramos distintos.

## Método

1. Saca un frame de cámara y uno de pantalla:
   ```bash
   ffmpeg -ss 5  -i build/composited.mp4 -frames:v 1 /tmp/cam.png
   ffmpeg -ss 90 -i build/composited.mp4 -frames:v 1 /tmp/screen.png
   ```
2. Míralos de verdad, uno al lado del otro.
3. Prueba el filtro **sobre el frame**, no sobre el video entero:
   ```bash
   ffmpeg -i /tmp/cam.png -vf "eq=contrast=1.08:saturation=1.12" /tmp/cam2.png
   ```
4. Cuando convenza, añádelo al render final.

Iterar sobre frames es instantáneo; iterar sobre un render de 10 minutos no.

## Límites

- Si la toma está sobreexpuesta, no hay filtro que la recupere. Regrabar.
- No subas la saturación más de ~1.2: los tonos de piel se vuelven naranjas.
- Cuidado con `brightness` alto en video con mucho negro — el ruido sube con él.
- Aplica color **una sola vez**, en el render final. Encadenar correcciones en
  varias pasadas acumula banding.
