import { FormEvent, useEffect, useMemo, useState } from 'react';
import { billingService, listingsService } from '../api/services';
import { ApplicationSummary, Listing, SubscriptionStatus } from '../types/api';

const emptyListing = {
  category: 'job',
  title: '',
  description: '',
  contact_method: 'email',
  contact_value: '',
};

export function EmployerDashboard() {
  const [form, setForm] = useState(emptyListing);
  const [billingStatus, setBillingStatus] = useState<SubscriptionStatus | null>(null);
  const [billingHistory, setBillingHistory] = useState<Array<{ id: number; event_type: string; created_at: string }>>([]);
  const [ownedListings, setOwnedListings] = useState<Listing[]>([]);
  const [applications, setApplications] = useState<Record<number, ApplicationSummary[]>>({});
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const canSubmit = useMemo(
    () => Boolean(form.title && form.description && form.contact_value),
    [form]
  );

  async function loadDashboard() {
    setLoading(true);
    try {
      const [status, history, listings] = await Promise.all([
        billingService.status(),
        billingService.history(),
        listingsService.mine(),
      ]);
      const applicationRows = await Promise.all(
        listings.map(async (listing) => [listing.id, await listingsService.applicationsFor(listing.id)] as const)
      );
      setBillingStatus(status);
      setBillingHistory(history);
      setOwnedListings(listings);
      setApplications(Object.fromEntries(applicationRows));
      setError('');
    } catch {
      setError('Could not load employer account data.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function purchase(type: 'listing' | 'subscription') {
    setError('');
    try {
      const data = await billingService.checkout(type, 1);
      if (typeof data.url !== 'string' || new URL(data.url).protocol !== 'https:') {
        throw new Error('The checkout URL was missing or insecure.');
      }
      window.location.assign(data.url);
    } catch {
      setError('Could not start secure checkout. Check Stripe and billing URL configuration.');
    }
  }

  async function createListing(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!canSubmit) return setError('Title, description, and contact details are required.');
    try {
      await listingsService.create(form);
      setResult('Listing created successfully.');
      setForm(emptyListing);
      await loadDashboard();
    } catch {
      setError('Failed to create listing. An active subscription or listing credit is required.');
    }
  }

  async function updateApplication(listingId: number, applicationId: number, status: ApplicationSummary['status']) {
    setError('');
    try {
      await listingsService.updateApplication(listingId, applicationId, status);
      setApplications((current) => ({
        ...current,
        [listingId]: (current[listingId] ?? []).map((application) =>
          application.id === applicationId ? { ...application, status } : application
        ),
      }));
    } catch {
      setError('Could not update this application.');
    }
  }

  return (
    <div>
      <h2>Employer Dashboard</h2>
      <p>
        Listing credits: {billingStatus?.listing_credits ?? 'loading'} · Subscription:{' '}
        {billingStatus ? (billingStatus.has_active_subscription ? 'active' : 'inactive') : 'loading'}
        {billingStatus?.active_until ? ` until ${new Date(billingStatus.active_until).toLocaleDateString()}` : ''}
      </p>
      <button onClick={() => void purchase('listing')}>Purchase listing credit</button>
      <button onClick={() => void purchase('subscription')}>Start subscription</button>

      <form onSubmit={createListing}>
        <h3>Create listing</h3>
        <select aria-label="category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          <option value="job">job</option>
          <option value="housing">housing</option>
          <option value="ride">ride</option>
          <option value="gig">gig</option>
        </select>
        <input placeholder="title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <textarea placeholder="description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input placeholder="contact value" value={form.contact_value} onChange={(e) => setForm({ ...form, contact_value: e.target.value })} />
        <button disabled={loading}>Create listing</button>
      </form>

      <section>
        <h3>Applications</h3>
        {ownedListings.length === 0 && !loading && <p>No listings yet.</p>}
        {ownedListings.map((listing) => (
          <article key={listing.id}>
            <h4>{listing.title}</h4>
            {(applications[listing.id] ?? []).length === 0 && <p>No applications yet.</p>}
            {(applications[listing.id] ?? []).map((application) => (
              <div key={application.id}>
                <p>Worker #{application.user_id}: {application.message}</p>
                <label>
                  Status for application #{application.id}{' '}
                  <select
                    aria-label={`Application ${application.id} status`}
                    value={application.status}
                    onChange={(e) => void updateApplication(listing.id, application.id, e.target.value as ApplicationSummary['status'])}
                  >
                    <option value="new">new</option>
                    <option value="reviewing">reviewing</option>
                    <option value="accepted">accepted</option>
                    <option value="rejected">rejected</option>
                  </select>
                </label>
              </div>
            ))}
          </article>
        ))}
      </section>

      <section>
        <h3>Billing history</h3>
        {billingHistory.map((event) => <p key={event.id}>{event.event_type} · {new Date(event.created_at).toLocaleString()}</p>)}
      </section>

      {result && <p role="status">{result}</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
