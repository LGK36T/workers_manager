// =============================================================================
// Plantilla Express 5: Despachador de Tareas Asíncronas (API Gateway)
// Compatible con backend_manager y consumido por frontend_manager
// =============================================================================

import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import pool from "../utils/database";
import { sendResponse } from "../utils/sendResponse";
import { authenticate } from "../middlewares/auth";
import { validateRequest } from "../middlewares/validateRequest";
import { NotFoundError } from "../utils/errors";

const router = Router();

// 1. Esquema de Validación Zod para el Despacho
export const dispatchTaskSchema = z.object({
  taskType: z.string().min(1).max(100),
  payload: z.record(z.any()).default({}),
});

export type DispatchTaskInput = z.infer<typeof dispatchTaskSchema>;

// 2. Controlador: Encolar Tarea y responder de inmediato 202 Accepted
export async function dispatchTask(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const { taskType, payload } = req.body as DispatchTaskInput;
    const userId = req.user?.sub || null;

    const query = `SELECT app.async_task_create($1, $2, $3) AS data;`;
    const result = await pool.query(query, [taskType, JSON.stringify(payload), userId]);

    const createdTask = result.rows[0]?.data;
    sendResponse(req, res, createdTask, 202);
  } catch (err) {
    next(err);
  }
}

// 3. Controlador: Consultar Estado de la Tarea (para Polling)
export async function getTaskStatus(req: Request, res: Response, next: NextFunction): Promise<void> {
  try {
    const taskId = req.params.id as string;
    const query = `SELECT app.async_task_get_status($1) AS data;`;
    const result = await pool.query(query, [taskId]);

    const statusData = result.rows[0]?.data;
    if (!statusData) {
      throw new NotFoundError("Tarea asíncrona");
    }

    sendResponse(req, res, statusData, 200);
  } catch (err) {
    next(err);
  }
}

// 4. Enrutador Express
router.post("/dispatch", authenticate, validateRequest(dispatchTaskSchema), dispatchTask);
router.get("/:id/status", authenticate, getTaskStatus);

export default router;
