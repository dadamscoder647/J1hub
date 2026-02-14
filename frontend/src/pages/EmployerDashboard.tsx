import { FormEvent, useMemo, useState } from 'react';
import { billingService, listingsService } from '../api/services';

const emptyListing = {
  category: 'job',
  title: '',
  description: '',
  contact_method: 'email',
  contact_value: '',
};

export function EmployerDashboard() {
  const [form, setForm] = useState(emptyListing);
  const [creditsStatus, setCreditsStatus] = useState('Unknown (server has no dedicated status endpoint).');
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const canSubmit = useMemo(() => form.title && form.description && form.contact_value, [form]);

  async function purchase(type: 'listing' | 'subscription') {
    setError('');
    try {
      const data = await billingService.checkout(type, 1);
      setResult(`Checkout session created: ${data.sessionId}`);
    } catch {
      setError('Purchase failed. Check Stripe and billing URL env config.');
    }
  }

  async function createListing(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!canSubmit) return setError('category/title/description/contact fields are required.');
    try {
      await listingsService.create(form);
      setResult('Listing created successfully.');
      setForm(emptyListing);
      setCreditsStatus('Listing creation attempted; credit may have been consumed if no subscription.');
    } catch {
      setError('Failed to create listing. Need credits or active subscription.');
    }
  }

  return (
    <div>
      <h2>Employer Dashboard</h2>
      <p>Credit/subscription status: {creditsStatus}</p>
      <button onClick={() => purchase('listing')}>Purchase listing credit</button>
      <button onClick={() => purchase('subscription')}>Start subscription</button>

      <form onSubmit={createListing}>
        <h3>Create listing</h3>
        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          <option value="job">job</option>
          <option value="housing">housing</option>
          <option value="ride">ride</option>
          <option value="gig">gig</option>
        </select>
        <input placeholder="title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <textarea placeholder="description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input placeholder="contact value" value={form.contact_value} onChange={(e) => setForm({ ...form, contact_value: e.target.value })} />
        <button>Create listing</button>
      </form>

      {result && <p>{result}</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
