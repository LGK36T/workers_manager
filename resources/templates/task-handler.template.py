"""
Plantilla: Manejador de Tareas Asíncronas Idempotente
Demuestra la orquestación de pasos, actualización periódica de progreso y persistencia.
"""

import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger("task_handler")

async def execute_task_handler(task: Dict[str, Any], db_adapter) -> None:
    """
    Despacha y procesa la tarea según su tipo, garantizando idempotencia.
    """
    task_id = str(task["id"])
    task_type = task["task_type"]
    payload = task.get("payload", {})

    logger.info(f"Iniciando procesamiento de tarea {task_id} [{task_type}]")

    # 1. Validación de Idempotencia previa
    # Si la tarea ya tiene resultados generados (ej. reintento por caída de red final), no duplicar
    is_already_done = await db_adapter.check_if_completed(task_id)
    if is_already_done:
        logger.info(f"Tarea {task_id} ya completada anteriormente. Omitiendo reprocesamiento.")
        return

    # 2. Enrutamiento según el tipo de tarea
    if task_type == "GENERATE_REPORT":
        await handle_generate_report(task_id, payload, db_adapter)
    elif task_type == "DATA_BATCH_ANALYSIS":
        await handle_data_analysis(task_id, payload, db_adapter)
    else:
        raise ValueError(f"Tipo de tarea desconocido: {task_type}")


async def handle_generate_report(task_id: str, payload: Dict[str, Any], db_adapter) -> None:
    """
    Ejemplo: Generación pesada de reporte con 4 etapas y reporte de avance en UI.
    """
    # Etapa 1: Extracción de datos (25%)
    await db_adapter.update_progress(task_id, 25)
    await asyncio.sleep(1.0)  # Simula consulta analítica intensiva

    # Etapa 2: Procesamiento y agregación (50%)
    await db_adapter.update_progress(task_id, 50)
    await asyncio.sleep(1.5)  # Simula cálculo de métricas o generación de gráficos

    # Etapa 3: Ensamblado y formateo de datos (75%)
    await db_adapter.update_progress(task_id, 75)
    await asyncio.sleep(1.0)  # Simula serialización o generación de archivo

    # Etapa 4: Guardado de resultados finales (100%)
    result_data = {
        "reportId": f"rep-{task_id[:8]}",
        "title": payload.get("title", "Reporte Consolidado"),
        "totalRecords": 1540,
        "summary": {
            "processedCount": 1540,
            "errorCount": 0,
            "status": "VALIDATED"
        },
        "downloadUrl": f"/api/v1/files/download/{task_id}.pdf"
    }

    # Completar tarea atómicamente en PostgreSQL
    await db_adapter.complete_task(task_id, result_data)
    logger.info(f"Tarea {task_id} completada exitosamente con progreso 100%")


async def handle_data_analysis(task_id: str, payload: Dict[str, Any], db_adapter) -> None:
    """
    Ejemplo: Procesamiento por lotes de registros.
    """
    items = payload.get("items", [])
    total_items = len(items)

    for index, item in enumerate(items, start=1):
        # Simula trabajo por ítem
        await asyncio.sleep(0.1)

        # Actualizar progreso cada 10%
        current_pct = int((index / max(1, total_items)) * 100)
        if current_pct % 10 == 0:
            await db_adapter.update_progress(task_id, current_pct)

    result_data = {
        "analyzedItems": total_items,
        "anomaliesDetected": 0,
        "status": "CLEAN"
    }

    await db_adapter.complete_task(task_id, result_data)
