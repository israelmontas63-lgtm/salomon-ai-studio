# Salomón AI: Protocolo Maestro de Ingeniería de Iconografía (FINAL)

## 1. Design Tokens (Especificaciones Técnicas)

```yaml
design_tokens:
  dimensions:
    canvas: 512
    safe_area: 0.82       # 18% margen de seguridad
    outer_ring: 0.05      # 5% grosor aro blanco
    gold_border: 0.035    # 3.5% grosor marco dorado
    ring_separation: 0.03 # 3% separación blanco↔dorado
    logo_scale: 0.58      # 58% ancho/alto
  colors:
    white_halo: "#FFFFFF"
    gold_frame: "#C9A227"
    metal_black: "#0A0A0A"
  rendering:
    contrast_ratio: 7.0
    interpolation: "lanczos"
    format: "png_high_res"
```

## 2. Restricciones de Validación (JSON)

```json
{
  "validation": {
    "mustRemainCentered": true,
    "allowDistortion": false,
    "allowCropping": false,
    "minimumContrastRatio": 7,
    "preserveAspectRatio": true,
    "responsiveScaling": true
  }
}
```

## 3. Reglas de Ejecución Técnica

- **Activo Maestro:** `255542.png` es la única fuente de verdad absoluta.
- **Técnica:** Escalado matemático mediante interpolación Lanczos. Prohibido dibujar el monograma SA mediante CSS/SVG.
- **Formatos requeridos:**
  - `android-chrome-192x192.png`
  - `android-chrome-512x512.png`
  - `apple-touch-icon.png` (180×180)
  - `mstile-150x150.png`
  - `favicon-32x32.png`
  - `favicon-16x16.png`
- **Cumplimiento:** Centralización exacta del monograma SA y texto «Salomón AI» sobre el eje geométrico del lienzo. Separación entre aro blanco y marco dorado = **3%**.

## 4. Despliegue

Exportar a `static/icons/`, actualizar `manifest.json`, desplegar a Render.
