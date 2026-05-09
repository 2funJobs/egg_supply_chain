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
import { packages as packagesApi, pallets as palletsApi } from '../api'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['created', 'close'])
const auth = useAuthStore()

// 1. The Form State
const form = ref({
  qrId: '',
  pallet: '',
  layingDate: '',
  expiryDate: ''
})

// 2. The Loading & Error States
const isLoading = ref(false)
const error = ref(null)

// THESE ARE THE TWO MISSING VARIABLES THAT CAUSED THE CRASH:
const availablePallets = ref([])
const isLoadingPallets = ref(true)

// 3. Bulletproof Validation
const isValid = computed(() => {
  return (
    (form.value.qrId?.trim()?.length || 0) >= 3 &&
    (form.value.pallet?.trim()?.length || 0) >= 3 &&
    !!form.value.layingDate && 
    !!form.value.expiryDate
  )
})

// 4. Generate ID
const generateId = () => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  form.value.qrId = `PCKG-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`
}

// 5. Submit the Form
const handleCreate = async () => {
  if (!isValid.value || isLoading.value) return
  error.value = null
  isLoading.value = true

  try {
    const payload = {
      package_qr_id: form.value.qrId.trim(),
      pallet: form.value.pallet.trim(),
      laying_date: form.value.layingDate,
      expiry_date: form.value.expiryDate
    }

    const res = await packagesApi.create(payload)
    emit('created', res.data)
  } catch (err) {
    const data = err.response?.data
    if (typeof data === 'object' && data !== null) {
      error.value = Object.values(data).flat().join(' ')
    } else {
      error.value = 'Failed to create package. Check the server logs.'
    }
  } finally {
    isLoading.value = false
  }
}

// 6. Fetch Open Pallets on Load
onMounted(async () => {
  try {
    const res = await palletsApi.list({ status: 'IN_PRODUCTION' })
    const rawData = res.data || {}
    availablePallets.value = Array.isArray(rawData) ? rawData : (rawData.results || [])
  } catch (err) {
    console.error("Failed to fetch available pallets", err)
    availablePallets.value = [] 
  } finally {
    isLoadingPallets.value = false 
  }
})
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50
             flex items-end md:items-center justify-center p-4"
      @click.self="$emit('close')"
    >
      <div class="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden">

        <!-- Header -->
        <div class="flex justify-between items-center p-6 pb-0">
          <div>
            <h2 class="text-xl font-black text-stone-800">New Package</h2>
            <p class="text-stone-400 text-sm mt-0.5">Assign eggs to a master pallet</p>
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

          <!-- Package QR ID -->
          <div>
            <label class="block text-sm font-bold text-stone-700 mb-1.5">Package QR ID</label>
            <div class="flex gap-2">
              <input
                v-model="form.qrId"
                type="text"
                placeholder="e.g. PCKG-2024..."
                class="flex-1 px-4 py-3 bg-stone-50 border rounded-xl font-mono text-sm
                       transition-colors focus:outline-none
                       focus:ring-1 focus:ring-amber-400 focus:border-amber-400"
                :class="form.qrId && form.qrId.trim().length < 3 ? 'border-red-300 bg-red-50' : 'border-stone-200'"
              />
              <button
                type="button"
                @click="generateId"
                class="px-4 py-3 bg-stone-100 text-stone-600 rounded-xl font-bold text-xs
                       hover:bg-stone-200 transition-colors shrink-0"
              >
                Auto
              </button>
            </div>
          </div>

          <!-- Master Pallet Assignment -->
          <div>
            <label class="block text-sm font-bold text-stone-700 mb-1.5">Master Pallet</label>
            
            <select
              v-model="form.pallet"
              :disabled="isLoadingPallets || availablePallets?.length === 0"
              class="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl font-mono text-sm
                    transition-colors focus:outline-none text-stone-700
                    focus:ring-1 focus:ring-amber-400 focus:border-amber-400 disabled:opacity-50"
            >
              <option value="" disabled>
                {{ isLoadingPallets ? 'Loading pallets...' : (availablePallets?.length === 0 ? 'No open pallets available' : 'Select an active pallet...') }}
              </option>
              
              <!-- Loop through the fetched IN_PRODUCTION pallets -->
              <option 
                v-for="pallet in availablePallets" 
                :key="pallet.master_qr_id" 
                :value="pallet.master_qr_id"
              >
                {{ pallet.master_qr_id }} (Created: {{ new Date(pallet.created_at).toLocaleDateString() }})
              </option>
            </select>

            <!-- Helpful warning if they have no open pallets -->
            <p v-if="!isLoadingPallets && availablePallets?.length === 0" class="text-xs text-red-500 mt-1.5 ml-1">
              You must create a new Pallet before you can add packages.
            </p>
          </div>

          <!-- Dates Grid -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-bold text-stone-700 mb-1.5">Laying Date</label>
              <input
                v-model="form.layingDate"
                type="date"
                class="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-sm
                       transition-colors focus:outline-none text-stone-600
                       focus:ring-1 focus:ring-amber-400 focus:border-amber-400"
              />
            </div>
            <div>
              <label class="block text-sm font-bold text-stone-700 mb-1.5">Expiry Date</label>
              <input
                v-model="form.expiryDate"
                type="date"
                class="w-full px-4 py-3 bg-stone-50 border border-stone-200 rounded-xl text-sm
                       transition-colors focus:outline-none text-stone-600
                       focus:ring-1 focus:ring-amber-400 focus:border-amber-400"
              />
            </div>
          </div>

          <!-- Producer auto-set info pill -->
          <div class="bg-amber-50 border border-amber-100 rounded-xl p-3 flex items-center gap-3 mt-2">
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
            {{ isLoading ? 'Creating…' : 'Create Package' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
