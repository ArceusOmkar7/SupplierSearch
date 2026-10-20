import { useState, type FormEvent } from 'react';
import { ApiError, signIn, type BuyerSession } from '../api/client';

export function Login({ onSignedIn }: { onSignedIn: (session: BuyerSession) => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try { onSignedIn(await signIn(username, password)); }
    catch (failure) {
      setError(failure instanceof ApiError && failure.status === 401
        ? 'The username or password was not accepted.'
        : failure instanceof ApiError ? failure.message : 'Cannot reach the local service. Try again.');
    } finally { setPassword(''); setBusy(false); }
  }

  return <section className="login" aria-labelledby="login-title">
    <h2 id="login-title">Sign in to your workspace</h2>
    <p>Use the buyer account created on this computer.</p>
    <form onSubmit={submit} aria-busy={busy}>
      <label htmlFor="username">Username</label>
      <input id="username" autoComplete="username" required value={username} onChange={event => setUsername(event.target.value)} disabled={busy} />
      <label htmlFor="password">Password</label>
      <input id="password" type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} disabled={busy} />
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
    </form>
  </section>;
}
