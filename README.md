# Workers Manager

Skill de arquitectura y procesamiento asíncrono. Define estándares para tareas en segundo plano, colas de trabajo resilientes, workers en Python 3.12+ con `asyncio` y su integración con Express 5, PostgreSQL 17 y Next.js 15.

---

## Arquitectura y Principios

- **Desacoplamiento Total:** Aislamiento estricto entre productores (API Gateway en Express), almacenamiento transaccional (PostgreSQL 17) y consumidores (Workers en Python).
- **Idempotencia Estricta:** Manejo mandatorio de claves de deduplicación y verificación previa para evitar efectos colaterales duplicados en caso de reintentos.
- **Concurrencia Segura con SKIP LOCKED:** Procedimientos de consumo en PostgreSQL (`app.async_task_claim`) que permiten escalar horizontalmente decenas de workers sin contención de bloqueos.
- **Reintentos con Backoff Exponencial y Jitter:** Políticas de reintento calibradas que no saturan servicios externos caídos, combinadas con Dead-Letter Queues (DLQ) para fallos definitivos.
- **Apagado Agraciado (*Graceful Shutdown*):** Intercepción de señales `SIGTERM` y `SIGINT` para finalizar trabajos en curso y cerrar ordenadamente pools de conexiones.
- **Flujo E2E Integrado:** Disparo desde frontend (`POST /dispatch`), encolado con respuesta inmediata `202 Accepted`, procesamiento en worker, actualización de progreso y "pintado" automático en Next.js.

---

## Estructura del Repositorio

```text
workers_manager/
├── SKILL.md                          # Instrucciones y flujo de trabajo principal
├── references/                       # Documentación técnica de referencia
│   └── technical-architecture.md     # Especificación técnica exhaustiva
├── resources/
│   └── templates/                    # Plantillas de código reutilizables
│       ├── worker-main.template.py           # Loop principal con graceful shutdown
│       ├── task-handler.template.py          # Manejador de tareas idempotente
│       ├── retry-policy.template.py          # Backoff exponencial con jitter
│       ├── db-adapter.template.py            # Adaptador de base de datos con psycopg v3
│       ├── task-contract.template.py         # Contratos y esquemas Pydantic v2
│       ├── api-task-dispatcher.template.ts   # Despachador de tareas para Express 5
│       └── frontend-task-hook.template.ts    # Store Zustand + Custom Hook para polling reactivo
├── CHANGELOG.md                      # Historial de cambios
├── LICENSE                           # Licencia MIT
└── README.md                         # Este documento
```

---

## Instalación y Uso

Colocar este directorio dentro de la ruta de skills del entorno de trabajo:

```bash
.agents/skills/workers_manager/
```

Para consultar el flujo de trabajo completo, ver [SKILL.md](./SKILL.md).

---

## Licencia

[MIT](./LICENSE)
