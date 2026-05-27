<!-- CreatePalletModal.vue
     New concepts:
       1. <Teleport to="body"> — renders the modal's DOM as a direct child of <body>
          even though the component is nested deep in the tree. This avoids
          z-index and overflow:hidden clipping problems.
       2. defineEmits() — the modal tells the parent what happened; the parent decides what to do.
       3. Computed form validation — the submit button is gated by real-time computed booleans.

     Props:   none (the modal knows nothing about which pallet list to update)
     Emits:   'created'  → payload: the new pallet object returned by the API
              'close'    → no payload; parent should hide the modal -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { pallets as palletsApi, organizations as orgsApi } from '../api'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['created', 'close'])
const auth = useAuthStore()

const isLoading = ref(false)
const error = ref(null)
// State
const markets        = ref([])
const selectedMarket = ref('')
const marketsLoading = ref(false)

const isValid = computed(() => !!selectedMarket.value)

// Market listesini çek (sadece MARKET tipindekiler)
const fetchMarkets = async () => {
  marketsLoading.value = true
  try {
    const res    = await orgsApi.list({ organization_type: 'MARKET' })
    const data   = res.data
    markets.value = Array.isArray(data) ? data : (data.results ?? [])
  } catch {
    error.value = 'Market listesi yüklenemedi.'
  } finally {
    marketsLoading.value = false
  }
}

// handleCreate'e destination_market ekle
const handleCreate = async () => {
  if (!isValid.value) return
  isLoading.value = true
  error.value = null
  try {
    const pallet = await palletsApi.create({
      destination_market: selectedMarket.value,  // artık tek gönderilen alan
    })
    console.log("hello")
    emit('created', pallet.data)
  } catch (err) {
    error.value = err.response?.data?.detail ?? 'Failed to create pallet.'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchMarkets)
</script>

<template>
  <!-- Teleport renders this entire block at document.body, not at the component's
       location in the DOM tree. The component's reactivity (refs, computed) still
       live in the parent — only the DOM rendering moves. -->
  <Teleport to="body">
    <!-- Full-screen backdrop. @click.self closes the modal only when the user
         clicks the backdrop itself, not the modal panel inside it. -->
    <div
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50
             flex items-end md:items-center justify-center p-4"
      @click.self="$emit('close')"
    >
      <!-- Modal panel — slides up on mobile, centered on desktop -->
      <div class="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden">

        <!-- Header -->
        <div class="flex justify-between items-center p-6 pb-0">
          <div>
            <h2 class="text-xl font-black text-stone-800">New Pallet</h2>
            <p class="text-stone-400 text-sm mt-0.5">Register a batch in the supply chain</p>
          </div>
          <button
            @click="$emit('close')"
            class="p-2 rounded-xl text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div class="p-6 space-y-4">

          <!-- Error banner -->
          <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm">
            ⚠️ {{ error }}
          </div>

          <div>
          <label class="block text-sm font-bold text-stone-700 mb-1.5">
            Destination Market
          </label>

          <!-- Yükleniyor -->
          <div
            v-if="marketsLoading"
            class="h-12 bg-stone-50 border border-stone-200 rounded-xl animate-pulse"
          />

          <!-- Dropdown -->
          <select
            v-else
            v-model="selectedMarket"
            class="w-full px-4 py-3 bg-stone-50 border rounded-xl text-sm
                  focus:outline-none focus:ring-1 focus:ring-amber-400 focus:border-amber-400
                  transition-colors appearance-none"
            :class="selectedMarket ? 'border-stone-200 text-stone-800' : 'border-stone-200 text-stone-400'"
          >
            <option value="" disabled>Select a market…</option>
            <option
              v-for="market in markets"
              :key="market.org_code"
              :value="market.org_code"
            >
              {{ market.name }}  ·  {{ market.org_code }}
            </option>
          </select>

          <!-- Market bulunamadı uyarısı -->
          <p v-if="!marketsLoading && markets.length === 0" class="text-xs text-amber-600 mt-1.5 ml-1">
            ⚠️ No markets registered in the system yet.
          </p>
        </div>

          <!-- Producer auto-set info pill -->
          <div class="bg-amber-50 border border-amber-100 rounded-xl p-3 flex items-center gap-3">
            <span class="text-2xl shrink-0">🏭</span>
            <div>
              <p class="text-xs text-stone-500">Producer (from your account)</p>
              <p class="text-sm font-bold text-stone-800">{{ auth.user?.orgName }}</p>
            </div>
          </div>
        </div>

        <!-- Footer actions -->
        <div class="flex gap-3 px-6 pb-6">
          <button
            @click="$emit('close')"
            class="flex-1 py-3.5 rounded-2xl border border-stone-200 text-stone-600 font-bold
                   hover:bg-stone-50 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="handleCreate"
            :disabled="!isValid || isLoading"
            class="flex-1 py-3.5 rounded-2xl font-bold transition-all
                   flex items-center justify-center gap-2"
            :class="isValid && !isLoading
              ? 'bg-amber-600 text-white hover:bg-amber-700 shadow-lg shadow-amber-600/20'
              : 'bg-stone-200 text-stone-400 cursor-not-allowed'"
          >
            <svg v-if="isLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            {{ isLoading ? 'Creating…' : 'Create Pallet' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
