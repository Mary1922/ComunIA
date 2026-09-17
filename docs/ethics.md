# Ética, privacidad y gobernanza del dato

## Supervisión humana

ComunIA es una herramienta de apoyo. La clasificación inicial queda en estado
`pending` hasta que una persona la aprueba o corrige.

## Minimización de datos

Nombre, teléfono, vivienda y comunidad se recogen porque permiten identificar
el origen del reporte y evitar comunicaciones anónimas o imposibles de verificar.

Sin embargo, estos datos no son necesarios para calcular la urgencia y por ello
no se incluyen en el prompt enviado al LLM. El modelo recibe únicamente la
descripción de la incidencia.

## Sesgos

El prompt obliga a ignorar género, raza, origen, nacionalidad, nivel
socioeconómico, barrio y ubicación inferida al determinar la prioridad.

La dirección se usa para identificar la comunidad administrada, no para elevar
o reducir la gravedad.

## Proveedor externo

El proveedor externo Groq supone una transferencia del texto de la incidencia fuera
del equipo local. Antes de un uso real deben revisarse las obligaciones de
protección de datos, contratos con proveedores y política de conservación.

El prototipo configura las llamadas externas sin almacenamiento de la respuesta
cuando el proveedor permite esa opción.

## Limitaciones

- Un LLM puede clasificar incorrectamente aunque el JSON sea válido.
- Los guardrails cubren únicamente un conjunto limitado de riesgos explícitos.
- El fuzzy matching debe revisarse al ampliar mucho el catálogo de comunidades.
- El sistema no sustituye protocolos de emergencia ni decisiones profesionales.


## Uso de Groq Free tier

El prototipo prioriza una capa gratuita para evitar coste económico durante el
desarrollo. Los límites del proveedor deben tratarse como una restricción de
servicio y los errores 429 se gestionan mediante reintentos con backoff.

Aunque el proveedor sea gratuito durante el prototipo, se mantiene una estimación
de coste basada en la tarifa pública por tokens para poder evaluar escalabilidad.

## Calidad y trazabilidad humana

La comparación entre modelos no se considera una validación por consenso: dos LLM
pueden coincidir y estar equivocados. La métrica de calidad se calcula únicamente
cuando una persona supervisora fija una categoría y prioridad de referencia.

Los ficheros de ejecución `data/incidents.json` y `data/comparisons.json` pueden
contener datos de contacto, por lo que se excluyen del repositorio Git. Para una
implantación real debe sustituirse el almacenamiento JSON por un sistema con control
de acceso, cifrado y política explícita de conservación.
