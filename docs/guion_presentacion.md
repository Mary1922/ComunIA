# Guion de presentación · ComunIA

## Presentación oral breve — 2 a 3 minutos

> **Duración objetivo: ~2:15–2:30 min.**

Hola. Mi proyecto se llama **ComunIA** y es una aplicación para la gestión inteligente de incidencias en comunidades de propietarios.

El problema que intenta resolver es muy cotidiano: una administración de fincas recibe avisos por teléfono, correo o WhatsApp en texto libre, y después tiene que decidir qué ocurre, qué urgencia tiene, a qué área corresponde y hacer seguimiento hasta que se resuelve.

ComunIA automatiza la primera parte de ese proceso mediante inteligencia artificial, pero mantiene siempre la decisión final bajo supervisión humana.

La aplicación tiene **dos modos de trabajo**.

El primero es **Gestión de incidencias**, pensado para administración o secretaría. Permite registrar avisos, consultar una bandeja filtrable, ver prioridades y categorías, y mantener un histórico cronológico de llamadas, citas, visitas de proveedores y actuaciones hasta cerrar la incidencia. También incorpora una simulación de WhatsApp para mostrar cómo se podría informar automáticamente al vecino sin realizar ningún envío real durante la demo.

El segundo es **Supervisión IA**. Aquí se puede ejecutar el triaje con dos proveedores: **Gemma 3 4B en local mediante Ollama** y **Qwen 3.8 27B mediante Groq**. La aplicación compara clasificación, latencia, tokens y coste de referencia, y la calidad se mide contra una validación humana, no simplemente por coincidencia entre modelos.

A nivel técnico, el backend está desarrollado con **FastAPI** y utiliza **Pydantic** para validar estrictamente las entradas y las salidas de los modelos. El prompt incluye Few-shot, control de sesgos y una estructura ReAct auditable basada en observación, acción y resultado. También existe retry y backoff para el proveedor externo y una batería actual de **35 tests automatizados**.

En resumen, ComunIA no se limita a clasificar una incidencia: combina **IA, validación humana y gestión operativa** en un único flujo.

A continuación, en el vídeo, mostraré el funcionamiento completo de la aplicación.

---

# Orden recomendado para el vídeo de demostración

El vídeo debe enseñar producto, no explicar demasiado código. Un recorrido de **4–6 minutos** es suficiente.

## 1. Abrir ComunIA

Mostrar brevemente la portada y los dos modos:

- Gestión de incidencias.
- Supervisión IA.

Empieza por **Gestión de incidencias** y enseña durante unos segundos el panel operativo con los KPIs. Es la mejor imagen para explicar que ComunIA no es solo un clasificador, sino una herramienta de trabajo para una administración de fincas.

Frase sugerida:

> “He separado el trabajo diario de administración de la parte técnica de supervisión de los modelos.”

## 2. Gestión de incidencias

Abrir **Registrar nueva incidencia** y crear un caso claro, por ejemplo:

> “No se recibe señal de televisión en ninguna vivienda de la comunidad desde esta mañana.”

Mostrar:

- comunidad;
- contacto;
- teléfono validado;
- clasificación generada;
- número amigable `Incidencia X-2026`;
- confirmación de registro;
- previsualización de WhatsApp en modo demo.

## 3. Bandeja y seguimiento

Abrir **Bandeja de incidencias**.

Mostrar rápidamente filtros por comunidad, categoría, prioridad o estado.

Seleccionar la incidencia recién creada y abrir **Seguimiento de la incidencia**.

Registrar una actuación, por ejemplo:

> “Avisado mantenimiento de antenas. Cita concertada para mañana a las 10:00.”

Mostrar que aparece cronológicamente y que se puede modificar el estado operativo.

## 4. Supervisión IA

Cambiar a **Supervisión IA**.

Abrir el histórico y seleccionar una incidencia pendiente de revisión.

Mostrar:

- botón de validación humana;
- aprobar o corregir la clasificación.

## 5. Comparación Ollama vs Groq

Seleccionar una incidencia que todavía no se haya comparado y pulsar:

> **Comparar Ollama vs Groq ahora**

Mostrar primero los dos resultados lado a lado y después, solo durante unos segundos, las métricas de rendimiento:

- categoría y prioridad;
- resumen ejecutivo;
- trazabilidad ReAct;
- latencia;
- tokens;
- coste de referencia.

No detenerse demasiado en los números: el objetivo es demostrar que existen y se registran.

## 6. Calidad y cierre

Mostrar brevemente:

- validación humana de la comparación;
- calidad acumulada;
- histórico de comparaciones.

Cerrar con una frase corta:

> “ComunIA permite pasar de un aviso desestructurado a una incidencia clasificada, validada y gestionada hasta su cierre, manteniendo la IA siempre bajo supervisión humana.”

---

## Qué evitar en el vídeo

- No recorrer todos los filtros uno por uno.
- No enseñar claves API ni `.env`.
- No dedicar tiempo a explicar cada archivo del repositorio.
- No esperar a que Ollama responda en silencio: puedes explicar en una frase que es el modelo local mientras procesa.
- No intentar demostrar todas las incidencias sintéticas; basta con enseñar que la bandeja está poblada.
- No hacer un WhatsApp real: la simulación está diseñada precisamente para la demo.
