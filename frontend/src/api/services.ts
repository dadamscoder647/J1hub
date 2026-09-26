import { client } from './client';
import {
  ApplicationSummary,
  AuthResponse,
  Listing,
  PaginatedResponse,
  PendingVerificationDocument,
  SubscriptionStatus,
  VerificationStatusResponse,
} from '../types/api';

export const authService = {
  register: (payload: { email: string; password: string; role: 'worker' | 'employer' }) =>
    client.post('/auth/register', payload),
  login: async (payload: { email: string; password: string }) => {
    const { data } = await client.post<AuthResponse>('/auth/login', payload);
    return data;
  },
};

export const verifyService = {
  upload: (document: File, waiver: boolean) => {
    const form = new FormData();
    form.append('document', document);
    form.append('waiver', String(waiver));
    return client.post('/verify/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  status: async () => {
    const { data } = await client.get<VerificationStatusResponse>('/verify/status');
    return data;
  },
  pending: async (page = 1, perPage = 20) => {
    const { data } = await client.get<PaginatedResponse<PendingVerificationDocument>>(
      '/admin/verify/pending',
      { params: { page, per_page: perPage } }
    );
    return data;
  },
  download: (id: number) => client.get<Blob>(`/verify/doc/${id}`, { responseType: 'blob' }),
  approve: (id: number) => client.post(`/admin/verify/${id}/approve`),
  reject: (id: number, review_note: string) =>
    client.post(`/admin/verify/${id}/reject`, { review_note }),
};

export const listingsService = {
  search: async (q: string) => {
    const { data } = await client.get<{ results: Listing[] }>('/listings', { params: { q } });
    return data.results;
  },
  create: (payload: Record<string, unknown>) => client.post('/listings', payload),
  mine: async () => {
    const { data } = await client.get<{ results: Listing[] }>('/listings/mine');
    return data.results;
  },
  update: (id: number, payload: Record<string, unknown>) => client.patch(`/listings/${id}`, payload),
  apply: (listingId: number, message: string) => client.post(`/listings/${listingId}/apply`, { message }),
  applicationsFor: async (listingId: number) => {
    const { data } = await client.get<{ results: ApplicationSummary[] }>(`/listings/${listingId}/applications`);
    return data.results;
  },
  applicationsMine: async () => {
    const { data } = await client.get<{ results: ApplicationSummary[] }>('/listings/applications/mine');
    return data.results;
  },
  updateApplication: (listingId: number, applicationId: number, status: ApplicationSummary['status']) =>
    client.patch(`/listings/${listingId}/applications/${applicationId}`, { status }),
};

export const billingService = {
  checkout: async (purchase_type: 'listing' | 'subscription', quantity = 1) => {
    const { data } = await client.post('/billing/create-checkout-session', { purchase_type, quantity });
    return data;
  },
  status: async () => {
    const { data } = await client.get<SubscriptionStatus>('/billing/status');
    return data;
  },
  history: async () => {
    const { data } = await client.get<{ events: Array<{ id: number; event_type: string; created_at: string }> }>('/billing/history');
    return data.events;
  },
};
