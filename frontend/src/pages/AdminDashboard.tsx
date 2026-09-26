import { useEffect, useState } from 'react';
import { verifyService } from '../api/services';
import { PendingVerificationDocument } from '../types/api';

export function AdminDashboard() {
  const [pending, setPending] = useState<PendingVerificationDocument[]>([]);
  const [reviewNote, setReviewNote] = useState('Incomplete document');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const response = await verifyService.pending();
      setPending(response.results);
    } catch {
      setError('Failed to load pending verification documents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function decide(id: number, decision: 'approve' | 'reject') {
    setError('');
    try {
      if (decision === 'approve') await verifyService.approve(id);
      else await verifyService.reject(id, reviewNote);
      await load();
    } catch {
      setError(`Could not ${decision} this document.`);
    }
  }

  async function download(document: PendingVerificationDocument) {
    setError('');
    try {
      const { data } = await verifyService.download(document.id);
      const url = URL.createObjectURL(data);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = document.filename;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setError('Could not download this document.');
    }
  }

  return (
    <div>
      <h2>Admin Dashboard</h2>
      <label>
        Rejection note{' '}
        <input value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} />
      </label>
      {loading && <p>Loading pending documents...</p>}
      {!loading && pending.length === 0 && <p>No pending documents.</p>}
      {pending.map((doc) => (
        <article key={doc.id} style={{ border: '1px solid #ddd', margin: '8px 0', padding: 8 }}>
          <p>#{doc.id} user={doc.user_id} file={doc.filename}</p>
          <button onClick={() => void download(doc)}>Download</button>
          <button onClick={() => void decide(doc.id, 'approve')}>Approve</button>
          <button onClick={() => void decide(doc.id, 'reject')}>Reject</button>
        </article>
      ))}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
