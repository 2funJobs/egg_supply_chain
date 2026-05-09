<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePermissions } from '../composables/usePermissions'
import { pallets as palletsApi, blockchain as blockchainApi, packages as packagesApi } from '../api'
import StatCard from '../components/StatCard.vue'
import PalletCard from '../components/PalletCard.vue'

const router = useRouter()
const auth = useAuthStore()

// Call the composable — destructure only the booleans this view needs
const { canCreatePallet, canTransferPallet, canCreateCertificate } = usePermissions()

const recentPallets = ref([])
const stats = ref({ pallets: 0, transactions: 0 })
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const [palletsRes, logsRes] = await Promise.all([
      palletsApi.list(),
      blockchainApi.list(),
    ])
    const pd = palletsRes.data
    const ld = logsRes.data
    const allPallets = Array.isArray(pd) ? pd : (pd.results || [])
    stats.value.pallets      = Array.isArray(pd) ? pd.length : (pd.count ?? allPallets.length)
    stats.value.transactions = Array.isArray(ld) ? ld.length : (ld.count ?? (ld.results?.length ?? 0))
    recentPallets.value = allPallets.slice(0, 4)
  } catch {
    error.value = 'Could not connect to the backend. Make sure Django is running on port 8000.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="w-full max-w-4xl mx-auto">

    <!-- HEADER -->
    <div class="bg-gradient-to-br from-amber-600 to-orange-800 pt-10 pb-10 px-6 rounded-b-[40px] shadow-lg">
      <div class="flex justify-between items-center mb-7">
        <div class="flex items-center gap-2">
          <span class="text-3xl">🥚</span>
          <h1 class="text-2xl font-black text-white tracking-wide">EggChain</h1>
        </div>
        <div class="flex items-center gap-2">
          <div class="bg-white/20 px-3 py-1.5 rounded-full">
            <span class="text-white/90 text-xs font-bold capitalize">
              {{ auth.user?.role?.toLowerCase()?.replace('_', ' ') || 'user' }}
            </span>
          </div>
          <div class="w-9 h-9 rounded-full bg-white/25 flex items-center justify-center
                      text-white font-black text-base border-2 border-white/40">
            {{ auth.user?.orgName?.charAt(0) || 'U' }}
          </div>
        </div>
      </div>

      <!-- Welcome card -->
      <div class="bg-white/15 backdrop-blur-md rounded-2xl p-5 border border-white/20 mb-5">
        <p class="text-amber-100 text-sm mb-0.5">Welcome back,</p>
        <h2 class="text-white text-xl font-black">{{ auth.user?.orgName || 'Your Organization' }}</h2>
        <p class="text-white/50 text-xs mt-1 font-mono">{{ auth.user?.orgCode }}</p>
      </div>

      <!-- Stats row — uses the StatCard component -->
      <div class="grid grid-cols-3 gap-3">
        <StatCard label="Pallets"   :value="stats.pallets"       :loading="loading" />
        <StatCard label="Tx Logs"   :value="stats.transactions"  :loading="loading" />
        <StatCard label="Chain OK"  emoji="🔗" />
      </div>
    </div>

    <!-- CONTENT -->
    <div class="px-5 py-6 space-y-7">

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex gap-3">
        <span class="shrink-0">⚠️</span>
        <p>{{ error }}</p>
      </div>

      <!-- ============================================================
           QUICK ACTIONS — role-based: only show what the user can do
           v-if on each action hides it when the user lacks permission.
           All users see the base 3; extras appear based on org type.
           ============================================================ -->
      <div>
        <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-3">Quick Actions</h3>
        <div class="grid grid-cols-3 gap-3">

          <!-- Always visible -->
          <button @click="router.push('/pallets')"
            class="bg-white rounded-2xl p-4 shadow-sm border border-stone-100 flex flex-col
                   items-center gap-2.5 hover:shadow-md hover:border-amber-200 transition-all active:scale-95">
            <div class="bg-amber-50 text-amber-600 p-3 rounded-xl">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
              </svg>
            </div>
            <span class="text-xs font-bold text-stone-700">Pallets</span>
          </button>

          <button @click="router.push('/scan')"
            class="bg-white rounded-2xl p-4 shadow-sm border border-stone-100 flex flex-col
                   items-center gap-2.5 hover:shadow-md hover:border-emerald-200 transition-all active:scale-95">
            <div class="bg-emerald-50 text-emerald-600 p-3 rounded-xl">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01
                     M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm14 0h2a1 1 0
                     001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1
                     1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
              </svg>
            </div>
            <span class="text-xs font-bold text-stone-700">Scan QR</span>
          </button>

          <!-- PRODUCER only: create a new pallet -->
          <button
            v-if="canCreatePallet"
            @click="router.push('/pallets')"
            class="bg-amber-600 rounded-2xl p-4 shadow-sm flex flex-col
                   items-center gap-2.5 hover:bg-amber-700 transition-all active:scale-95">
            <div class="bg-white/20 text-white p-3 rounded-xl">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
            </div>
            <span class="text-xs font-bold text-white">New Pallet</span>
          </button>

          <button
            v-if="canCreatePallet"
            @click="router.push('/packages')"
            class="bg-amber-600 rounded-2xl p-4 shadow-sm flex flex-col
                   items-center gap-2.5 hover:bg-amber-700 transition-all active:scale-95">
            <div class="bg-white/20 text-white p-3 rounded-xl">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
            </div>
            <span class="text-xs font-bold text-white">New Package</span>
          </button>

          <button 
            v-if="canCreatePallet" 
            @click="router.push('/ledger')"
            class="bg-white rounded-2xl p-4 shadow-sm border border-stone-100 flex flex-col
                   items-center gap-2.5 hover:shadow-md hover:border-purple-200 transition-all active:scale-95">
            <div class="bg-purple-50 text-purple-600 p-3 rounded-xl">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
            </div>
            <span class="text-xs font-bold text-stone-700">Ledger</span>
          </button>

          <!-- DISTRIBUTOR / MARKET only: transfer pallets -->
          <button
            v-if="canTransferPallet"
            @click="router.push('/pallets')"
            class="bg-stone-700 rounded-2xl p-4 shadow-sm flex flex-col
                   items-center gap-2.5 hover:bg-stone-800 transition-all active:scale-95">
            <div class="bg-white/20 text-white p-3 rounded-xl">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
              </svg>
            </div>
            <span class="text-xs font-bold text-white">Transfer</span>
          </button>

          <!-- INSPECTOR / VET only: issue certificates -->
          <button
            v-if="canCreateCertificate"
            @click="router.push('/pallets')"
            class="bg-emerald-700 rounded-2xl p-4 shadow-sm flex flex-col
                   items-center gap-2.5 hover:bg-emerald-800 transition-all active:scale-95">
            <div class="bg-white/20 text-white p-3 rounded-xl">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0
                     3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946
                     3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138
                     3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806
                     3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438
                     3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"/>
              </svg>
            </div>
            <span class="text-xs font-bold text-white">Certificate</span>
          </button>
        </div>
      </div>

      <!-- RECENT PALLETS — uses PalletCard component -->
      <div>
        <div class="flex justify-between items-center mb-3">
          <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest">Recent Pallets</h3>
          <button @click="router.push('/pallets')" class="text-xs font-bold text-amber-600 hover:text-amber-700">
            See all →
          </button>
        </div>

        <div v-if="loading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="bg-white rounded-2xl h-20 animate-pulse border border-stone-100"></div>
        </div>

        <div v-else-if="recentPallets.length === 0 && !error"
             class="bg-white rounded-2xl p-10 text-center border border-stone-100 shadow-sm">
          <div class="text-5xl mb-3">📦</div>
          <p class="text-stone-600 font-bold">No pallets yet</p>
          <p class="text-stone-400 text-sm mt-1">Create your first pallet to get started</p>
        </div>

        <!-- PalletCard component used here — simple, no footer slot needed -->
        <div v-else class="space-y-3">
          <PalletCard
            v-for="pallet in recentPallets"
            :key="pallet.master_qr_id"
            :pallet="pallet"
            @click="router.push('/pallets')"
          />
        </div>
      </div>

      <div class="h-4"></div>
    </div>
  </div>
</template>
