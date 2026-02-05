/**
 * Axios API client with interceptors
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000/api';

const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Include cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Only redirect to login on 401 if not already on auth pages
    // and not from the /auth/me endpoint (which is used to check auth state)
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname;
      const isAuthPage = currentPath === '/login' || currentPath === '/register';
      const isAuthMeEndpoint = error.config?.url?.includes('/auth/me');

      // Don't redirect if already on auth page or if it's the /auth/me check
      if (!isAuthPage && !isAuthMeEndpoint) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
