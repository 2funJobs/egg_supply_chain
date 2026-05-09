import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// () => import(...) is "lazy loading" — the component's JS is only
// downloaded when the user actually navigates to that route.
// This keeps the initial page load fast.
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/pallets',
    name: 'pallets',
    component: () => import('../views/PalletsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/packages',
    name: 'packages',
    component: () => import('../views/PackagesView.vue'),
    beforeEnter: (to, from, next) => {
      const auth = useAuthStore()
      // If they are a Market or Distributor, redirect them to the Pallets page
      if (auth.orgType === 'MARKET' || auth.orgType === 'DISTRIBUTOR') {
        next('/pallets') 
      } else {
        next() // Let them in
      }
    },
    meta: { requiresAuth: true },
  },
  {
    path: '/ledger',
    name: 'ledger',
    component: () => import('../views/LedgerView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/pallets/:qrId',
    name: 'palletDetail',
    component: () => import('../views/PalletDetailView.vue'),
    meta: { requiresAuth: true },
    // :qrId is a dynamic segment — accessed via useRoute().params.qrId
  },
  {
    path: '/packages/:qrId',
    name: 'packageDetail',
    component: () => import('../views/PackageDetailView.vue'),
    meta: { requiresAuth: true },
    // :qrId is a dynamic segment — accessed via useRoute().params.qrId
  },
  {
    path: '/scan',
    name: 'scan',
    component: () => import('../views/HistoryView.vue'),
    // No requiresAuth — this page is public so consumers can scan QR codes
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard: runs before every route change.
// Think of it as middleware — it can redirect the user before the page loads.
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    // Protected route but not logged in → send to login
    next('/login')
  } else if (to.name === 'login' && auth.isAuthenticated) {
    // Already logged in, trying to visit login → redirect to dashboard
    next('/')
  } else {
    next()
  }
})

export default router
