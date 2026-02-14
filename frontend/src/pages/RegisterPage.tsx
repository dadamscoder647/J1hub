import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../api/services';

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('worker');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!email.includes('@')) return setError('Email is required.');
    if (password.length < 8) return setError('Password must be at least 8 characters.');
    setLoading(true);
    try {
      await authService.register({ email: email.trim().toLowerCase(), password, role });
      navigate('/login');
    } catch {
      setError('Registration failed. Email may already exist.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <h2>Register</h2>
      <input aria-label="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
      <input aria-label="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" />
      <select aria-label="role" value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="worker">worker</option>
        <option value="employer">employer</option>
        <option value="admin">admin</option>
      </select>
      <button disabled={loading}>{loading ? 'Creating account...' : 'Register'}</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
