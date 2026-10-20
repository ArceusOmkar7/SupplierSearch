/** Transport/security controls only: these tests contain no supplier/source/evidence records. */
import { afterEach, expect, test, vi } from 'vitest';
import { ApiError, clearPrivateState, registerPrivateCleanup, request, requestWithMetadata } from './client';

afterEach(() => { clearPrivateState(); vi.unstubAllGlobals(); });

test('logout clears registered private caches and streams', () => {
  const cleanup = vi.fn();
  const unregister = registerPrivateCleanup(cleanup);
  clearPrivateState();
  expect(cleanup).toHaveBeenCalledOnce();
  unregister();
  clearPrivateState();
  expect(cleanup).toHaveBeenCalledOnce();
});

test('an in-flight response cannot restore private state after logout', async () => {
  let finish!: (value: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const pending = request('/session');
  const rejected = expect(pending).rejects.toMatchObject({ status: 401 });
  clearPrivateState();
  finish(new Response('{}', { status: 200 }));
  await rejected;
});

test('unauthenticated responses clear private state and use a safe error', async () => {
  const cleanup = vi.fn();
  const unregister = registerPrivateCleanup(cleanup);
  vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 401 })));
  await expect(request('/session')).rejects.toBeInstanceOf(ApiError);
  expect(cleanup).toHaveBeenCalledOnce();
  unregister();
});

test('the exact server ETag is available to subsequent conditional edits', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 200, headers: { ETag: '"control-version"' } })));
  const result = await requestWithMetadata('/control');
  expect(result.etag).toBe('"control-version"');
});
