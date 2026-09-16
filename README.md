# ComunIA

Motor de triaje asistido por LLM para administradores de comunidades de
propietarios.

## Qué hace

ComunIA recibe incidencias procedentes de email, WhatsApp o teléfono y genera:

- categoría;
- prioridad (`critical`, `high`, `medium`, `low`);
- resumen de máximo 10 palabras;
- área responsable;
- justificación auditable;
- tokens, latencia y coste estimado.

Permite utilizar un modelo local mediante Ollama o un modelo externo de OpenAI,
comparar ambos y someter el resultado a validación humana. El histórico utiliza
la tasa de aprobación/corrección humana como indicador práctico de calidad por
proveedor.

## Estructura

```text
app/
  api/
  core/
  guardrails/
  llm/
  models/
  parsers/
  prompts/
  services/
dashboard/
data/
docs/
tests/
```

Consulta `docs/architecture.md` para la explicación completa.

## 1. Entorno virtual en WSL

Desde la raíz de ComunIA:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Configuración

```bash
cp .env.example .env
```

Edita `.env`.

Para Ollama necesitas tener el servicio local ejecutándose y disponer del modelo
indicado en `OLLAMA_MODEL`.

Para OpenAI debes añadir una API key válida en:

```text
OPENAI_API_KEY=
```

No subas `.env` a GitHub.

## 3. Backend

```bash
uvicorn app.main:app --reload
```

Documentación interactiva:

```text
http://localhost:8000/docs
```

Comprobación rápida:

```text
GET http://localhost:8000/api/v1/health
```

## 4. Dashboard

En otra terminal, con el mismo `.venv`:

```bash
streamlit run dashboard/app.py
```

## 5. Tests

```bash
pytest -q
```

Para cobertura:

```bash
pytest --cov=app --cov-report=term-missing
```

## Endpoints

- `POST /api/v1/triage`: procesa con un proveedor elegido.
- `POST /api/v1/compare`: compara Ollama y OpenAI.
- `GET /api/v1/incidents`: consulta incidencias guardadas.
- `PATCH /api/v1/incidents/{id}/review`: aprobación/corrección humana.
- `GET /api/v1/health`: estado del backend.

## Comunidad escrita en texto libre

El usuario puede escribir, por ejemplo:

```text
Av. Democracia 110
AVDA DEMOCRACIA 110
democracia 110
Demcraci 110
```

`CommunityService` normaliza el texto, exige un número de finca y realiza
matching aproximado contra `data/communities.json`.

Si no existe una coincidencia suficientemente fiable, la incidencia no continúa
al LLM y se solicita al usuario que corrija la referencia.

## Seguridad de datos

Los datos identificativos se validan y almacenan para gestionar la incidencia,
pero no se envían al LLM para calcular la urgencia.

Consulta `docs/ethics.md`.
