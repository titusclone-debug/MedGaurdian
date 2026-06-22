import type { ApiError, UserSession } from './types'

export function getStoredUser(): UserSession | null {
  const savedUser = localStorage.getItem('medguardian_user')
  if (!savedUser) return null
  try {
    return JSON.parse(savedUser)
  } catch {
    return null
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem('medguardian_token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    'Content-Type': 'application/json',
  }
}

export async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  })

  if (response.status === 401) {
    localStorage.removeItem('medguardian_token')
    localStorage.removeItem('medguardian_user')
    window.location.reload()
    throw { message: 'Session expired', status: 401 } satisfies ApiError
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw {
      message: body.detail || `Request failed with status ${response.status}`,
      status: response.status,
    } satisfies ApiError
  }

  return response.json()
}
