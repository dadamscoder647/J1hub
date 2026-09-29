import { useEffect, useState } from 'react';
import { verifyService } from '../api/services';
import type { PaginatedResponse, PendingVerificationDocument } from '../types/api';

type PendingPagination = PaginatedResponse<PendingVerificationDocument>['pagination'];

export function AdminDashboard() {
  const [pending, setPending] = useState<PendingVerificationDocument[]>([]);
  const [pagination, setPagination] = useState<PendingPagination | null>(null);
  const [reviewNote, setReviewNote] = useState('Incomplete document');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function load(page = pagination?.page ?? 1) {
    setLoading(true);
    setError('');
    try {
      let response = await verifyService.pending(page);
      const lastPage = response.pagination.total_pages;
      if (lastPage > 0 && page > lastPage) {
        response = await verifyService.pending(lastPage);
      }
      setPending(response.results);
      setPagination(response.pagination);
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
      {pagination && pagination.total > 0 && (
        <nav aria-label="Pending verification pages">
          <button
            type="button"
            disabled={loading || !pagination.has_prev}
            onClick={() => void load(pagination.page - 1)}
          >
            Previous page
          </button>{' '}
          <span role="status">
            Page {pagination.page} of {pagination.total_pages} ({pagination.total} pending)
          </span>{' '}
          <button
            type="button"
            disabled={loading || !pagination.has_next}
            onClick={() => void load(pagination.page + 1)}
          >
            Next page
          </button>
        </nav>
      )}
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
