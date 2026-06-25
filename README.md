# LinkedIn AI Automator

Sistema multi-agente para investigar papers recientes de arXiv, filtrarlos por relevancia semantica y generar borradores de posts de LinkedIn con un LLM configurable. Incluye frontend React, backend FastAPI, persistencia en Postgres y soporte para multiples proveedores LLM.

## Que Hace

El flujo principal ejecuta cuatro agentes:

- `Researcher`: consulta arXiv segun categorias configurables.
- `Curator`: filtra papers por embeddings e intereses semanticos.
- `Writer`: genera el contenido de LinkedIn con el LLM configurado.
- `Reviewer`: revisa el borrador para detectar claims riesgosos o problemas basicos.

Desde el frontend puedes configurar temas, categorias, criterios de busqueda, tipo de contenido, foco del post e instrucciones de estilo. Tambien puedes regenerar el post actual con una instruccion puntual sin repetir la investigacion completa.

## Stack

- Backend: `FastAPI`, `Pydantic`, `SQLModel`, `LangGraph`, `LangChain tools`.
- Frontend: `Vite`, `React`, `TypeScript`, `Tailwind CSS`.
- Base de datos: `Postgres 16`.
- NLP: `sentence-transformers` para embeddings.
- LLMs: adapters internos para `LMStudio`, `OpenAI`, `Google Gemini`, `Anthropic Claude` y `Ollama`.
- Infra local: `Docker Compose`.

## Arquitectura

```text
Frontend React
    |
    | POST /api/generate
    v
FastAPI Backend
    |
    v
LangGraph workflow
    |
    +--> Researcher Agent -> arXiv API
    +--> Curator Agent    -> Embeddings filter
    +--> Writer Agent     -> LLM provider factory
    +--> Reviewer Agent   -> Review heuristics
    |
    v
Postgres
```

El estado del workflow vive en `src/state.py`. Los agentes no guardan estado interno; reciben `WorkflowState` y devuelven mutaciones. Las integraciones externas se exponen como tools en `src/tools/`.

## Estructura Del Repositorio

```text
apps/
  backend/              # FastAPI app, DB models, Dockerfile y SQL init
  frontend/             # Vite + React UI
config/
  filter_profile.json   # Perfil default para filtrado semantico
scripts/                # Scripts locales para correr piezas del pipeline
src/
  agents/               # Nodos del workflow multi-agente
  filtering/            # Embeddings y scoring semantico
  generation/           # LLM clients y generador LinkedIn
  ingestion/            # Cliente arXiv
  tools/                # Tools usadas por agentes
tests/                  # Tests unitarios e integracion ligera
```

## Requisitos

- Docker y Docker Compose.
- Python 3.12 si vas a correr tests o scripts fuera de Docker.
- Node.js 20.x si vas a trabajar el frontend fuera de Docker.
- Un proveedor LLM disponible:
  - LMStudio local o remoto.
  - OpenAI con API key.
  - Anthropic con API key.
  - Google Gemini con API key.
  - Ollama local o remoto.

## Configuracion

1. Crea tu archivo local de entorno:

```bash
cp .env.example .env
```

2. Ajusta el proveedor LLM en `.env`.

### LMStudio

```env
LLM_PROVIDER=lmstudio
LLM_MODEL=openai/gpt-oss-20b
LLM_BASE_URL=http://host.docker.internal:1234/v1
```

### OpenAI

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

### Anthropic

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-haiku-latest
ANTHROPIC_API_KEY=...
```

### Google Gemini

```env
LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-flash
GOOGLE_API_KEY=...
```

### Ollama

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
LLM_BASE_URL=http://host.docker.internal:11434
```

Las API keys son variables backend-only. No se exponen al frontend.

## Levantar La Aplicacion

Con Docker Compose:

```bash
COMPOSE_DETACH=1 ./utils.sh dev
```

Servicios:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Postgres: `localhost:5432`

Comandos utiles:

```bash
./utils.sh db                 # Levanta solo Postgres
./utils.sh backend            # Levanta backend y dependencias necesarias
./utils.sh frontend           # Levanta solo frontend
./utils.sh logs               # Logs de todos los servicios
./utils.sh logs backend       # Logs de un servicio
./utils.sh stop               # Detiene el stack
```

Si hay puertos ocupados, detiene el stack anterior:

```bash
./utils.sh stop
```

## Base De Datos

Postgres se inicializa con:

```text
apps/backend/sql/001_create_persistence_schema.sql
```

Tablas principales:

- `posts`: post conceptual y estado de publicacion.
- `generations`: versiones generadas o regeneradas del contenido.
- `agent_logs`: trazas de agentes asociadas a una generacion.

Datos de conexion local por defecto:

```text
Host: localhost
Port: 5432
Database: linkedin_automate
User: postgres
Password: postgres
```

Verificar conteos:

```bash
docker compose exec postgres psql -U postgres -d linkedin_automate -c "select count(*) from posts; select count(*) from generations; select count(*) from agent_logs;"
```

## API Principal

### Health

```http
GET /health
```

### Generar Post

```http
POST /api/generate
```

Payload ejemplo:

```json
{
  "instructions": "Use a practical and executive tone.",
  "categories": ["cs.CL", "cs.AI", "cs.LG"],
  "interests": ["AI agents", "LLM automation", "retrieval augmented generation"],
  "min_score": 0.18,
  "max_results": 15,
  "max_curated_results": 5,
  "content_type": "linkedin_post",
  "content_focus": "Practical AI automation for technical leaders"
}
```

### Regenerar Post

```http
POST /api/regenerate
```

Usa el LLM configurado para reescribir un draft existente con instrucciones como "hazlo mas conciso" o "profundiza sobre X".

### Listar Posts

```http
GET /api/posts
```

Devuelve posts generados, contenido activo y estado de publicacion.

### Obtener Trazas

```http
GET /api/posts/{id}/trace
```

Devuelve los `agent_logs` asociados a la generacion activa del post.

## Desarrollo Local Sin Docker

Instalar dependencias Python:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Levantar backend local:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/linkedin_automate \
  .venv/bin/python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000
```

Frontend local:

```bash
cd apps/frontend
npm install
npm run dev
```

## Tests

Suite Python:

```bash
.venv/bin/python -m pytest
```

Build frontend:

```bash
cd apps/frontend
npm run build
```

Lint frontend:

```bash
cd apps/frontend
npm run lint
```

## Notas De Seguridad

- No versionar `.env`.
- Usar `.env.example` como plantilla.
- Mantener API keys solo en variables backend-only (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `LLM_API_KEY`).
- Para Docker, `host.docker.internal` permite que el backend dentro del contenedor contacte servicios locales como LMStudio u Ollama.

## Estado Actual

El proyecto ya cuenta con:

- Workflow multi-agente funcional.
- UI configurable para generacion y regeneracion.
- Persistencia en Postgres.
- Trazas de agentes por generacion.
- Capa agnostica de LLMs por variables de entorno.
