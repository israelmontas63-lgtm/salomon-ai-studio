# Capa 3: Razonamiento lógico y enjambre

Controlador: `cognicion/capas_inteligencia/layer_03_reasoning/__init__.py`

- `run_logical_swarm` — sub-agentes paralelos (premisa, coherencia, falacias, certidumbre)
- `ConsensusMatrix` — consenso ponderado → `proceed` | `hedge` | `revise`
- `cascade_reason` — lógica local + `enrich_turn` (respeta gate web del cortex)

Enlazado desde `cognicion/orquestador.py`. No toca cámara ni L7 `apply_supervision`.
