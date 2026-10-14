# Referencia Técnica — Procesamiento Asíncrono y Workers en Python

> **Versión:** 2.0  
> **Ecosistema:** Python 3.12+ · `asyncio` · `psycopg` v3 (con `psycopg_pool`) · Pydantic v2 · Express 5 · Next.js 15  
> **Propósito:** Especificación de ingeniería y estándares de desarrollo para implementar sistemas de procesamiento en segundo plano, colas de trabajo resilientes, ejecución paralela e integración completa con el backend (`backend_manager`), frontend (`frontend_manager`) y la base de datos (`database_manager`).

---

## Tabla de Contenidos

1. [Visión General y Arquitectura del Sistema Asíncrono](#1-visión-general-y-arquitectura-del-sistema-asíncrono)
2. [Ciclo de Vida y Máquina de Estados de la Tarea](#2-ciclo-de-vida-y-máquina-de-estados-de-la-tarea)
3. [Idempotencia y Claves de Deduplicación](#3-idempotencia-y-claves-de-deduplicación)
4. [Motores de Ejecución: `asyncio` Nativo (PostgreSQL) vs Celery + Redis](#4-motores-de-ejecución-asyncio-nativo-postgresql-vs-celery--redis)
5. [Estrategia de Reintentos: Backoff Exponencial con Jitter](#5-estrategia-de-reintentos-backoff-exponencial-con-jitter)
6. [Manejo de Errores y Dead-Letter Queue (DLQ)](#6-manejo-de-errores-y-dead-letter-queue-dlq)
7. [Control de Ciclo de Vida: Timeouts y Apagado Agraciado (*Graceful Shutdown*)](#7-control-de-ciclo-de-vida-timeouts-y-apagado-agraciado-graceful-shutdown)
8. [Persistencia de Resultados y Conexiones a PostgreSQL](#8-persistencia-de-resultados-y-conexiones-a-postgresql)
9. [Trazabilidad Distribuida (`correlation_id`) y Logging Estructurado](#9-trazabilidad-distribuida-correlation_id-y-logging-estructurado)
10. [Capa API (Express 5): Encolado y Consulta de Estado](#10-capa-api-express-5-encolado-y-consulta-de-estado)
11. [Capa Frontend (Next.js 15 / Zustand): Polling y Pintado de UI](#11-capa-frontend-nextjs-15--zustand-polling-y-pintado-de-ui)
12. [Estructura del Proyecto Worker en Python](#12-estructura-del-proyecto-worker-en-python)
13. [Dockerización y Despliegue en Producción](#13-dockerización-y-despliegue-en-producción)
14. [Checklist Pre-Deploy y Auditoría de Workers](#14-checklist-pre-deploy-y-auditoría-de-workers)

---

## 1. Visión General y Arquitectura del Sistema Asíncrono

Para mantener la API de Express ágil y responsiva con tiempos de respuesta bajo los 100ms, cualquier operación que demande más de 200ms de procesamiento de CPU, I/O intensivo o consultas a servicios de terceros debe desacoplarse hacia un proceso independiente: un **Worker Asíncrono en Python**.

### Flujo Unidireccional de Información

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Frontend (Next.js 15 / React 19)                                         │
│    Usuario gatilla acción -> Store dispara POST /api/v1/{module}/dispatch    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP 202 Accepted { taskId }
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. API Gateway (Node.js 22 / Express 5)                                     │
│    Valida payload con Zod -> Inserta en BD con status = 'pending'          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Persiste en app.async_tasks
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Base de Datos (PostgreSQL 17)                                            │
│    Almacena tarea y expone procedimiento atómico app.async_task_claim()     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ SELECT ... FOR UPDATE SKIP LOCKED
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. Worker Service (Python 3.12 / asyncio)                                   │
│    Reclama tarea -> marca 'processing' -> ejecuta lógica pesada ->          │
│    actualiza progreso -> guarda resultado final en tablas y marca 'completed│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Resultado persistido en BD
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. API Gateway (Express 5)                                                  │
│    Atiende polling periódico: GET /api/v1/{module}/tasks/:taskId/status     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 200 OK { status: 'completed', data }
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. Frontend (Next.js 15 / Zustand)                                          │
│    Detecta 'completed' -> actualiza Store -> "pinta" los datos en pantalla │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ciclo de Vida y Máquina de Estados de la Tarea

Toda tarea asíncrona transita obligatoriamente por una máquina de estados estricta y predecible:

```
        ┌─────────────┐
        │   PENDING   │ ◄─── (Tarea creada en BD / cola)
        └──────┬──────┘
               │  Reclamada por un worker disponible
               ▼
        ┌─────────────┐
   ┌──► │ PROCESSING  │ (Actualiza progreso 0% -> 100%)
   │    └──────┬──────┘
   │           │
   │      ¿Éxito o Error?
   │           ├────────────────────────────┐
   │        Éxito                         Error
   │           ▼                            ▼
   │    ┌─────────────┐             ┌──────────────┐
   │    │  COMPLETED  │             │   RETRYING   │ (Backoff exponencial + jitter)
   │    └─────────────┘             └───────┬──────┘
   │                                        │
   │  Reintento programado                  │  ¿Agotó max_attempts?
   └────────────────────────────────────────┤
                                            ▼
                                    ┌──────────────┐
                                    │    FAILED    │ (Dead-Letter / Registro de fallo)
                                    └──────────────┘
```

| Estado | Significado | Acciones del Worker |
| :--- | :--- | :--- |
| `pending` | Tarea registrada y a la espera de un worker libre | Ninguna (en cola) |
| `processing` | Worker asignado, ejecutando cálculos pesados | Reporta `progress` porcentual periódicamente |
| `retrying` | Falló por error transitorio; reprogramada con retraso | Espera a que `scheduled_at <= NOW()` |
| `completed` | Finalizada con éxito; resultado persistido en BD | Almacena `result` en JSONB y `completed_at` |
| `failed` | Agotó los reintentos permitidos o sufrió un error fatal | Registra `error_message` y stack trace |
| `cancelled` | Cancelada explícitamente por el usuario o administrador | Aborta el procesamiento si estaba activa |

---

## 3. Idempotencia y Claves de Deduplicación

### Principio Fundamental
**Todo worker debe ser estrictamente idempotente:** Si la misma tarea se procesa dos o más veces debido a reintentos de red, reconexiones o reinicio inesperado del proceso, el resultado debe ser exactamente el mismo y **no debe generar duplicados** (ej. no cobrar dos veces, no duplicar filas en tablas contables ni enviar correos repetidos).

### Estrategia de Implementación
1. **Clave de Deduplicación (`idempotency_key` o `task_id`):** Cada tarea generada por la API cuenta con un identificador único.
2. **Validación Previa:** Antes de ejecutar cualquier efecto secundario externo (ej. llamada a una API de pagos o inserción de registros finales), el worker consulta si ya existe un resultado asociado a dicho `task_id`.
3. **Inserciones Condicionales:** Uso de `ON CONFLICT (task_id) DO NOTHING` o verificación transaccional previa.

```python
async def execute_task(task_id: str, payload: dict) -> dict:
    # 1. Comprobar si ya fue procesada
    existing_result = await db.get_task_result(task_id)
    if existing_result:
        logger.info("Tarea %s ya procesada previamente. Retornando caché.", task_id)
        return existing_result

    # 2. Ejecutar procesamiento de negocio...
    result = await do_heavy_work(payload)

    # 3. Guardar atómicamente
    await db.save_task_result(task_id, result)
    return result
```

---

## 4. Motores de Ejecución: `asyncio` Nativo (PostgreSQL) vs Celery + Redis

Dependiendo de la escala y la infraestructura del proyecto, se seleccionan dos patrones arquitectónicos recomendados:

### Patrón A: Python `asyncio` Nativo + PostgreSQL `SKIP LOCKED` (Recomendado por defecto)
* **Ventajas:** Cero dependencias adicionales (no requiere instalar ni mantener Redis o RabbitMQ). Consistencia transaccional ACID completa entre los datos del negocio y el estado de la tarea.
* **Mecanismo:** El worker ejecuta un bucle asíncrono con `asyncio.sleep()` que consume de la tabla `app.async_tasks` invocando `app.async_task_claim()`.
* **Idóneo para:** Proyectos medianos, startups, entornos contenerizados sencillos y sistemas donde la atomicidad de la base de datos es prioritaria.

### Patrón B: Celery + Redis / RabbitMQ (Para alta escala distribuida)
* **Ventajas:** Diseñado para miles de tareas por segundo, programación periódica compleja (*Celery Beat*), orquestación de flujos dependientes (*chains*, *chords* y *groups*).
* **Mecanismo:** La API de Express publica el mensaje en Redis; los workers de Celery consumen la cola y al finalizar escriben el resultado en PostgreSQL 17.
* **Idóneo para:** Aplicaciones empresariales con alto volumen de procesamiento masivo y distribución en múltiples clusters.

---

## 5. Estrategia de Reintentos: Backoff Exponencial con Jitter

Cuando una tarea falla, reintentar de inmediato satura aún más los servicios que puedan estar degradados. Se debe aplicar **Backoff Exponencial con Variación Aleatoria (*Jitter*)**:

$$t_{\text{wait}} = \min(t_{\text{max}}, t_{\text{base}} \times 2^{\text{attempt}}) \pm \text{random\_jitter}$$

### Clasificación de Excepciones
* **Errores Transitorios (Reintentables):** Caídas de conexión a red, timeouts de base de datos, límites de tasa (*rate limit* 429 de APIs externas). Se reintentan aplicando la fórmula.
* **Errores Fatales (No Reintentables):** Violaciones de esquemas, errores de validación en el payload (400 Bad Request), datos inexistentes o lógica de negocio inválida. Se marcan inmediatamente como `failed` para no gastar recursos inútilmente.

---

## 6. Manejo de Errores y Dead-Letter Queue (DLQ)

Cuando una tarea agota su número máximo de intentos (`attempts >= max_attempts`):
1. **Transición a Fallo:** El worker actualiza el estado a `failed`.
2. **Registro Forense:** Se almacena el mensaje de error legible, el tipo de excepción y el volcado completo de la traza (*traceback*) en formato JSON dentro de `error_details`.
3. **Aislamiento en DLQ:** La tarea queda en estado inactivo sin ser reconsultada por los workers activos, disponible para inspección o reprocesamiento manual desde un panel de administración.

---

## 7. Control de Ciclo de Vida: Timeouts y Apagado Agraciado (*Graceful Shutdown*)

### Timeouts Estrictos
Para evitar que un worker quede congelado indefinidamente por una conexión de red colgada o un bucle infinito, cada tarea se ejecuta dentro de un límite de tiempo:

```python
try:
    async with asyncio.timeout(300):  # 5 minutos máximo
        result = await process_job(payload)
except TimeoutError:
    logger.error("Tarea %s excedió el tiempo límite permitido", task_id)
    await handle_task_timeout(task_id)
```

### Apagado Agraciado (*Graceful Shutdown*)
Cuando Docker o Kubernetes envía una señal de terminación (`SIGTERM` o `SIGINT`):
1. El worker intercepta la señal y deja de aceptar o reclamar nuevas tareas (`is_running = False`).
2. Espera a que las tareas que ya están en procesamiento terminen limpiamente o alcancen un punto de control (*checkpoint*).
3. Si la tarea en curso no puede finalizar en el tiempo de gracia (ej. 15 segundos), revierte el estado a `pending` o libera el bloqueo para que otro worker la retome tras el reinicio.
4. Cierra de forma ordenada el pool de conexiones de base de datos.

---

## 8. Persistencia de Resultados y Conexiones a PostgreSQL

El worker en Python se conecta a PostgreSQL 17 utilizando **`psycopg` versión 3**, haciendo uso exclusivo de su pool de conexiones asíncronas (`psycopg_pool.AsyncConnectionPool`):

* **Eficiencia de Conexiones:** El pool mantiene entre 2 y 10 conexiones activas reutilizables, evitando el costo de establecer una conexión TCP por cada tarea.
* **Invocación de Stored Procedures:** El worker interactúa mediante los mismos Stored Procedures definidos en `database_manager`:
  * Reclamar tarea: `SELECT app.async_task_claim(%s)`
  * Reportar progreso: `SELECT app.async_task_update_progress(%s, %s)`
  * Finalizar con éxito: `SELECT app.async_task_complete(%s, %s)`
  * Notificar fallo/reintento: `SELECT app.async_task_fail(%s, %s, %s, %s)`

---

## 9. Trazabilidad Distribuida (`correlation_id`) y Logging Estructurado

Para permitir el seguimiento de una solicitud desde que el usuario hace clic en el frontend hasta que el worker escribe en la base de datos, se utiliza un identificador de correlación:

```
[ Frontend: requestId (UUID) ] ──► [ Express: X-Request-ID ] ──► [ Task: id / correlationId ] ──► [ Worker: logger.bind(task_id) ]
```

El logger del worker debe emitir registros en formato JSON estructurado, facilitando su consumo en plataformas como Datadog, CloudWatch o Grafana Loki:

```json
{
  "timestamp": "2026-10-14T10:15:30.123Z",
  "level": "INFO",
  "worker_id": "worker-heavy-01",
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "task_type": "REPORT_GENERATION",
  "progress": 75,
  "message": "Generando sección estadística del reporte"
}
```

---

## 10. Capa API (Express 5): Encolado y Consulta de Estado

En el backend, el módulo que requiere procesamiento asíncrono implementa:

1. **Endpoint de Encolado (`POST /api/v1/{module}/dispatch`):**
   * Valida parámetros con Zod.
   * Invoca `app.async_task_create()`.
   * Responde con código HTTP `202 Accepted`:
     ```json
     {
       "success": true,
       "data": {
         "taskId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
         "status": "pending"
       },
       "error": null
     }
     ```
2. **Endpoint de Consulta de Estado (`GET /api/v1/{module}/tasks/:id/status`):**
   * Consulta `app.async_task_get_status()`.
   * Retorna `{ status, progress, result, errorMessage }`.

---

## 11. Capa Frontend (Next.js 15 / Zustand): Polling y Pintado de UI

El frontend desarrollado bajo `frontend_manager` consume la tarea de forma reactiva y transparente:

1. **Disparo de la Tarea:** El store de Zustand llama al servicio HTTP y guarda `currentTaskId` y `onLoading = true`.
2. **Mecanismo de Polling con Intervalo Seguro:**
   * Un custom hook activa un temporizador (cada 1.5 a 2 segundos).
   * Consulta el endpoint de estado de la API.
   * Actualiza el porcentaje de progreso (`progress`) para alimentar una barra de progreso o skeleton.
3. **Pintado de Resultados:**
   * Cuando detecta `status === 'completed'`, cancela el temporizador.
   * Asigna los datos resultantes al estado principal del store.
   * Cambia `onLoading = false`.
   * El componente funcional renderiza los datos en pantalla de forma instantánea.

---

## 12. Estructura del Proyecto Worker en Python

```text
workers/
├── src/
│   ├── core/
│   │   ├── config.py              # Variables de entorno con pydantic-settings
│   │   ├── database.py            # AsyncConnectionPool de psycopg v3
│   │   ├── logger.py              # Logging JSON estructurado
│   │   └── retry.py               # Algoritmo de backoff y jitter
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── base.py                # Clase base abstracta para tareas
│   │   ├── report_generator.py    # Tarea de generación de reportes
│   │   └── data_analyzer.py       # Tarea de análisis de datos
│   ├── models/
│   │   └── task.py                # Modelos Pydantic (TaskPayload, TaskResult)
│   ├── worker.py                  # Loop principal de consumo y señales
│   └── main.py                    # Punto de entrada de la aplicación
├── tests/
│   ├── test_retry.py
│   └── test_tasks.py
├── .env.example
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

---

## 13. Dockerización y Despliegue en Producción

### `Dockerfile` Multi-Stage Optimizado para Python
```dockerfile
# ─── Etapa 1: Build y dependencias ───
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ─── Etapa 2: Imagen Final de Producción ───
FROM python:3.12-slim AS runner

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 tzdata dumb-init && rm -rf /var/lib/apt/lists/*
ENV TZ=America/Santiago

RUN useradd -u 1001 -m -s /bin/bash appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY src ./src

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app/src

USER appuser

ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "src/main.py"]
```

---

## 14. Checklist Pre-Deploy y Auditoría de Workers

Antes de desplegar cualquier worker a producción, validar los siguientes puntos:

- [ ] Todas las tareas implementan control de idempotencia mediante `task_id` o deduplicación.
- [ ] No existen operaciones bloqueantes síncronas (`time.sleep()`, llamadas HTTP con `requests`); se usa `asyncio.sleep()` y clientes asíncronos (`httpx`).
- [ ] Los reintentos aplican backoff exponencial con jitter y respetan un límite máximo (`max_attempts`).
- [ ] Se capturan adecuadamente las señales `SIGTERM` y `SIGINT` para un *Graceful Shutdown* sin pérdida de tareas.
- [ ] Todas las tareas tienen un timeout máximo configurado (`asyncio.timeout`).
- [ ] La base de datos es accedida mediante un pool de conexiones reutilizable con límites configurados.
- [ ] Los logs se emiten en formato JSON estructurado conteniendo el `task_id`.
- [ ] La API de Express responde inmediatamente con `202 Accepted` al encolar.
- [ ] El frontend maneja los estados de progreso y pinta los datos automáticamente al completarse la tarea.
