# Sistema visual de ComunIA

## Objetivo

El dashboard adopta una estética profesional, urbana y sostenible para reforzar el contexto de gestión de comunidades de propietarios sin competir con la información operativa.

## Paleta

- Verde principal: `#2E7D5A`
- Verde oscuro: `#1F5F46`
- Verde suave: `#EAF5EF`
- Acento: `#4CAF7D`
- Texto principal: `#17211C`
- Fondo claro: `#F4FAF6`

El verde funciona como guiño a sostenibilidad y eficiencia, mientras los fondos neutros mantienen contraste y legibilidad.

## Tipografía

La interfaz usa **Manrope** mediante Google Fonts. Si el recurso remoto no está disponible, el navegador utiliza una sans-serif del sistema como fallback.

## Imagen de fondo

Foto: **Corentin Jaunault / Unsplash**  
Página: https://unsplash.com/photos/modern-apartment-buildings-with-a-green-courtyard-8Li3kSPoeo4

La fotografía muestra edificios residenciales modernos alrededor de un espacio verde comunitario. Se aplica una capa translúcida clara para que la fotografía aporte contexto sin perjudicar la lectura del dashboard.

La página de la imagen indica que es gratuita bajo la **Unsplash License**. La atribución no es obligatoria bajo esa licencia, pero ComunIA la mantiene en el pie del dashboard como buena práctica.

## Componentes

El sistema visual se concentra en `dashboard/assets/style.css` y mantiene `dashboard/app.py` enfocado en la lógica de interfaz. Se personalizan cabecera, sidebar, formularios, botones, métricas, tarjetas, estados, expanders, tablas y footer.

Los estados críticos conservan colores semánticos propios (rojo/naranja/verde) para evitar que la paleta corporativa oculte información relevante de urgencia.

## Localización de la interfaz

La capa de presentación traduce los valores internos sin modificar los contratos del backend. Por ejemplo, `critical`, `danos_agua` y `pending` siguen siendo los valores type-safe utilizados por Pydantic y por la API, mientras que la interfaz muestra `Crítica`, `Daños de agua` y `Pendiente de revisión`.

## Referencia pública de incidencias

El identificador UUID se conserva como identificador técnico interno. En el histórico, el dashboard genera una referencia pública más legible, con numeración cronológica independiente por año, por ejemplo `Incidencia 1-2026`, `Incidencia 2-2026`. Esta referencia es una capa de presentación y no sustituye el UUID del backend.

## Jerarquía visual de prioridad

La prioridad se comunica también mediante color: rojo intenso para crítica, rojo suave para alta, amarillo para media y verde para baja. El resumen de máximo diez palabras se presenta como un bloque ejecutivo destacado para facilitar el escaneo visual por parte de la persona supervisora.

## Referencia pública de comparaciones

El histórico de comparaciones aplica el mismo criterio de legibilidad: el UUID continúa siendo el identificador técnico interno, mientras que la interfaz muestra referencias cronológicas como `Comparación 1-2026`, `Comparación 2-2026`, etc. El histórico ofrece además un selector para consultar una comparación concreta sin exponer identificadores largos al usuario final.

## Densidad y cabecera

La cabecera principal se mantiene como elemento de identidad, pero con una altura reducida para que el formulario de nueva incidencia aparezca antes en pantalla. El encabezado nativo de Streamlit se deja visualmente transparente para evitar que una franja translúcida se superponga al contenido durante el desplazamiento.

Las tarjetas de prioridad, categoría y área usan un componente compacto propio y mantienen una altura visual equivalente al resumen ejecutivo, mejorando la densidad de información sin sacrificar legibilidad.
