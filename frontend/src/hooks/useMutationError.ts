import { useCallback, useContext } from 'react'
import { ToastContext } from '../design-system/primitives/toast-context'
import { ApiError } from '../services/httpClient'

export function useMutationError() {
  const ctx = useContext(ToastContext)

  return useCallback(
    (error: unknown, context?: string) => {
      let message = 'Ocurrió un error inesperado.'
      if (error instanceof ApiError) {
        message = error.message
      } else if (error instanceof Error) {
        message = error.message
      }
      if (ctx) {
        ctx.push({
          title: context ?? 'Error',
          description: message,
          tone: 'danger',
        })
      }
    },
    [ctx],
  )
}
