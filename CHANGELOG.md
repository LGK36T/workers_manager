# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [2.0.0] - 2026-10-14

### Añadido
- Documento exhaustivo de arquitectura técnica en [references/technical-architecture.md](./references/technical-architecture.md) detallando el ciclo de vida de tareas en Python, idempotencia, backoff exponencial con jitter, Dead-Letter Queues, graceful shutdown, logging estructurado y conexión E2E con Next.js y Express.
- Plantillas canónicas de código en `resources/templates/`:
  - `worker-main.template.py` (Loop principal en Python con `asyncio` y captura de señales `SIGTERM`/`SIGINT`).
  - `task-handler.template.py` (Manejador de tareas idempotente con progreso porcentual y persistencia).
  - `retry-policy.template.py` (Algoritmo de backoff exponencial con jitter y clasificación de errores).
  - `db-adapter.template.py` (Adaptador de base de datos para PostgreSQL 17 con pool `psycopg v3`).
  - `task-contract.template.py` (Contratos de datos con Pydantic v2 para payloads y resultados).
  - `api-task-dispatcher.template.ts` (Servicio y controlador en Express 5 para encolado `202 Accepted` y status polling).
  - `frontend-task-hook.template.ts` (Store Zustand y custom hook para polling y renderizado en Next.js 15).
- Especificación del flujo de extremo a extremo: Front -> API -> Worker (Python) -> BD -> API -> Front.

### Modificado
- Actualizado [SKILL.md](./SKILL.md) con flujo de trabajo por fases de 8 pasos y directrices estrictas de ejecución asíncrona.
- Actualizado [README.md](./README.md) con la nueva estructura de repositorios y principios de procesamiento asíncrono.

---

## [0.2.0] - 2026-10-11

### Añadido
- Archivo nativo para agentes de IA ([SKILL.md](./SKILL.md)) con directrices de idempotencia, políticas de reintentos, timeouts y logging estructurado.
- Licencia de código abierto MIT ([LICENSE](./LICENSE)).

### Modificado
- Reorientación completa del proyecto de módulo genérico a **Skill para agentes de IA** en [README.md](./README.md).

---

## [0.1.0] - 2026-10-11

### Añadido
- Inicialización del repositorio Git y configuración base del proyecto.
- Documentación inicial y registro de control de cambios.
- Configuración de exclusiones de archivos para control de versiones (`.gitignore`).
