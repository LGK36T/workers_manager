---
name: workers-manager
description: >-
  Instrucciones y estándares de arquitectura para agentes de IA al diseñar, implementar y monitorear tareas en segundo plano, colas de trabajo y procesamiento asíncrono.
---

# Skill: Workers Manager para Agentes de IA

Este skill instruye a los agentes de IA en el diseño e implementación de sistemas de procesamiento en segundo plano, colas de mensajería (BullMQ, Celery, SQS, RabbitMQ) y tareas programadas periódicas (cron jobs).

---

## 🎯 Directrices Principales de Comportamiento

### 1. Idempotencia Obligatoria en Jobs
- Cada worker o manejador de tarea debe ser **estrictamente idempotente**: si un job se procesa más de una vez con los mismos parámetros, el resultado debe ser consistente sin generar efectos colaterales duplicados (ej. dobles pagos o correos repetidos).
- Emplear claves únicas de deduplicación (`jobId`, claves de idempotencia en base de datos o Redis).

### 2. Políticas de Reintentos y Resiliencia
- No realizar reintentos inmediatos ni infinitos: aplicar **backoff exponencial** con variación aleatoria (*jitter*) para no saturar servicios externos caídos.
- Implementar **Dead-Letter Queues (DLQ)** para aislar jobs que agoten sus intentos máximos y permitir análisis o reprocesamiento manual.

### 3. Timeouts y Apagado Agraciado (Graceful Shutdown)
- Cada tarea debe contar con un tiempo límite de ejecución (*timeout*) definido para evitar procesos colgados indefinidamente.
- Escuchar señales de terminación del sistema operativo (`SIGTERM`, `SIGINT`) para que los workers completen los jobs en curso o liberen bloqueos antes de salir.

### 4. Trazabilidad y Logging Estructurado
- Todo mensaje de cola debe incluir un identificador de correlación (`correlationId` o `traceId`) para rastrear el flujo completo desde el origen (API/frontend) hasta el worker.
- Registrar métricas esenciales: tiempo en cola, duración del procesamiento y tasa de éxito/error.

### 5. Aislamiento y Desacoplamiento
- Los procesos worker no deben compartir memoria con el servidor web o API principal.
- Desacoplar la producción de tareas (encolado) del consumo de las mismas (procesamiento).

---

## 🚫 Acciones Prohibidas para el Agente

- ❌ Diseñar jobs no idempotentes que provoquen efectos secundarios duplicados en reintentos.
- ❌ Bloquear el hilo principal o event loop con operaciones síncronas intensivas o sleeps sin ceder control.
- ❌ Suprimir excepciones silenciosamente sin registrar la causa en la cola o sistema de métricas.
- ❌ Configurar reintentos infinitos inmediatos.
