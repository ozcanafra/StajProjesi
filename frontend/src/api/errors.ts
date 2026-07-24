import { isAxiosError } from 'axios'

export function getErrorMessage(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    if (!err.response) {
      return 'Sunucuya ulasilamiyor. Backend/Docker calisiyor mu kontrol et.'
    }
    const detail = (err.response.data as { detail?: string } | undefined)?.detail
    if (detail) return detail
  }
  return fallback
}
