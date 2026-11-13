export interface Slot {
  id: string
  provider: string
  start: string
  end: string
  available: boolean
}

export interface Booking {
  id: string
  slot_id: string
  name: string
  email: string
  status: 'confirmed' | 'cancelled'
  created_at: string
}

export interface NewBooking {
  slot_id: string
  name: string
  email: string
}

const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const API_KEY = import.meta.env.VITE_API_KEY ?? ''

/** An error response from the API: {"error": "<message>"} */
export class ApiError extends Error {
  status: number
  retryAfter: number | null

  constructor(message: string, status: number, retryAfter: number | null = null) {
    super(message)
    this.status = status
    this.retryAfter = retryAfter
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
        ...init.headers,
      },
    })
  } catch {
    throw new ApiError('Could not reach the booking service. Please try again.', 0)
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const retryAfter = Number(response.headers.get('Retry-After')) || null
    throw new ApiError(body?.error ?? 'Something went wrong.', response.status, retryAfter)
  }
  return body as T
}

export async function listSlots(): Promise<Slot[]> {
  const body = await request<{ slots: Slot[] }>('/slots')
  return body.slots
}

/** The Idempotency-Key makes a retried or double-clicked request book only once. */
export function createBooking(input: NewBooking, idempotencyKey: string): Promise<Booking> {
  return request<Booking>('/bookings', {
    method: 'POST',
    body: JSON.stringify(input),
    headers: { 'Idempotency-Key': idempotencyKey },
  })
}
