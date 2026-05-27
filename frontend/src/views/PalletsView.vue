<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { pallets as palletsApi } from '../api'
import { usePermissions } from '../composables/usePermissions'
import PalletCard from '../components/PalletCard.vue'
import CreatePalletModal from '../components/CreatePalletModal.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const { canCreatePallet, canTransferPallet } = usePermissions()


const allPallets    = ref([])
const loading       = ref(true)
const error         = ref(null)
const activeFilter  = ref('ALL')
const searchQuery   = ref('')
const showModal     = ref(false)  // controls CreatePalletModal visibility

const filters = [
  { label: 'All',           value: 'ALL' },
  { label: 'In Production', value: 'IN_PRODUCTION' },
  { label: 'In Transit',    value: 'IN_TRANSIT' },
  { label: 'At Market',     value: 'AT_MARKET' },
  { label: 'Faulty',        value: 'FAULTY' },
]

const filteredPallets = computed(() => {
  let result = allPallets.value
  if (activeFilter.value !== 'ALL') {
    result = result.filter((p) => p.status === activeFilter.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter((p) => p.master_qr_id.toLowerCase().includes(q))
  }
  return result
})

const formatDate = (str) => {
  if (!str) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  }).format(new Date(str))
}

// Called when the modal emits 'created'.
// Prepend the new pallet to the list so it appears immediately at the top,
// then navigate to its detail page.
const onPalletCreated = (newPallet) => {
  allPallets.value.unshift(newPallet)
  showModal.value = false
  router.push(`/pallets/${newPallet.master_qr_id}`)
}



onMounted(async () => {
  try {
    const palletQueryParams = {}

    if (auth.user?.role === 'PRODUCER') {
      palletQueryParams.producer__org_code = auth.user?.orgCode
    }

    const [palletsRes] = await Promise.all([
      palletsApi.list(palletQueryParams),
    ])
    allPallets.value = Array.isArray(palletsRes.data) ? palletsRes.data : (palletsRes.data.results ?? [])
  } catch {
    error.value = 'Failed to load pallets. Is the Django server running?'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="w-full max-w-4xl mx-auto">

    <!-- HEADER -->
    <div class="bg-gradient-to-br from-stone-700 to-stone-900 pt-10 pb-8 px-6 rounded-b-[32px] shadow-lg">
      <div class="flex justify-between items-start mb-5">
        <div>
          <h1 class="text-2xl font-black text-white">Pallets</h1>
          <p class="text-stone-400 text-sm mt-1">
            {{ loading ? 'Loading…' : `${allPallets.length} pallets total` }}
          </p>
        </div>
        <!-- Only PRODUCER staff/admins see this button.
             Clicking sets showModal = true, which renders CreatePalletModal below. -->
        <button
          v-if="canCreatePallet"
          @click="showModal = true"
          class="bg-amber-500 text-white px-4 py-2.5 rounded-xl font-bold text-sm
                 hover:bg-amber-600 transition-colors flex items-center gap-2 shrink-0"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          New Pallet
        </button>
      </div>

      <div class="relative">
        <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400"
             fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by QR ID…"
          class="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl
                 text-white placeholder-stone-500 focus:outline-none focus:border-amber-400
                 focus:ring-1 focus:ring-amber-400 transition-colors text-sm"
        />
      </div>
    </div>

    <!-- FILTER TABS -->
    <div class="px-5 mt-5 flex gap-2 overflow-x-auto pb-1">
      <button
        v-for="filter in filters"
        :key="filter.value"
        @click="activeFilter = filter.value"
        class="shrink-0 px-4 py-2 rounded-full text-sm font-bold transition-colors"
        :class="activeFilter === filter.value
          ? 'bg-amber-600 text-white shadow-sm'
          : 'bg-white text-stone-600 border border-stone-200 hover:border-amber-300'"
      >
        {{ filter.label }}
      </button>
    </div>

    <!-- PALLET LIST -->
    <div class="px-5 py-5 space-y-3">

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
        ⚠️ {{ error }}
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 5" :key="i"
             class="bg-white rounded-2xl h-24 animate-pulse border border-stone-100"></div>
      </div>

      <div v-else-if="filteredPallets.length === 0"
           class="bg-white rounded-2xl p-12 text-center border border-stone-100 shadow-sm">
        <div class="text-5xl mb-4">📭</div>
        <p class="text-stone-600 font-bold">No pallets found</p>
        <p class="text-stone-400 text-sm mt-1">
          {{ searchQuery ? 'Try a different search term' : 'No pallets match this filter' }}
        </p>
      </div>

      <!-- PalletCard navigates to the detail page on click.
           The footer slot adds the approval dots + optional Transfer button. -->
      <div v-else class="space-y-3">
        <PalletCard
          v-for="pallet in filteredPallets"
          :key="pallet.master_qr_id"
          :pallet="pallet"
          @click="router.push(`/pallets/${pallet.master_qr_id}`)"
        >
          <template #footer>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 pb-4 text-xs text-stone-500">
              <span class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full"
                      :class="pallet.vet_approval ? 'bg-emerald-400' : 'bg-stone-300'"></span>
                Vet {{ pallet.vet_approval ? 'Approved' : 'Pending' }}
              </span>
              <span class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full"
                      :class="pallet.is_quality_maintained ? 'bg-emerald-400' : 'bg-stone-300'"></span>
                Quality {{ pallet.is_quality_maintained ? 'OK' : 'Unknown' }}
              </span>
              <span v-if="pallet.created_at" class="ml-auto text-stone-400">
                {{ formatDate(pallet.created_at) }}
              </span>
            </div>
          </template>
        </PalletCard>
      </div>

      <div class="h-4"></div>
    </div>

    <!-- CreatePalletModal — rendered via <Teleport> so it appears at document.body.
         v-if removes it from the DOM entirely when closed (not just hidden).
         @created and @close are the events the modal emits. -->
    <CreatePalletModal
      v-if="showModal"
      @created="onPalletCreated"
      @close="showModal = false"
    />

  </div>

</template>
