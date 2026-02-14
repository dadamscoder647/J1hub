import { client } from './client';
import { AuthResponse, Listing, VerificationStatusResponse } from '../types/api';

export const authService = {
  register: (payload: { email: string; password: string; role: string }) =>
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
  pending: async () => {
    const { data } = await client.get('/admin/verify/pending');
    return data;
  },
  approve: (id: number) => client.post(`/verify/${id}/approve`),
  reject: (id: number, review_note: string) =>
    client.post(`/verify/${id}/reject`, { review_note }),
};

export const listingsService = {
  search: async (q: string) => {
    const { data } = await client.get<{ results: Listing[] }>('/listings', { params: { q } });
    return data.results;
  },
  create: (payload: Record<string, unknown>) => client.post('/listings', payload),
  update: (id: number, payload: Record<string, unknown>) => client.patch(`/listings/${id}`, payload),
  apply: (listingId: number, message: string) => client.post(`/listings/${listingId}/apply`, { message }),
};

export const billingService = {
  checkout: async (purchase_type: 'listing' | 'subscription', quantity = 1) => {
    const { data } = await client.post('/billing/create-checkout-session', { purchase_type, quantity });
    return data;
  },
};
