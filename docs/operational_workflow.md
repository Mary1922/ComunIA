# Flujo operativo de incidencias

La vista **Gestión de incidencias** está pensada para secretaría y personal de
administración que necesita gestionar trabajo, no analizar modelos LLM.

## Objetivos de la vista

- ver cuántas incidencias siguen abiertas;
- localizar las pendientes de validación;
- destacar incidencias críticas o de prioridad alta;
- filtrar por estado, prioridad, categoría, comunidad, fecha y persona de contacto;
- abrir una incidencia concreta y consultar sus datos;
- registrar actuaciones con fecha, responsable y detalle;
- mantener una cronología legible hasta la resolución.

## Estados operativos

- `open`: incidencia registrada y todavía sin gestión iniciada;
- `in_progress`: existe una actuación de gestión en curso;
- `scheduled`: hay una cita o intervención programada;
- `waiting_provider`: se está esperando respuesta o actuación de un proveedor;
- `closed`: incidencia finalizada y expediente cerrado.

El valor histórico `resolved` se mantiene únicamente por compatibilidad con datos
antiguos y se presenta como `closed` en la interfaz. No se ofrece como estado
seleccionable en el flujo actual.

Estos estados son independientes de la revisión humana de la clasificación del
LLM. La separación evita mezclar la calidad del triaje con la evolución real de
la reparación.

## Ejemplo de cronología

1. **Registro de incidencia** — se comunica que la antena comunitaria no recibe
   señal.
2. **Aviso / contacto con proveedor** — se avisa a mantenimiento de antenas y se
   concierta cita para el martes a las 10:00.
3. **Visita del proveedor** — el técnico revisa la instalación y comunica que
   necesita una pieza.
4. **Pendiente de pieza o material** — el proveedor queda encargado de llamar
   para concertar una nueva cita.
5. **Resolución** — reparación completada y servicio restablecido.

## Búsqueda y seguimiento

La bandeja de gestión incorpora filtros combinables por estado operativo, prioridad, categoría, comunidad, fecha y persona de contacto. El selector de comunidad parte siempre del catálogo maestro de `data/communities.json`, aunque alguna comunidad todavía no tenga incidencias. Las actuaciones se muestran cronológicamente y, tras registrar una nueva, ComunIA confirma la operación y limpia el formulario para facilitar el siguiente registro.

Los teléfonos de contacto se almacenan como texto, pero el dominio exige exactamente 9 cifras numéricas para este prototipo orientado a España.

## Recuperación de validaciones pendientes

En **Supervisión IA > Histórico de incidencias**, una incidencia cuyo estado de
revisión sea `pending` muestra la acción **Validar incidencia ahora**. Esta acción
reutiliza el mismo flujo de revisión disponible tras el triaje inicial: la persona
supervisora puede aprobar la clasificación propuesta o corregir categoría,
prioridad, área, resumen y justificación. Tras guardar, la incidencia se actualiza
en el histórico sin necesidad de volver a registrarla.

## Previsualización de WhatsApp en modo demostración

Tras registrar una incidencia desde **Gestión de incidencias**, ComunIA ofrece la acción
**Preparar WhatsApp al contacto**. La aplicación compone un mensaje con la referencia
pública de la incidencia y el resumen ejecutivo generado por el triaje, pero no realiza
ningún envío real ni conecta con WhatsApp. La previsualización identifica de forma
explícita que se trata de un modo de demostración. Esta separación deja preparado el
punto de integración para una futura capa de notificaciones sin introducir riesgo sobre
los teléfonos sintéticos del conjunto de demo.

En **Supervisión IA**, el formulario **Nueva incidencia** permanece colapsado por defecto,
al igual que los históricos, para reducir ruido visual. Se abre manualmente cuando la
persona supervisora necesita registrar o comparar una incidencia nueva.
