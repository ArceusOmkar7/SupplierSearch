import { vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/** Load an actual recorded API response (see backend/tests/acceptance). */
export function capture<T>(name: string): { etag: string | null; body: T } {
  return JSON.parse(readFileSync(resolve(__dirname, '../../../tests/captures', `${name}.json`), 'utf-8'));
}

export interface Call { method: string; path: string; headers: Headers; body: unknown }

type Handler = (call: Call) => { status?: number; body?: unknown; etag?: string | null } | undefined;

/**
 * Route fetch() to recorded responses. Unhandled requests fail loudly so a component can never
 * silently depend on invented data.
 */
export function mockApi(handlers: Record<string, Handler>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: string, init: RequestInit = {}) => {
    const url = new URL(input, 'http://127.0.0.1');
    const method = init.method ?? 'GET';
    const path = url.pathname.replace('/api/v1', '') + url.search;
    const call: Call = {
      method, path, headers: new Headers(init.headers),
      body: typeof init.body === 'string' ? JSON.parse(init.body) : init.body,
    };
    calls.push(call);
    if (path === '/session') {
      return new Response(JSON.stringify({ buyer_id: 'b', display_name: 'Test buyer', csrf_token: 'csrf', expires_at: '2099-01-01T00:00:00Z' }), { status: 200 });
    }
    const handler = handlers[`${method} ${path}`];
    const result = handler?.(call);
    if (!result) throw new Error(`Unrecorded request: ${method} ${path}`);
    return new Response(result.status === 204 ? null : JSON.stringify(result.body ?? {}), {
      status: result.status ?? 200,
      headers: result.etag ? { ETag: result.etag } : {},
    });
  }));
  return calls;
}

export class FakeEventSource {
  static instances: FakeEventSource[] = [];
  listeners = new Map<string, ((event: MessageEvent<string>) => void)[]>();
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  constructor(public url: string) { FakeEventSource.instances.push(this); queueMicrotask(() => this.onopen?.()); }
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }
  emit(type: string, data: unknown) {
    for (const listener of this.listeners.get(type) ?? []) listener({ data: JSON.stringify(data) } as MessageEvent<string>);
  }
  close() { this.closed = true; }
}
