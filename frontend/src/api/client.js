import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

export function getWsBaseUrl() {
  return API_BASE_URL.replace(/^http/, 'ws');
}
