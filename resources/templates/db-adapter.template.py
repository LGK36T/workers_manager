"""
Plantilla: Adaptador de Base de Datos para Workers en Python
Encapsula la comunicación con PostgreSQL 17 a través de Stored Procedures.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

logger = logging.getLogger("db_adapter")

class TaskDatabaseAdapter:
    def __init__(self) -> None:
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "mydb")
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASSWORD", "password")

        conninfo = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

        self._pool = AsyncConnectionPool(
            conninfo=conninfo,
            min_size=2,
            max_size=10,
            timeout=10.0,
            kwargs={
                "row_factory": dict_row,
                "options": "-c timezone=America/Santiago"
            },
            open=False
        )

    async def initialize(self) -> None:
        """Abre el pool de conexiones."""
        await self._pool.open()
        logger.info("Pool de base de datos para worker inicializado")

    async def close(self) -> None:
        """Cierra el pool de conexiones."""
        await self._pool.close()
        logger.info("Pool de base de datos para worker cerrado")

    async def claim_next_task(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Invoca app.async_task_claim(worker_id) que ejecuta SKIP LOCKED.
        Retorna la tarea reclamada o None si la cola está vacía.
        """
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT app.async_task_claim(%s) AS task;", [worker_id])
                row = await cur.fetchone()
                return row["task"] if row and row["task"] else None

    async def update_progress(self, task_id: str, progress: int) -> None:
        """Actualiza el porcentaje de progreso (0-100)."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT app.async_task_update_progress(%s, %s);",
                    [task_id, progress]
                )

    async def complete_task(self, task_id: str, result: Dict[str, Any]) -> None:
        """Marca la tarea como completada e inyecta el resultado final."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT app.async_task_complete(%s, %s);",
                    [task_id, json.dumps(result)]
                )

    async def fail_task(
        self,
        task_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        retry_delay_seconds: int = 30
    ) -> None:
        """Registra el fallo de la tarea y gestiona reintento o envío a DLQ."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT app.async_task_fail(%s, %s, %s, %s);",
                    [
                        task_id,
                        error_message,
                        json.dumps(error_details) if error_details else None,
                        retry_delay_seconds
                    ]
                )

    async def check_if_completed(self, task_id: str) -> bool:
        """Verifica si la tarea ya fue marcada como completed (idempotencia)."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT status FROM app.async_tasks WHERE id = %s;",
                    [task_id]
                )
                row = await cur.fetchone()
                return bool(row and row["status"] == "completed")
