# Datos sintéticos para la demo

ComunIA incluye `scripts/generate_demo_incidents.py` para poblar el entorno de demostración sin utilizar datos personales reales ni realizar llamadas a Ollama/Groq.

```bash
python scripts/generate_demo_incidents.py --count 50
```

El script conserva las incidencias ya existentes y añade hasta 50 registros sintéticos distribuidos entre las comunidades configuradas en `data/communities.json`. Genera nombres, viviendas y teléfonos ficticios de 9 cifras, distintos tipos de incidencia, prioridades, estados operativos, proveedores y cronologías de seguimiento.

La generación es reproducible mediante una semilla y evita duplicados si se ejecuta de nuevo con la misma configuración. Para retirar únicamente el lote demo generado con la semilla predeterminada:

```bash
python scripts/generate_demo_incidents.py --count 50 --remove-demo
```

`data/incidents.json` continúa fuera de Git mediante `.gitignore`; el objetivo es que los datos de demostración existan únicamente en el entorno local de la presentación.
