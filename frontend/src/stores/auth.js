import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { jwtDecode } from 'jwt-decode'
import api from '../api'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  // --- State ---
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || null)

  // The JWT only carries org_code and org_name — NOT the org type.
  // We fetch it separately after login so we can drive role-based UI.
  const orgType = ref(null) // 'PRODUCER' | 'DISTRIBUTOR' | 'MARKET' | 'INSPECTOR'

  // --- Getters (computed properties on the store) ---
  const isAuthenticated = computed(() => !!accessToken.value)
  const userRole = computed(() => user.value?.role || null)

  // --- Actions ---
  const login = async (email, password) => {
    // The login endpoint doesn't need a token (it IS the token endpoint),
    // but it still goes through the api instance so baseURL is consistent.
    const response = await api.post('/auth/login/', { email, password })
    const { access, refresh } = response.data

    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    accessToken.value = access

    // Attach the token to every future request via the axios instance default
    api.defaults.headers.common['Authorization'] = `Bearer ${access}`

    decodeUserFromToken(access)

    // Now that user.value has orgCode, fetch the org type.
    // await so the caller can rely on orgType being set when login() resolves.
    if (user.value?.orgCode) {
      await fetchOrgType(user.value.orgCode)
    }
  }

  const refreshAccessToken = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) throw new Error('No refresh token available')

      // Use plain axios to bypass the interceptor and prevent infinite loops.
      // Make sure to use your actual API base URL here.
      const response = await axios.post(`${api.defaults.baseURL}/auth/refresh/`, {
        refresh: refreshToken
      })

      const newAccess = response.data.access
      
      // Update state and storage with the new access token
      localStorage.setItem('access_token', newAccess)
      accessToken.value = newAccess
      api.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`

      decodeUserFromToken(newAccess)
      return newAccess

    } catch (error) {
      console.error('Session expired. Please log in again.', error)
      logout() // If the refresh token is also expired, wipe everything.
      throw error
    }
  }

  const decodeUserFromToken = (token) => {
    try {
      const decoded = jwtDecode(token)
      user.value = {
        id:      decoded.user_id,
        role:    decoded.role,
        orgCode: decoded.org_code,
        orgName: decoded.org_name,
      }
    } catch (error) {
      console.error('Failed to decode token', error)
    }
  }

  // Fetches the organization_type for the user's org.
  // Non-critical: if it fails, permissions just default to false — no crash.
  const fetchOrgType = async (orgCode) => {
    if (!orgCode) return
    try {
      const res = await api.get('/organizations/')
      const orgs = Array.isArray(res.data) ? res.data : (res.data.results || [])
      const org = orgs.find((o) => o.org_code === orgCode)
      if (org) orgType.value = org.organization_type
    } catch {
      // Swallow silently — the user is still logged in, just without org-type-gated UI
    }
  }

  const logout = () => {
    user.value = null
    accessToken.value = null
    orgType.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    delete api.defaults.headers.common['Authorization']
    window.location.href = '/login'
  }

  // Restore state on page refresh (the store is recreated from scratch each time)
  if (accessToken.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${accessToken.value}`
    decodeUserFromToken(accessToken.value)
    if (user.value?.orgCode) {
      // Fire-and-forget: don't block the page from loading
      fetchOrgType(user.value.orgCode)
    }
  }

  return { user, accessToken, orgType, isAuthenticated, userRole, login, logout, refreshAccessToken }
})
