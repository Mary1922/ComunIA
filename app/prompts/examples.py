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
                "Observación: hay una persona atrapada. "
                "Acción: requiere intervención inmediata. "
                "Resultado: ascensores con prioridad critical."
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
                "Observación: existe una entrada activa de agua. "
                "Acción: requiere intervención de mantenimiento. "
                "Resultado: danos_agua con prioridad high."
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
                "Observación: el portero automático está averiado. "
                "Acción: requiere reparación programable. "
                "Resultado: portero_automatico con prioridad medium."
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
                "Observación: se solicita una copia de un recibo. "
                "Acción: requiere gestión administrativa. "
                "Resultado: contabilidad con prioridad low."
            ),
        },
    },
]
