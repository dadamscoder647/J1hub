import { useEffect, useState } from 'react';
import { verifyService } from '../api/services';

export function AdminDashboard() {
  const [pending, setPending] = useState<Array<{ id: number; filename: string; user_id: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setPending(await verifyService.pending());
    } catch {
      setError('Failed to load pending verification queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  async function approve(id: number) {
    await verifyService.approve(id);
    await load();
  }

  async function reject(id: number) {
    await verifyService.reject(id, 'Incomplete document');
    await load();
  }

  return (
    <div>
      <h2>Admin Dashboard</h2>
      {loading && <p>Loading pending docs...</p>}
      {!loading && pending.length === 0 && <p>No pending documents.</p>}
      {pending.map((doc) => (
        <article key={doc.id} style={{ border: '1px solid #ddd', margin: '8px 0', padding: 8 }}>
          <p>#{doc.id} user={doc.user_id} file={doc.filename}</p>
          <button onClick={() => approve(doc.id)}>Approve</button>
          <button onClick={() => reject(doc.id)}>Reject</button>
        </article>
      ))}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
