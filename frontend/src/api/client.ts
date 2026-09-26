import axios, { AxiosError } from 'axios';
import { storage } from '../utils/storage';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1';

const client = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
});

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
    if (error.response?.status === 401) {
      storage.clearAll();
    }
    return Promise.reject(error);
  }
);

export { client };
