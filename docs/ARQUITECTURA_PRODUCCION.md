# Arquitectura de Producción — Salomón AI Studio

Jerarquía limpia (estilo Clean Architecture) sobre el árbol actual.
**SystemGuard** y el Golden State de cámara son inamovibles sin `AUTORIZADO`.

## Capas

```
┌─────────────────────────────────────────────────────────┐
│  Presentación                                            │
│  app.py · api/sbi/* (CLI) · studio/dist (PWA)            │
├─────────────────────────────────────────────────────────┤
│  Aplicación / Orquestación                               │
│  cerebro.py · cognicion/orquestador.py · esencia.py      │
├─────────────────────────────────────────────────────────┤
│  Dominio cognitivo                                       │
│  cognicion/cognitivo/*   (Dual: claridad, episodios)     │
│  cognicion/ejecutivo/*   (mercados, contenido, …)        │
│  cognicion/razonamiento · memoria · autonoma             │
├─────────────────────────────────────────────────────────┤
│  Seguridad (ISO 27001-oriented)                          │
│  SystemGuard.py · cognicion/seguridad/* · SBI-PRO        │
│  salomon_integrity_ledger.json · golden_snapshots/       │
├─────────────────────────────────────────────────────────┤
│  Infraestructura                                         │
│  settings.py · persistencia/ · data/ · render.yaml       │
└─────────────────────────────────────────────────────────┘
```

## Trazabilidad obligatoria

| Capa | Módulo | Endpoints |
|------|--------|-----------|
| Seguridad | `cognicion/seguridad/sbi_pro.py` | `/api/sbi/*` |
| Cognitiva | `cognicion/cognitivo/` | `/api/cognitivo/{estado,pre,correccion,consolidar}` |
| Ejecutiva | `cognicion/ejecutivo/` | `/api/ejecutivo/{estado,informe}` |
| Inmune | `SystemGuard.py` | boot + ledger |

Ninguna capa puede desactivar SystemGuard ni SBI-PRO.

## Gate pre-deploy

```bash
python scripts/system_integrity_check.py
```

- Exit `0` → PASS (apto para push con autorización a `main`)
- Exit `1` → FAIL (detener despliegue; ver `docs/INFORME_INTEGRITY_CHECK.md`)

## TDD del bloque

```bash
pytest tests/test_sbi_pro.py tests/test_ejecutivo.py tests/test_cognitivo_dual.py -q
```

## Maquetas UI

Viven en `docs/maquetas/` (no en la raíz del repo).
