/** Same-origin session client; credentials and private state never enter localStorage. */
export interface BuyerSession {
  buyer_id: string;
  display_name: string;
  csrf_token: string;
  expires_at: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

let csrfToken: string | undefined;
let privateEpoch = 0;
const privateCleanups = new Set<() => void>();

export function registerPrivateCleanup(cleanup: () => void): () => void {
  privateCleanups.add(cleanup);
  return () => { privateCleanups.delete(cleanup); };
}

export function clearPrivateState(): void {
  privateEpoch += 1;
  csrfToken = undefined;
  for (const cleanup of privateCleanups) cleanup();
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  csrf?: string;
  etag?: string;
  idempotencyKey?: string;
  signal?: AbortSignal;
}

export interface ApiResponse<T> { data: T; etag: string | null; }

export async function requestWithMetadata<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const method = options.method ?? 'GET';
  const headers = new Headers();
  if (options.body !== undefined) headers.set('Content-Type', 'application/json');
  if (!['GET', 'HEAD'].includes(method)) {
    const token = options.csrf ?? csrfToken ?? (await getSession()).csrf_token;
    headers.set('X-CSRF-Token', token);
  }
  if (options.etag) headers.set('If-Match', options.etag);
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey);
  const epoch = privateEpoch;
  const response = await fetch(`/api/v1${path}`, {
    method, headers, credentials: 'same-origin', cache: 'no-store', signal: options.signal,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (epoch !== privateEpoch) throw new ApiError(401, 'The session changed. Sign in to continue.');
  if (!response.ok) {
    if (response.status === 401) clearPrivateState();
    const messages: Record<number, string> = {
      401: 'Sign in to continue.',
      403: 'The request could not be authorized. Refresh and try again.',
      404: 'This resource is unavailable.',
      409: 'This action conflicts with an earlier request.',
      412: 'This item changed. Reload it before continuing.',
      429: 'Too many attempts. Wait a few minutes and try again.',
      503: 'A local service is unavailable. Try again after it starts.',
    };
    throw new ApiError(response.status, messages[response.status] ?? 'The request could not be completed.');
  }
  const result = response.status === 204 ? undefined as T : await response.json() as T;
  if (epoch !== privateEpoch) throw new ApiError(401, 'The session changed. Sign in to continue.');
  return { data: result, etag: response.headers.get('ETag') };
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return (await requestWithMetadata<T>(path, options)).data;
}

export async function getSession(signal?: AbortSignal): Promise<BuyerSession> {
  const session = await request<BuyerSession>('/session', { signal });
  csrfToken = session.csrf_token;
  return session;
}

export async function signIn(username: string, password: string): Promise<BuyerSession> {
  const bootstrap = await request<{ csrf_token: string }>('/auth/csrf');
  const session = await request<BuyerSession>('/auth/login', {
    method: 'POST', body: { username, password }, csrf: bootstrap.csrf_token,
  });
  clearPrivateState();
  csrfToken = session.csrf_token;
  return session;
}

export async function signOut(): Promise<void> {
  const token = csrfToken ?? (await getSession()).csrf_token;
  clearPrivateState();
  try { await request<void>('/auth/logout', { method: 'POST', csrf: token }); }
  finally { clearPrivateState(); }
}
