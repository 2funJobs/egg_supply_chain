<!-- App.vue is the root component — it renders on every page.
     It shows the navigation sidebar (desktop) or bottom bar (mobile),
     and the current page is injected via <RouterView />. -->
<script setup>
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { usePermissions } from './composables/usePermissions'

const { canViewPackages } = usePermissions()

// useRouter() gives you the router instance to navigate programmatically.
// useRoute() gives you the currently active route object (path, params, etc.)
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// Helper: returns true when the current URL matches the given path.
// Used to highlight the active nav item.
const isActive = (path) => route.path === path

const handleLogout = () => {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <!-- min-h-screen ensures the page always fills the full viewport height.
       md:flex-row switches from column (mobile stack) to side-by-side on desktop. -->
  <div class="min-h-screen bg-stone-50 font-sans flex flex-col md:flex-row">

    <!-- =====================================================================
         NAVIGATION — hidden on login page, shown when the user is logged in
         Mobile:  fixed bottom bar (common mobile app pattern)
         Desktop: sticky left sidebar
         ===================================================================== -->
    <nav
      v-if="auth.isAuthenticated"
      class="
        fixed bottom-0 w-full bg-white border-t border-stone-200 px-2 py-2
        flex justify-around items-center z-50
        md:sticky md:top-0 md:h-screen md:w-64 md:flex-col md:justify-start
        md:items-start md:border-t-0 md:border-r md:border-stone-200
        md:px-5 md:py-8 md:gap-1
      "
    >
      <!-- Logo — only visible on desktop sidebar -->
      <div class="hidden md:flex items-center gap-2 w-full mb-10 px-3">
        <span class="text-3xl">🥚</span>
        <h1 class="text-xl font-black tracking-wide text-stone-800">EggChain</h1>
      </div>

      <!-- RouterLink is Vue Router's component for navigation.
           Unlike <a href>, it does client-side routing (no full page reload).
           The :class binding applies styles based on whether the route is active. -->
      <RouterLink
        to="/"
        class="flex flex-col md:flex-row items-center gap-1 md:gap-3 md:w-full
               md:px-4 md:py-3 md:rounded-xl transition-colors px-4 py-1.5"
        :class="isActive('/')
          ? 'text-amber-600 md:bg-amber-50'
          : 'text-stone-400 hover:text-amber-500 md:hover:bg-stone-100'"
      >
        <svg class="w-6 h-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        <span class="text-[10px] md:text-sm font-semibold">Dashboard</span>
      </RouterLink>

      <RouterLink
        to="/pallets"
        class="flex flex-col md:flex-row items-center gap-1 md:gap-3 md:w-full
               md:px-4 md:py-3 md:rounded-xl transition-colors px-4 py-1.5"
        :class="isActive('/pallets')
          ? 'text-amber-600 md:bg-amber-50'
          : 'text-stone-400 hover:text-amber-500 md:hover:bg-stone-100'"
      >
        <svg class="w-6 h-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
        </svg>
        <span class="text-[10px] md:text-sm font-semibold">Pallets</span>
      </RouterLink>

      <RouterLink
        v-if="canViewPackages"
        to="/packages"
        class="flex flex-col md:flex-row items-center gap-1 md:gap-3 md:w-full
               md:px-4 md:py-3 md:rounded-xl transition-colors px-4 py-1.5"
        :class="isActive('/packages')
          ? 'text-amber-600 md:bg-amber-50'
          : 'text-stone-400 hover:text-amber-500 md:hover:bg-stone-100'"
      >
        <svg class="w-6 h-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
        </svg>
        <span class="text-[10px] md:text-sm font-semibold">Packages</span>
      </RouterLink>

      <RouterLink
        to="/ledger"
        class="flex flex-col md:flex-row items-center gap-1 md:gap-3 md:w-full
               md:px-4 md:py-3 md:rounded-xl transition-colors px-4 py-1.5"
        :class="isActive('/ledger')
          ? 'text-amber-600 md:bg-amber-50'
          : 'text-stone-400 hover:text-amber-500 md:hover:bg-stone-100'"
      >
        <svg class="w-6 h-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M13 10V3L4 14h7v7l9-11h-7z"/>
        </svg>
        <span class="text-[10px] md:text-sm font-semibold">Ledger</span>
      </RouterLink>

      <!-- The QR Scan button floats up on mobile (classic mobile FAB pattern) -->
      <div class="relative flex flex-col items-center">
        <RouterLink
          to="/scan"
          class="relative -top-5 md:static md:mt-2 md:w-full
                 bg-amber-600 text-white p-4 md:py-3 md:px-4 rounded-full md:rounded-xl
                 shadow-lg flex items-center justify-center gap-2
                 hover:bg-amber-700 transition-colors"
        >
          <svg class="w-7 h-7 md:w-5 md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01
                 M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm14 0h2a1 1 0
                 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1
                 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
          </svg>
          <span class="hidden md:inline font-bold text-sm">Scan QR</span>
        </RouterLink>
        <span class="text-[10px] font-semibold text-stone-500 mt-1 md:hidden">Scan QR</span>
      </div>

      <!-- User info + logout — desktop sidebar only -->
      <div class="hidden md:flex flex-col gap-2 w-full mt-auto pt-6 border-t border-stone-100">
        <div class="flex items-center gap-3 px-3 mb-2">
          <div class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center
                      text-amber-700 font-black text-lg shrink-0">
            {{ auth.user?.orgName?.charAt(0) || 'U' }}
          </div>
          <div class="min-w-0">
            <p class="text-sm font-bold text-stone-800 truncate">{{ auth.user?.orgName || 'Organization' }}</p>
            <p class="text-xs text-stone-500 capitalize">{{ auth.user?.role?.toLowerCase() || 'user' }}</p>
          </div>
        </div>
        <button
          @click="handleLogout"
          class="flex items-center gap-3 w-full px-4 py-3 rounded-xl
                 text-red-500 hover:bg-red-50 transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
          </svg>
          <span class="text-sm font-semibold">Logout</span>
        </button>
      </div>
    </nav>

    <!-- Main content area. pb-24 adds bottom padding on mobile so content
         isn't hidden behind the fixed bottom nav. -->
    <main class="flex-1 pb-24 md:pb-0 overflow-x-hidden">
      <RouterView />
    </main>

  </div>
</template>
