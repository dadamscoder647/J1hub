import { FormEvent, useEffect, useState } from 'react';
import { listingsService, verifyService } from '../api/services';
import { ApplicationSummary, Listing, VerificationStatusResponse } from '../types/api';

export function WorkerDashboard() {
  const [status, setStatus] = useState<VerificationStatusResponse | null>(null);
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [waiver, setWaiver] = useState(false);
  const [query, setQuery] = useState('');
  const [listings, setListings] = useState<Listing[]>([]);
  const [message, setMessage] = useState('Interested in this role');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  async function loadStatus() {
    try {
      setStatus(await verifyService.status());
    } catch {
      setError('Failed to load verification status.');
    }
  }

  async function loadApplications() {
    try {
      setApplications(await listingsService.applicationsMine());
    } catch {
      setError('Failed to load your applications.');
    }
  }

  useEffect(() => {
    void loadStatus();
    void loadApplications();
  }, []);

  async function upload(e: FormEvent) {
    e.preventDefault();
    if (!file) return setError('Please choose a file.');
    if (!waiver) return setError('Waiver acknowledgement is required.');
    setLoading(true);
    setError('');
    setResult('');
    try {
      await verifyService.upload(file, waiver);
      setResult('Document uploaded. Verification is pending review.');
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
      setListings(await listingsService.search(query));
    } catch {
      setError('Failed to fetch listings.');
    } finally {
      setLoading(false);
    }
  }

  async function apply(id: number) {
    setError('');
    setResult('');
    try {
      await listingsService.apply(id, message);
      setResult('Application sent. You can follow its status below.');
      await loadApplications();
    } catch {
      setError('Could not apply. Your verification must be approved and the listing must be active.');
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
        <button type="button" onClick={() => void search()}>Search</button>
        {listings.length === 0 && !loading && <p>No listings found.</p>}
        {listings.map((listing) => (
          <article key={listing.id} style={{ border: '1px solid #ddd', margin: '8px 0', padding: 8 }}>
            <h4>{listing.title}</h4>
            <p>{listing.description}</p>
            <input aria-label={`Message for ${listing.title}`} value={message} onChange={(e) => setMessage(e.target.value)} />
            <button type="button" onClick={() => void apply(listing.id)}>Apply</button>
          </article>
        ))}
      </section>

      <section>
        <h3>My Applications</h3>
        {applications.length === 0 && <p>No applications yet.</p>}
        {applications.map((application) => (
          <article key={application.id}>
            <p>Listing #{application.listing_id}: {application.message}</p>
            <p>Status: {application.status}</p>
          </article>
        ))}
      </section>
      {result && <p role="status">{result}</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
