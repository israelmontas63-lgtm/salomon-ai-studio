# -*- coding: utf-8 -*-
"""Shim de compatibilidad — implementación canónica en lib.web_search."""
from lib.web_search import *  # noqa: F403
from lib.web_search import (  # noqa: F401
    buscar_web,
    consultar,
    estado_conectividad,
    necesita_busqueda_web,
    responder_con_busqueda,
)
