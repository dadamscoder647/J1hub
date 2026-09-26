import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!email.includes('@') || password.length < 8) {
      setError('Use a valid email and password length >= 8.');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
      navigate('/');
    } catch {
      setError('Invalid credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <h2>Login</h2>
      <input aria-label="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
      <input aria-label="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" />
      <button disabled={loading}>{loading ? 'Signing in...' : 'Login'}</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
