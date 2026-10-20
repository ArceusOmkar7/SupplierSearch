import { useEffect, useState } from 'react';
import { ApiError, getSession, registerPrivateCleanup, signOut, type BuyerSession } from '../api/client';
import { CaseWorkspace } from './CaseWorkspace';
import { Login } from './Login';

export function App() {
  const [session, setSession] = useState<BuyerSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    const unregister = registerPrivateCleanup(() => setSession(null));
    getSession(controller.signal).then(setSession).catch(failure => {
      if (!controller.signal.aborted && !(failure instanceof ApiError && failure.status === 401)) {
        setError('Cannot reach the local service. Refresh after it starts.');
      }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); unregister(); };
  }, []);

  async function logout() {
    setError('');
    setSession(null);
    try { await signOut(); }
    catch { setError('Server sign out could not be confirmed.'); }
  }

  return <main>
    <header><h1>VeriSource</h1><p>Supplier verification</p></header>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Opening your workspace…</p>
      : session ? <section aria-label="Private workspace">
        <p>Signed in as {session.display_name}</p>
        <button type="button" onClick={logout}>Sign out</button>
        <CaseWorkspace />
      </section> : <Login onSignedIn={setSession} />}
  </main>;
}
