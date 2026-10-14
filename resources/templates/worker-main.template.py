"""
Plantilla: Loop Principal del Worker en Python (asyncio + Graceful Shutdown)
Consume tareas asíncronas desde PostgreSQL (SKIP LOCKED) o Redis de forma resiliente.
"""

import asyncio
import signal
import socket
import logging
import sys
from typing import Optional
from contextlib import suppress

# Adaptadores internos
from db_adapter import TaskDatabaseAdapter
from task_handler import execute_task_handler

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger("worker")

class AsyncWorker:
    def __init__(self) -> None:
        self.worker_id = f"worker-{socket.gethostname()}-{id(self)}"
        self.is_running = False
        self.db = TaskDatabaseAdapter()
        self.current_task_id: Optional[str] = None

    async def start(self) -> None:
        """Inicia el ciclo principal de consumo de tareas."""
        await self.db.initialize()
        self.is_running = True
        logger.info(f"Worker {self.worker_id} iniciado y listo para procesar tareas")

        while self.is_running:
            try:
                # 1. Reclamar siguiente tarea pendiente de forma atómica
                task = await self.db.claim_next_task(self.worker_id)

                if not task:
                    # No hay tareas pendientes: ceder control y esperar
                    await asyncio.sleep(2.0)
                    continue

                self.current_task_id = str(task["id"])
                logger.info(f"Tarea reclamada: {self.current_task_id} de tipo '{task['task_type']}'")

                # 2. Ejecutar manejador de tarea con timeout
                try:
                    async with asyncio.timeout(300):  # Timeout de 5 minutos
                        await execute_task_handler(task, self.db)
                except TimeoutError:
                    logger.error(f"Timeout excedido al procesar tarea {self.current_task_id}")
                    await self.db.fail_task(
                        self.current_task_id,
                        error_message="Tiempo máximo de ejecución excedido (5m)",
                        error_details={"reason": "TimeoutError"}
                    )
                except Exception as ex:
                    logger.exception(f"Error inesperado en tarea {self.current_task_id}: {str(ex)}")
                    await self.db.fail_task(
                        self.current_task_id,
                        error_message=str(ex),
                        error_details={"exception_type": type(ex).__name__}
                    )
                finally:
                    self.current_task_id = None

            except asyncio.CancelledError:
                logger.info("Worker recibió orden de cancelación")
                break
            except Exception as e:
                logger.error(f"Error en el bucle principal del worker: {str(e)}")
                await asyncio.sleep(5.0)

        # 3. Limpieza final tras apagado
        await self.cleanup()

    async def stop(self) -> None:
        """Solicita el apagado agraciado del worker."""
        logger.info("Iniciando apagado agraciado (Graceful Shutdown)...")
        self.is_running = False

    async def cleanup(self) -> None:
        """Cierra conexiones y libera recursos."""
        await self.db.close()
        logger.info("Recursos liberados. Worker detenido correctamente.")


async def main() -> None:
    worker = AsyncWorker()
    loop = asyncio.get_running_loop()

    # Registrar interceptores de señales del Sistema Operativo
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Proceso terminado por el usuario o sistema")
