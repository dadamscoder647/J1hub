import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 20 }}>
      <header style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <Link to="/">Home</Link>
        {!user && <Link to="/login">Login</Link>}
        {!user && <Link to="/register">Register</Link>}
        {user?.role === 'worker' && <Link to="/worker">Worker Dashboard</Link>}
        {user?.role === 'employer' && <Link to="/employer">Employer Dashboard</Link>}
        {user?.role === 'admin' && <Link to="/admin">Admin Dashboard</Link>}
        {user && (
          <button onClick={logout} style={{ marginLeft: 'auto' }}>
            Logout ({user.email})
          </button>
        )}
      </header>
      <hr />
      <Outlet />
    </div>
  );
}
