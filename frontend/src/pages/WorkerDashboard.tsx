import { FormEvent, useEffect, useState } from 'react';
import { listingsService, verifyService } from '../api/services';
import { Listing, VerificationStatusResponse } from '../types/api';

export function WorkerDashboard() {
  const [status, setStatus] = useState<VerificationStatusResponse | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [waiver, setWaiver] = useState(false);
  const [query, setQuery] = useState('');
  const [listings, setListings] = useState<Listing[]>([]);
  const [message, setMessage] = useState('Interested in this role');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadStatus = async () => {
    try {
      setStatus(await verifyService.status());
    } catch {
      setError('Failed to load verification status.');
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  async function upload(e: FormEvent) {
    e.preventDefault();
    if (!file) return setError('Please choose a file.');
    if (!waiver) return setError('Waiver acknowledgement is required.');
    setLoading(true);
    setError('');
    try {
      await verifyService.upload(file, waiver);
      await loadStatus();
    } catch {
      setError('Upload failed. Allowed types: jpeg/jpg/png/pdf; max 10MB.');
    } finally {
      setLoading(false);
    }
  }

  async function search() {
    setLoading(true);
    setError('');
    try {
      const rows = await listingsService.search(query);
      setListings(rows);
    } catch {
      setError('Failed to fetch listings.');
    } finally {
      setLoading(false);
    }
  }

  async function apply(id: number) {
    try {
      await listingsService.apply(id, message);
      alert('Application sent');
    } catch {
      setError('Could not apply. Make sure you are verified and listing is active.');
    }
  }

  return (
    <div>
      <h2>Worker Dashboard</h2>
      <p>Verification: <b>{status?.verification_status ?? 'loading...'}</b></p>

      <form onSubmit={upload}>
        <h3>Upload verification document</h3>
        <input aria-label="document" type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <label>
          <input type="checkbox" checked={waiver} onChange={(e) => setWaiver(e.target.checked)} /> I acknowledge waiver
        </label>
        <button disabled={loading}>{loading ? 'Uploading...' : 'Upload'}</button>
      </form>

      <section>
        <h3>Search Listings</h3>
        <input aria-label="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="search title/company" />
        <button onClick={search}>Search</button>
        {listings.length === 0 && !loading && <p>No listings found.</p>}
        {listings.map((l) => (
          <article key={l.id} style={{ border: '1px solid #ddd', margin: '8px 0', padding: 8 }}>
            <h4>{l.title}</h4>
            <p>{l.description}</p>
            <input value={message} onChange={(e) => setMessage(e.target.value)} />
            <button onClick={() => apply(l.id)}>Apply</button>
          </article>
        ))}
      </section>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
