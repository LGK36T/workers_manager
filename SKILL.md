---
name: workers-manager
description: >-
  Instrucciones y estándares de arquitectura para diseñar, implementar y monitorear tareas en segundo plano, colas de trabajo y procesamiento asíncrono en Python 3.12+, PostgreSQL 17, Celery/asyncio y su integración reactiva con frontend y backend.
---

# Workers Manager

Guía de arquitectura, procesamiento asíncrono y flujo de trabajo para background workers en Python 3.12+, `asyncio`, PostgreSQL 17, Express 5 y Next.js 15.

---

## Flujo de Procesamiento Asíncrono E2E

El ciclo completo entre usuario, API, worker y base de datos opera de forma desacoplada:

```
[ FRONTEND ] Gatilla acción -> POST /api/v1/{module}/dispatch
     ↓
[ EXPRESS API ] Valida payload -> Inserta en app.async_tasks ('pending') -> 202 Accepted { taskId }
     ↓
[ POSTGRESQL ] Almacena tarea -> Expone app.async_task_claim() con SKIP LOCKED
     ↓
[ PYTHON WORKER ] Reclama tarea ('processing') -> Ejecuta cálculos -> Actualiza progreso ->
                  Guarda datos finales en tablas de dominio -> Marca 'completed'
     ↓
[ EXPRESS API ] Atiende Polling: GET /api/v1/{module}/tasks/:taskId/status -> Retorna { status, data }
     ↓
[ FRONTEND ] Detecta 'completed' -> Actualiza Zustand Store -> "Pinta" los resultados en pantalla
```

Documentación detallada en [Guía de Arquitectura Técnica](./references/technical-architecture.md).

---

## Flujo de Trabajo

Al implementar o modificar un worker o tarea asíncrona, seguir este orden:

### 1. Definir el Contrato de la Tarea (Pydantic v2)
- Ubicación: `src/models/tasks/{task_name}.py`.
- Definir esquemas para `Payload`, `Result` y `Status`.
- Tipar explícitamente los campos obligatorios y opcionales.
- Referencia: [task-contract.template.py](./resources/templates/task-contract.template.py).

### 2. Configurar la Persistencia en Base de Datos
- Reutilizar la tabla `app.async_tasks` y los Stored Procedures de `database_manager`:
  - `app.async_task_create()` (API Gateway).
  - `app.async_task_claim()` (Worker con `SKIP LOCKED`).
  - `app.async_task_update_progress()` (Worker).
  - `app.async_task_complete()` (Worker).
  - `app.async_task_fail()` (Worker).
- Referencia: [db-adapter.template.py](./resources/templates/db-adapter.template.py).

### 3. Implementar el Manejador de Tarea (*Task Handler*)
- Ubicación: `src/tasks/{task_name}.py`.
- **Idempotencia Obligatoria:** Comprobar si la tarea ya fue procesada antes de ejecutar efectos secundarios.
- Actualizar el progreso porcentual (`progress`: 0% a 100%) en cada etapa relevante para feedback de usuario.
- Referencia: [task-handler.template.py](./resources/templates/task-handler.template.py).

### 4. Configurar la Política de Reintentos y Resiliencia
- Ubicación: `src/core/retry.py`.
- Aplicar backoff exponencial con *jitter* para errores transitorios de red o timeouts.
- Discriminar errores no recuperables (datos inválidos), enviándolos de inmediato a estado `failed` (Dead-Letter).
- Referencia: [retry-policy.template.py](./resources/templates/retry-policy.template.py).

### 5. Estructurar el Loop Principal y Graceful Shutdown
- Ubicación: `src/worker.py` y `src/main.py`.
- Interceptar señales `SIGTERM` y `SIGINT` mediante `loop.add_signal_handler()`.
- Definir timeouts máximos por tarea con `asyncio.timeout()`.
- Garantizar el cierre ordenado del pool de conexiones.
- Referencia: [worker-main.template.py](./resources/templates/worker-main.template.py).

### 6. Configurar el Despachador en la API (Express 5)
- Ubicación: `src/routers/tasks.ts` y `src/controllers/tasks.ts` en el backend.
- Validar el request con Zod y responder de inmediato `202 Accepted` con el `taskId`.
- Exponer endpoint `GET /tasks/:id/status` para la verificación de avance.
- Referencia: [api-task-dispatcher.template.ts](./resources/templates/api-task-dispatcher.template.ts).

### 7. Integrar Polling y Renderizado Reactivo en el Frontend
- Ubicación: `src/store/zustand/{task}.store.ts` y `src/store/hooks/use{Task}.hook.ts`.
- Iniciar polling de estado cada 1.5s - 2s tras gatillar la acción.
- Al detectar `status === 'completed'`, detener el polling, guardar los datos en el Store y "pintar" la interfaz sin bloqueos.
- Referencia: [frontend-task-hook.template.ts](./resources/templates/frontend-task-hook.template.ts).

### 8. Verificación y Pruebas
```bash
pytest tests/
python -m src.main --test-run
```

---

## Reglas Estrictas

- Prohibido realizar operaciones síncronas bloqueantes (`time.sleep()`, llamadas HTTP con `requests`); usar siempre `asyncio.sleep()` y clientes asíncronos (`httpx`).
- Cada worker o manejador debe ser estrictamente idempotente para tolerar reintentos sin generar duplicados.
- Toda consulta de cola en base de datos debe emplear `FOR UPDATE SKIP LOCKED`.
- Las tareas deben contar con un tiempo límite de ejecución (*timeout*) para evitar procesos colgados.
- Se debe propagar el identificador de trazabilidad (`correlationId` / `taskId`) en todos los logs estructurados.
- Nunca emitir respuestas HTTP síncronas en la API para tareas pesadas; siempre encolar y responder `202 Accepted`.

---

## Referencias y Plantillas

- [Guía de Arquitectura Técnica](./references/technical-architecture.md)
- [Plantillas de Código Python y TypeScript](./resources/templates/)
