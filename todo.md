# Backlog del Proyecto: LinkedIn AI Automator

# Backlog: Sistema Multi-Agente para LinkedIn

- [x] Fase 1: Reestructuración de Arquitectura
    - [x] Crear cliente base de arXiv (Migrado a Tool)
    - [x] Crear estructura de carpetas `src/agents/`, `src/tools/`
    - [x] Definir el esquema del estado global en `src/state.py`
- [x] Fase 2: Implementación de Agentes (Nodos)
    - [x] Implementar Researcher Agent y vincular arXiv Tool
    - [x] Implementar Curator Agent (Lógica de scoring)
    - [x] Implementar Writer Agent (Prompting con estilo LinkedIn)
    - [x] Implementar Reviewer Agent (Validación de alucinaciones)
- [x] Fase 3: Orquestación del Grafo (`src/graph.py`)
    - [x] Construir el workflow/grafo que conecta los agentes
    - [x] Probar el ciclo completo en local
- [x] Fase 4: Conexión de App
    - [x] Construir backend con FastAPI
    - [x] Conectar Frontend con Backend
    - [x] Construir utils.sh para levantar servicios
- [x] Fase 5: Persistencia Backend
    - [x] Añadir SQLModel y configuración Postgres
    - [x] Crear modelos `Post`, `Generation` y `AgentLog`
    - [x] Inicializar tablas al arrancar FastAPI
    - [x] Exponer endpoints `/api/posts` y `/api/posts/{id}/trace`
    - [x] Levantar Postgres local con Docker Compose
    - [x] Crear SQL de inicialización del modelo de datos