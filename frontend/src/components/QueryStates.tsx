import type { ReactNode } from 'react';

import { ApiError } from '../api/client';

/** Spinner-free loading placeholder — one per data region. */
export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="state state--loading" role="status">
      {label}
    </div>
  );
}

/** Empty-result message; distinct from loading and error (§3.4). */
export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="state state--empty" role="status">
      {children}
    </div>
  );
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred.';
}

/** Error message with a retry affordance — never shows a raw stack trace. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="state state--error" role="alert">
      <p>{messageFor(error)}</p>
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
