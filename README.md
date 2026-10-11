# Workers Manager

Módulo responsable de la orquestación, supervisión y ejecución de tareas asíncronas, procesamiento en segundo plano (background jobs) y tareas periódicas programadas.

---

## 📌 Descripción General

**Workers Manager** centraliza la lógica para el procesamiento asíncrono y desacoplado de operaciones que demandan alto tiempo de cómputo o que deben ejecutarse en segundo plano (envío de correos, generación de reportes, sincronización de datos, ingesta de eventos, etc.). Permite mantener los servicios principales de `backend_manager` ágiles y con baja latencia.

---

## 🎯 Objetivos y Responsabilidades

- **Gestión de Colas de Tareas:** Administración y consumo de colas (Redis, RabbitMQ, SQS, Kafka, etc.).
- **Procesamiento Concurrente y Escalabilidad:** Ejecución distribuida de workers con capacidad de escalado horizontal según la carga.
- **Tareas Programadas (Cron / Batch Jobs):** Planificación y ejecución confiable de procesos recurrentes y periódicos.
- **Tolerancia a Fallos y Reintentos:** Manejo de reintentos exponenciales, dead-letter queues (DLQ) y recuperación ante fallos.
- **Monitoreo y Métricas:** Supervisión del estado de los workers, tiempos de procesamiento de jobs y tasas de éxito/error.

---

## 📂 Estructura del Proyecto

```text
workers_manager/
├── src/
│   ├── config/          # Conexiones a brokers de mensajería y servicios
│   ├── jobs/            # Definición e implementación de tareas específicas
│   ├── queues/          # Configuración y definición de colas de mensajes
│   ├── schedules/       # Definición de tareas periódicas / cron jobs
│   ├── services/        # Servicios auxiliares e integración externa
│   └── utils/           # Manejo de reintentos, validadores y helpers
├── tests/               # Pruebas unitarias y de integración de jobs
├── .gitignore           # Exclusiones de control de versiones
├── CHANGELOG.md         # Historial de versiones y cambios
└── README.md            # Documentación general del módulo
```

---

## 🚀 Inicio Rápido

### Requisitos Previos

- Broker de mensajería en ejecución (ej. Redis, RabbitMQ) o servicio en la nube equivalente.
- Entorno de ejecución configurado (Python / Celery, Node.js / BullMQ, Go, etc.).
- Variables de entorno configuradas a partir de `.env.example`.

### Configuración

1. Clonar el repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>/workers_manager.git
   cd workers_manager
   ```

2. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   ```

3. Iniciar los procesos de trabajo (workers):
   ```bash
   # Ejemplo de ejecución según el gestor
   npm run start:worker
   # o bien: celery -A worker worker --loglevel=info
   ```

---

## 🔄 Flujo de Trabajo con Git

1. Crear una rama descriptiva para cada nuevo job o mejora de infraestructura:
   ```bash
   git checkout -b feature/nuevo-worker-job
   ```
2. Realizar commits claros siguiendo buenas prácticas.
3. Registrar los cambios en el archivo [CHANGELOG.md](file:///home/LGK36T/workspace/skills/workers_manager/CHANGELOG.md).
4. Abrir un Pull Request / Merge Request para revisión del equipo.

---

## 📄 Licencia

Este proyecto está bajo los términos y directrices definidos por el equipo de desarrollo.
