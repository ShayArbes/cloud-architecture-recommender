/**
 * Typed fetch client. Every API call goes through here; responses are typed by
 * the caller and non-2xx responses raise a structured {@link ApiError} so the
 * UI can show friendly messages (§3.4) rather than raw fetch failures.
 */

import type { ApiErrorEnvelope } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isErrorEnvelope(body: unknown): body is ApiErrorEnvelope {
  return (
    typeof body === 'object' && body !== null && 'error' in body && typeof body.error === 'object'
  );
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON error body — fall through to a generic message.
  }
  if (isErrorEnvelope(body)) {
    const { code, message, details } = body.error;
    return new ApiError(response.status, code, message, details);
  }
  return new ApiError(
    response.status,
    'UNKNOWN_ERROR',
    `Request failed (${String(response.status)})`,
    {},
  );
}

interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  signal?: AbortSignal;
}

export async function apiRequest<TResponse>(
  path: string,
  { method = 'GET', body, signal }: RequestOptions = {},
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiError(0, 'NETWORK_ERROR', 'Could not reach the server.', {
      cause: String(cause),
    });
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as TResponse;
}
