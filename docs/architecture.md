# Arquitectura de ComunIA

## Objetivo

ComunIA clasifica comunicaciones recibidas por administradores de comunidades
de propietarios mediante un LLM local (Ollama) o un proveedor externo (Groq),
manteniendo validación estricta con Pydantic y revisión humana.

## Flujo principal

1. Streamlit recoge la incidencia.
2. Pydantic valida el contrato de entrada.
3. `CommunityService` identifica la comunidad contra `communities.json`.
4. Los datos personales y la dirección quedan fuera del prompt del LLM.
5. `TriageService` construye el prompt y selecciona el proveedor.
6. El proveedor devuelve JSON estructurado.
7. `response_parser.py` valida la salida con Pydantic.
8. Si falla el esquema, se solicita una reparación al LLM.
9. Se aplica un guardrail mínimo para riesgos críticos explícitos.
10. Se calculan tokens, latencia y coste.
11. El resultado se almacena en `incidents.json`.
12. El operador humano puede aprobar o corregir la clasificación.

## Separación de responsabilidades

- `api/`: transporte HTTP.
- `core/`: configuración, enums y excepciones.
- `models/`: contratos Pydantic.
- `prompts/`: instrucciones y ejemplos Few-shot.
- `llm/`: adaptadores de proveedores.
- `parsers/`: validación de la salida textual.
- `guardrails/`: reglas de seguridad deterministas.
- `services/`: lógica de negocio y orquestación.
- `dashboard/`: interfaz Human-in-the-loop.
- `tests/`: estabilidad y mocking.

## Decisión sobre el proveedor

El proveedor no forma parte de los datos permanentes de la incidencia.
`TriageRequest` contiene dos bloques conceptuales:

- `incident`: datos del reporte.
- `provider`: configuración de ejecución.

Esto permite procesar la misma incidencia con un proveedor o comparar ambos
sin modificar su identidad.

## Type-safety

Pydantic valida tanto la entrada como la clasificación del LLM. Además de tipos
y enums se comprueban reglas de negocio, por ejemplo:

- resumen de máximo 10 palabras;
- categorías cerradas;
- áreas cerradas;
- correspondencia categoría-área;
- teléfono con formato válido;
- campos inesperados prohibidos.


## Calidad de clasificación

La calidad no se infiere de que dos modelos coincidan. Se utiliza la revisión
humana como referencia práctica: el dashboard calcula, por proveedor, cuántas
clasificaciones revisadas fueron aprobadas sin cambios y cuántas necesitaron
corrección. Esta métrica se interpreta junto con coste y latencia.


## Proveedor externo Groq

La integración externa usa la API HTTP compatible con OpenAI de Groq, pero
ComunIA no depende del SDK de ningún proveedor. `GroqProvider` implementa el
mismo contrato `BaseLLMProvider` que `OllamaProvider`.

El modelo por defecto es `qwen/qwen3.8-27b`, configurable en `.env`. Se utiliza
Structured Outputs con JSON Schema estricto y Pydantic vuelve a validar el
resultado, manteniendo una segunda barrera type-safe independiente del proveedor.
