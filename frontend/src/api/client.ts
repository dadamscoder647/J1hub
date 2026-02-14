import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import { storage } from '../utils/storage';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
const refreshEndpoint = import.meta.env.VITE_REFRESH_ENDPOINT || '/auth/refresh';

const client = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshToken() {
  if (!refreshPromise) {
    refreshPromise = client
      .post(refreshEndpoint)
      .then((res) => res.data?.access_token ?? null)
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

client.interceptors.request.use((config) => {
  const token = storage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      const token = await refreshToken();
      if (token) {
        storage.setAccessToken(token);
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${token}`;
        return client(original);
      }
      storage.clearAll();
    }
    return Promise.reject(error);
  }
);

export { client };
