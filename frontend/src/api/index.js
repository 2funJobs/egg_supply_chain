import axios from 'axios'
import { useAuthStore } from '../stores/auth'

// One axios instance for the whole app. All requests share the same
// baseURL, so we only ever write '/pallets/' not the full URL.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
})

// Request interceptor: runs before every request.
// Grabs the JWT from localStorage and attaches it as a Bearer token.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor: runs after every response.
// Intercepts 401 errors, attempts to refresh the token, and retries the request.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If the server returns 401 (token expired) AND we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      
      // 1. Mark this request so we don't end up in an infinite retry loop
      originalRequest._retry = true

      try {
        // 2. Instantiate the store INSIDE the interceptor to avoid circular dependency errors
        // (because auth.js imports api.js, and api.js imports auth.js)
        const authStore = useAuthStore()

        // 3. Ask the store to fetch a new token
        const newAccessToken = await authStore.refreshAccessToken()

        // 4. Update the failed request with the brand new token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`

        // 5. Retry the original request seamlessly
        return api(originalRequest)

      } catch (refreshError) {
        // 6. If the refresh token fails (it's expired or invalid), kick them to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    // Pass along any other errors (400, 404, 500, etc.)
    return Promise.reject(error)
  }
)

// --- Resource-scoped API objects ---
// Group related calls together so imports are clean:
// import { pallets, blockchain } from '../api'

export const pallets = {
  list: (params) => api.get('/pallets/', { params }),
  get: (qrId) => api.get(`/pallets/${qrId}/`),
  create: (data) => api.post('/pallets/', data),
  transfer: (qrId, data) => api.patch(`/pallets/${qrId}/transfer/`, data),
  iotData: (qrId, data) => api.post(`/pallets/${qrId}/iot-data/`, data),
}

export const packages = {
  list: () => api.get('/packages/'),
  get: (qrId) => api.get(`/packages/${qrId}/`),
  history: (qrId) => api.get(`/packages/${qrId}/history/`),
  create: (data) => api.post('/packages/', data),
}

export const blockchain = {
  list: (params) => api.get('/blockchain-logs/', { params }),
  get: (txHash) => api.get(`/blockchain-logs/${txHash}/`),
}

export const organizations = {
  list: (params = {}) => api.get('/organizations/', { params }),
  get: (code) => api.get(`/organizations/${code}/`),
}

export const certificates = {
  list: () => api.get('/certificates/'),
  create: (data) => api.post('/certificates/', data),
}

export default api
