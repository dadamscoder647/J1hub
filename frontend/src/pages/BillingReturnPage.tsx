import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { billingService } from '../api/services';
import { SubscriptionStatus } from '../types/api';

export function BillingReturnPage({ cancelled = false }: { cancelled?: boolean }) {
  const { user } = useAuth();
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [error, setError] = useState('');

  async function refreshStatus() {
    setError('');
    try {
      setStatus(await billingService.status());
    } catch {
      setError('Billing status is not available yet. Return to the employer dashboard and refresh shortly.');
    }
  }

  useEffect(() => {
    if (!cancelled && user?.role === 'employer') void refreshStatus();
  }, [cancelled, user?.role]);

  return (
    <section>
      <h2>{cancelled ? 'Checkout cancelled' : 'Checkout returned'}</h2>
      {cancelled ? (
        <p>No purchase was completed in this checkout session.</p>
      ) : (
        <>
          <p>Stripe returned to J1Hub. Credits and subscription access appear after the signed webhook is processed.</p>
          {status && <p>Current credits: {status.listing_credits}; subscription: {status.has_active_subscription ? 'active' : 'inactive'}.</p>}
          {error && <p role="status">{error}</p>}
          {user?.role === 'employer' && <button onClick={() => void refreshStatus()}>Refresh billing status</button>}
        </>
      )}
      <p><Link to={user?.role === 'employer' ? '/employer' : '/'}>Continue to J1Hub</Link></p>
    </section>
  );
}
