// =============================================================================
// Plantilla Frontend: Zustand Store + Custom Hook para Tareas Asíncronas
// Permite que React 19 / Next.js 15 gatille tareas, monitoree progreso y pinte resultados
// =============================================================================

import { create } from 'zustand'
import { api } from '@/utils/api'
import { IDataResponse } from '@/store/interfaces/response.interface'

export type TaskStatus = 'idle' | 'pending' | 'processing' | 'completed' | 'failed'

export interface ITaskStatusResponse {
  taskId: string
  taskType: string
  status: TaskStatus
  progress: number
  result: any | null
  errorMessage: string | null
}

interface AsyncTaskState {
  currentTaskId: string | null
  status: TaskStatus
  progress: number
  resultData: any | null
  onLoading: boolean
  onError: boolean
  error: string

  // Acciones
  triggerTask: (taskType: string, payload: Record<string, any>) => Promise<string | null>
  pollStatus: (taskId: string) => Promise<void>
  resetTask: () => void
}

let pollingInterval: NodeJS.Timeout | null = null

export const useAsyncTaskStore = create<AsyncTaskState>((set, get) => ({
  currentTaskId: null,
  status: 'idle',
  progress: 0,
  resultData: null,
  onLoading: false,
  onError: false,
  error: '',

  triggerTask: async (taskType, payload) => {
    // 1. Limpiar estado previo
    if (pollingInterval) clearInterval(pollingInterval)
    set({ onLoading: true, onError: false, error: '', progress: 0, resultData: null, status: 'pending' })

    try {
      // 2. Disparar a la API
      const { data: response } = await api.post<IDataResponse<{ taskId: string }>>(
        '/tasks/dispatch',
        { taskType, payload }
      )

      if (!response.success || !response.data?.taskId) {
        throw new Error(response.error ?? 'Fallo al despachar la tarea')
      }

      const taskId = response.data.taskId
      set({ currentTaskId: taskId })

      // 3. Iniciar Polling de progreso automático (cada 1.5s)
      pollingInterval = setInterval(() => {
        get().pollStatus(taskId)
      }, 1500)

      return taskId
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error al iniciar la tarea'
      set({ onLoading: false, onError: true, error: message, status: 'failed' })
      return null
    }
  },

  pollStatus: async (taskId) => {
    try {
      const { data: response } = await api.get<IDataResponse<ITaskStatusResponse>>(
        `/tasks/${taskId}/status`
      )

      if (!response.success || !response.data) {
        return
      }

      const task = response.data
      set({ progress: task.progress, status: task.status })

      // 4. Si finalizó con éxito: detener polling y guardar resultado para pintar en UI
      if (task.status === 'completed') {
        if (pollingInterval) clearInterval(pollingInterval)
        set({
          resultData: task.result,
          onLoading: false,
          status: 'completed',
          progress: 100,
        })
      }

      // 5. Si falló: detener polling y notificar error
      if (task.status === 'failed') {
        if (pollingInterval) clearInterval(pollingInterval)
        set({
          onLoading: false,
          onError: true,
          error: task.errorMessage ?? 'La tarea finalizó con errores',
          status: 'failed',
        })
      }
    } catch {
      // En caso de caída momentánea de red, no abortar de inmediato; el polling reintentará
    }
  },

  resetTask: () => {
    if (pollingInterval) clearInterval(pollingInterval)
    set({
      currentTaskId: null,
      status: 'idle',
      progress: 0,
      resultData: null,
      onLoading: false,
      onError: false,
      error: '',
    })
  },
}))

// Custom Hook con selectores atómicos
export const useAsyncTask = () => {
  const triggerTask   = useAsyncTaskStore((s) => s.triggerTask)
  const resetTask     = useAsyncTaskStore((s) => s.resetTask)
  const currentTaskId = useAsyncTaskStore((s) => s.currentTaskId)
  const status        = useAsyncTaskStore((s) => s.status)
  const progress      = useAsyncTaskStore((s) => s.progress)
  const resultData    = useAsyncTaskStore((s) => s.resultData)
  const onLoading     = useAsyncTaskStore((s) => s.onLoading)
  const onError       = useAsyncTaskStore((s) => s.onError)
  const error         = useAsyncTaskStore((s) => s.error)

  return {
    triggerTask,
    resetTask,
    currentTaskId,
    status,
    progress,
    resultData,
    onLoading,
    onError,
    error,
  }
}
