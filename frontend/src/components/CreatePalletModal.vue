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
import { ref, computed } from 'vue'
import { pallets as palletsApi } from '../api'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['created', 'close'])
const auth = useAuthStore()

const qrId = ref('')
const isLoading = ref(false)
const error = ref(null)

// Validation: QR ID must be at least 3 non-whitespace characters.
// computed() re-evaluates automatically whenever qrId changes.
const isValid = computed(() => qrId.value.trim().length >= 3)

// Generate a timestamp-based ID so the user doesn't have to type one.
const generateId = () => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  qrId.value = `PAL-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`
}

const handleCreate = async () => {
  if (!isValid.value || isLoading.value) return
  error.value = null
  isLoading.value = true

  try {
    const res = await palletsApi.create({ master_qr_id: qrId.value.trim() })
    // Tell the parent a pallet was created. The parent decides what to do next
    // (refresh list, navigate to detail, show a toast, etc.)
    emit('created', res.data)
  } catch (err) {
    // DRF often returns field errors as { field: ["message"] }
    // Flatten them into a single string for display.
    const data = err.response?.data
    if (typeof data === 'object' && data !== null) {
      error.value = Object.values(data).flat().join(' ')
    } else {
      error.value = 'Failed to create pallet. Check the server logs.'
    }
  } finally {
    isLoading.value = false
  }
}
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

          <!-- QR ID field with auto-generate button -->
          <div>
            <label class="block text-sm font-bold text-stone-700 mb-1.5">Pallet QR ID</label>
            <div class="flex gap-2">
              <input
                v-model="qrId"
                type="text"
                placeholder="e.g. PAL-20240501-0830"
                @keyup.enter="handleCreate"
                class="flex-1 px-4 py-3 bg-stone-50 border rounded-xl font-mono text-sm
                       transition-colors focus:outline-none
                       focus:ring-1 focus:ring-amber-400 focus:border-amber-400"
                :class="qrId && !isValid ? 'border-red-300 bg-red-50' : 'border-stone-200'"
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
            <!-- Inline validation message — shows only when there's input but it's invalid -->
            <p
              v-if="qrId && !isValid"
              class="text-xs text-red-500 mt-1.5 ml-1"
            >
              At least 3 characters required.
            </p>
            <p v-else class="text-xs text-stone-400 mt-1.5 ml-1">
              Must be unique across the network.
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
