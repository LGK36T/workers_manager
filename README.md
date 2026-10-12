# Workers Manager (AI Agent Skill)

Skill especializada para guiar a los agentes de Inteligencia Artificial al diseñar, codificar, refactorizar y verificar sistemas de procesamiento asíncrono, colas de mensajería y tareas programadas en segundo plano.

---

## 📌 ¿Qué es este Skill?

**Workers Manager** establece directrices estrictas para que los agentes de IA (como Antigravity, Claude Code, Cursor, Copilot, etc.) diseñen background workers resilientes, tolerantes a fallos y con alta capacidad de procesamiento concurrente.

La especificación completa del comportamiento del agente se encuentra en [SKILL.md](file:///home/LGK36T/workspace/skills/workers_manager/SKILL.md).

---

## 🎯 Directrices que impone a la IA

- **Idempotencia Estricta:** Manejo mandatorio de claves de deduplicación para prevenir efectos secundarios duplicados en reintentos.
- **Reintentos Resilientes:** Políticas de backoff exponencial con jitter y aislamiento en Dead-Letter Queues (DLQ).
- **Control de Ciclo de Vida:** Timeouts obligatorios y gestión de apagado agraciado (*graceful shutdown*) ante señales de parada.
- **Trazabilidad de Mensajes:** Uso de `correlationId` para trazabilidad distribuida entre APIs y workers.
- **Desacoplamiento:** Aislamiento total entre productores (encolado) y consumidores (ejecución de workers).

---

## 📂 Contenido del Repositorio

```text
workers_manager/
├── SKILL.md             # Instrucciones principales para el agente de IA
├── CHANGELOG.md         # Historial de cambios del skill
├── LICENSE              # Licencia de código abierto (MIT)
├── README.md            # Documentación y descripción del skill
└── .gitignore           # Exclusiones de control de versiones
```

---

## 🚀 Uso e Integración

### En Google Antigravity / Asistentes IA
Coloca este repositorio dentro del directorio de skills de tu espacio de trabajo:
```bash
.agents/skills/workers_manager/
# o ~/.gemini/antigravity-cli/skills/workers_manager/
```
El agente descubrirá automáticamente el archivo `SKILL.md` y aplicará estas directrices cuando trabaje con colas, procesos en segundo plano o cron jobs.

---

## 📄 Licencia

Este proyecto está bajo la licencia [MIT](file:///home/LGK36T/workspace/skills/workers_manager/LICENSE).
