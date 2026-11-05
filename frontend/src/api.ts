import type { AppSettings, Evidence, EvidenceDetail, Match, Signature } from './types'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8001'

export class ApiError extends Error {
  code: string
  fields: string[]
  status: number
  constructor(message: string, code: string, status: number, fields: string[] = []) {
    super(message)
    this.code = code
    this.status = status
    this.fields = fields
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText, code: 'http_error' }))
    throw new ApiError(body.detail ?? 'permintaan gagal', body.code ?? 'http_error', res.status, body.fields ?? [])
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  list: () => call<Evidence[]>('/api/evidence'),
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return call<EvidenceDetail>('/api/evidence', { method: 'POST', body: form })
  },
  detail: (id: string) => call<EvidenceDetail>(`/api/evidence/${id}`),
  signature: (id: string) => call<Signature>(`/api/evidence/${id}/signature`),
  matches: (id: string) => call<Match[]>(`/api/evidence/${id}/matches`),
  remove: (id: string) => call<void>(`/api/evidence/${id}`, { method: 'DELETE' }),
  settings: () => call<AppSettings>('/api/settings'),
  updateSettings: (maxUploadMb: number) =>
    call<AppSettings>('/api/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_upload_mb: maxUploadMb }),
    }),
}
