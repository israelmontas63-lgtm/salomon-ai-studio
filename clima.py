# -*- coding: utf-8 -*-
"""Shim de compatibilidad — implementación canónica en lib.clima."""
from lib.clima import *  # noqa: F403
from lib.clima import (  # noqa: F401
    PALABRAS_CLIMA,
    es_consulta_clima,
    extraer_ciudad,
    obtener_datos_clima,
    preparar_contexto_clima,
)
