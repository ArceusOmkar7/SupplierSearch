import { clearPrivateState, registerPrivateCleanup } from './client';
import type { CaseEvent } from './types';

export type StreamStatus = 'connecting' | 'open' | 'reconnecting' | 'closed';

const EVENT_TYPES = [
  'message.created', 'revision.updated', 'revision.confirmed', 'checklist.ready',
  'checklist.confirmed', 'run.queued', 'run.progress', 'check.completed', 'action.required',
  'action.resolved', 'snapshot.ready', 'report.ready', 'case.closed', 'case.deleting',
] as const;

export interface CaseStreamHandlers {
  onEvent: (event: CaseEvent) => void;
  /** The server could not replay from our cursor: refetch current authorized state. */
  onReset: () => void;
  onStatus: (status: StreamStatus) => void;
}

/**
 * Subscribe to a case's durable event stream. The browser resends Last-Event-ID on its own
 * reconnects, events are deduplicated by sequence, and a reconnect never issues a command.
 * Logout (any private-state clear) closes the stream immediately.
 */
export function openCaseEvents(caseId: string, handlers: CaseStreamHandlers): () => void {
  let last = 0;
  let closed = false;
  handlers.onStatus('connecting');
  const source = new EventSource(`/api/v1/cases/${caseId}/events`, { withCredentials: true });
  const stop = () => {
    if (closed) return;
    closed = true;
    source.close();
    unregister();
    handlers.onStatus('closed');
  };
  const unregister = registerPrivateCleanup(stop);
  source.onopen = () => handlers.onStatus('open');
  source.onerror = () => { if (!closed) handlers.onStatus('reconnecting'); };
  for (const type of EVENT_TYPES) {
    source.addEventListener(type, message => {
      const event = JSON.parse((message as MessageEvent<string>).data) as CaseEvent;
      if (event.sequence <= last) return;
      last = event.sequence;
      handlers.onEvent(event);
    });
  }
  source.addEventListener('reset', () => handlers.onReset());
  source.addEventListener('close', () => {
    // The server closes a stream whose session ended; confirm by probing the session.
    stop();
    fetch('/api/v1/session', { credentials: 'same-origin', cache: 'no-store' })
      .then(response => { if (response.status === 401) clearPrivateState(); })
      .catch(() => undefined);
  });
  return stop;
}
