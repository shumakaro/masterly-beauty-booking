export class ApiError extends Error {
  readonly status: number
  constructor(status: number) {
    super(`API request failed (${status})`)
    this.status = status
  }
}

const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined

export async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  if (!baseUrl) throw new Error('VITE_API_BASE_URL is not configured')
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`, {
    signal,
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new ApiError(response.status)
  return response.json() as Promise<T>
}

