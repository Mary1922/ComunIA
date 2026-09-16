"""Ejemplos Few-shot para guiar la clasificación del LLM."""

FEW_SHOT_EXAMPLES = [
    {
        "incident": "Hay una persona atrapada dentro del ascensor.",
        "output": {
            "category": "ascensores",
            "priority": "critical",
            "summary": "Persona atrapada dentro del ascensor requiere actuación inmediata",
            "department": "mantenimiento",
            "reasoning": (
                "Existe riesgo directo para una persona y se requiere "
                "intervención inmediata."
            ),
        },
    },
    {
        "incident": "Está entrando mucha agua en el garaje desde el techo.",
        "output": {
            "category": "danos_agua",
            "priority": "high",
            "summary": "Entrada activa de agua amenaza el garaje comunitario",
            "department": "mantenimiento",
            "reasoning": (
                "La entrada de agua está activa y puede provocar daños "
                "materiales relevantes."
            ),
        },
    },
    {
        "incident": "El portero automático no funciona desde ayer.",
        "output": {
            "category": "portero_automatico",
            "priority": "medium",
            "summary": "Portero automático averiado desde ayer necesita revisión técnica",
            "department": "mantenimiento",
            "reasoning": (
                "La avería requiere reparación pero no describe un riesgo "
                "inmediato para personas."
            ),
        },
    },
    {
        "incident": "Necesito una copia del último recibo de la comunidad.",
        "output": {
            "category": "contabilidad",
            "priority": "low",
            "summary": "Propietario solicita copia del último recibo comunitario",
            "department": "gestion_comunidad",
            "reasoning": (
                "Se trata de una gestión documental sin riesgo ni avería."
            ),
        },
    },
]
