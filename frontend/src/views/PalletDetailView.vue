<!-- PalletDetailView.vue
     New concepts:
       1. Route params — useRoute().params.qrId extracts the :qrId segment from the URL
       2. watch() — re-runs a function whenever a reactive value changes.
          Here we watch the qrId param so navigating from /pallets/A to /pallets/B
          re-fetches data without a full page reload.
       3. Real-time form validation with computed() — derives validity from input values
       4. Sections: info grid, IoT form, transfer form, packages, blockchain logs -->
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePermissions } from '../composables/usePermissions'
import { pallets as palletsApi, packages as packagesApi, blockchain as blockchainApi } from '../api'
import StatusBadge from '../components/StatusBadge.vue'

const route  = useRoute()
const router = useRouter()
const { canTransferPallet } = usePermissions()

// computed() on a route param makes it reactive — if the URL changes,
// qrId.value updates automatically.
const qrId = computed(() => route.params.qrId)

// --- Page state ---
const pallet   = ref(null)
const pkgs     = ref([])
const logs     = ref([])
const loading  = ref(true)
const error    = ref(null)

// --- Transfer form state ---
const newHolder       = ref('')
const newStatus = ref('')
const xferLoading     = ref(false)
const xferError       = ref(null)
const xferSuccess     = ref(false)

// --- Helpers ---
const feedingLabels = { 0: 'Organic 🌿', 1: 'Free Range 🐔', 2: 'Barn 🏠', 3: 'Cage 🔒' }

const formatDate = (str) => {
  if (!str) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(str))
}

const shortHash = (h) => {
  if (!h || h.length < 16) return h || '—'
  return `${h.slice(0, 10)}…${h.slice(-8)}`
}

const actionConfig = {
  PROD: { label: 'Production',  emoji: '🏭' },
  TRAN: { label: 'Transfer',    emoji: '🚛' },
  QUAL: { label: 'Quality',     emoji: '✅' },
  RECV: { label: 'Received',    emoji: '📥' },
  CERT: { label: 'Certificate', emoji: '📜' },
}

// --- Data fetching ---
const loadData = async () => {
  loading.value = true
  error.value   = null
  pallet.value  = null
  pkgs.value    = []
  logs.value    = []

  try {
    // Fetch pallet + blockchain logs in parallel
    const [palletRes, logsRes] = await Promise.all([
      palletsApi.get(qrId.value),
      blockchainApi.list({ pallet__master_qr_id: qrId.value }),
    ])
    pallet.value = palletRes.data
    logs.value   = Array.isArray(logsRes.data) ? logsRes.data : (logsRes.data.results ?? [])

    // Packages: fetch all and filter client-side.
    // (A dedicated filter endpoint would be better for large datasets, but
    // this works without knowing the exact backend filter field names.)
    try {
      const pkgRes = await packagesApi.list()
      const all = Array.isArray(pkgRes.data) ? pkgRes.data : (pkgRes.data.results ?? [])
      pkgs.value = all.filter((p) =>
        p.pallet === qrId.value ||
        p.pallet?.master_qr_id === qrId.value
      )
    } catch { /* packages stay empty — non-critical */ }

  } catch (err) {
    error.value = err.response?.status === 404
      ? `Pallet "${qrId.value}" not found.`
      : 'Failed to load pallet. Is the server running?'
  } finally {
    loading.value = false
  }
}

// --- Transfer submit ---
const submitTransfer = async () => {
  // 1. Ensure both the org code and status are filled out before proceeding
  if (!newHolder.value.trim() || !newStatus.value || xferLoading.value) return
  
  xferLoading.value = true
  xferError.value   = null
  xferSuccess.value = false

  try {
    // 2. Add the status to the API payload
    const payload = {
      new_holder_code: newHolder.value.trim(),
      status: newStatus.value
    }

    await palletsApi.transfer(qrId.value, payload)
    
    xferSuccess.value = true
    
    // 3. Clear both form fields on success
    newHolder.value = ''
    newStatus.value = ''
    
    // Refresh the pallet data to show the new state on the UI
    const res = await palletsApi.get(qrId.value)
    pallet.value = res.data

  } catch (err) {
    const data = err.response?.data
    xferError.value = typeof data === 'string'
      ? data
      : Object.values(data ?? {}).flat().join(' ') || 'Transfer failed.'
  } finally {
    xferLoading.value = false
  }
}

// watch() — runs the callback whenever qrId changes.
// This handles the case where the user navigates from one pallet detail to another
// (e.g., going back to the list and clicking a different pallet).
// Without watch(), the component would show stale data from the previous pallet.
watch(qrId, loadData)

onMounted(loadData)
</script>

<template>
  <div class="w-full max-w-2xl mx-auto">

    <!-- ============================================================
         HEADER
         ============================================================ -->
    <div class="bg-gradient-to-br from-amber-600 to-orange-800 pt-10 pb-8 px-6 rounded-b-[32px] shadow-lg">

      <!-- Back button + title -->
      <div class="flex items-center gap-3 mb-5">
        <button
          @click="router.push('/pallets')"
          class="bg-white/20 hover:bg-white/30 transition-colors p-2 rounded-xl"
        >
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="min-w-0">
          <p class="text-amber-200 text-xs font-semibold">Pallet Detail</p>
          <h1 class="text-white font-black font-mono text-lg truncate">{{ qrId }}</h1>
        </div>
      </div>

      <!-- Status row -->
      <div v-if="pallet && !loading" class="flex items-center gap-3 flex-wrap">
        <StatusBadge :status="pallet.status" variant="pallet" />
        <span
          class="text-xs font-bold px-2.5 py-1 rounded-full"
          :class="pallet.vet_approval ? 'bg-emerald-400/20 text-emerald-200' : 'bg-white/10 text-white/50'"
        >
          {{ pallet.vet_approval ? '✓ Vet Approved' : '○ Vet Pending' }}
        </span>
        <span
          class="text-xs font-bold px-2.5 py-1 rounded-full"
          :class="pallet.is_quality_maintained ? 'bg-emerald-400/20 text-emerald-200' : 'bg-white/10 text-white/50'"
        >
          {{ pallet.is_quality_maintained ? '✓ Quality OK' : '○ Quality Unknown' }}
        </span>
      </div>

      <!-- Skeleton header state -->
      <div v-else-if="loading" class="flex gap-2">
        <div class="h-7 w-28 bg-white/20 rounded-full animate-pulse"></div>
        <div class="h-7 w-24 bg-white/20 rounded-full animate-pulse"></div>
      </div>
    </div>

    <!-- ============================================================
         CONTENT
         ============================================================ -->
    <div class="px-5 py-6 space-y-5">

      <!-- Error state -->
      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-5 rounded-2xl text-sm">
        <p class="font-bold mb-1">⚠️ Error</p>
        <p>{{ error }}</p>
        <button @click="router.push('/pallets')" class="mt-3 text-red-600 font-bold underline text-xs">
          ← Back to Pallets
        </button>
      </div>

      <!-- Full-page skeleton -->
      <template v-if="loading">
        <div class="bg-white rounded-2xl h-40 animate-pulse border border-stone-100"></div>
        <div class="bg-white rounded-2xl h-32 animate-pulse border border-stone-100"></div>
        <div class="bg-white rounded-2xl h-48 animate-pulse border border-stone-100"></div>
      </template>

      <template v-if="pallet && !loading">

        <!-- ── INFO GRID ─────────────────────────────────────────── -->
        <div class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-4">Details</h3>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Producer</p>
              <p class="text-sm font-bold text-stone-800 truncate">
                {{ pallet.producer?.name || pallet.producer || '—' }}
              </p>
            </div>
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Current Holder</p>
              <p class="text-sm font-bold text-stone-800 truncate">
                {{ pallet.current_holder?.name || pallet.current_holder || 'Producer' }}
              </p>
            </div>
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Created</p>
              <p class="text-sm font-bold text-stone-800">{{ formatDate(pallet.created_at) }}</p>
            </div>
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Departure</p>
              <p class="text-sm font-bold text-stone-800">{{ formatDate(pallet.departure_date) }}</p>
            </div>
          </div>
        </div>

        <!-- ── PACKAGES ──────────────────────────────────────────── -->
        <div v-if="pkgs.length > 0" class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-4">
            Packages ({{ pkgs.length }})
          </h3>
          <div class="space-y-2">
            <div
              v-for="pkg in pkgs"
              :key="pkg.package_qr_id"
              class="flex items-center gap-3 bg-stone-50 rounded-xl p-3"
            >
              <span class="text-xl shrink-0">🥚</span>
              <div class="min-w-0 flex-1">
                <p class="font-bold text-stone-800 font-mono text-xs">{{ pkg.package_qr_id }}</p>
                <p class="text-xs text-stone-500 mt-0.5">
                  {{ pkg.capacity }} eggs · {{ feedingLabels[pkg.feeding_type] ?? pkg.feeding_type }}
                </p>
              </div>
              <div class="text-right shrink-0">
                <p class="text-xs text-stone-400">Best before</p>
                <p class="text-xs font-bold text-amber-700">{{ pkg.expiry_date || '—' }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- ── TRANSFER FORM (DISTRIBUTOR / MARKET only) ─────────── -->
        <div
          v-if="canTransferPallet"
          class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm"
        >
          <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-1">
            Transfer Pallet
          </h3>
          <p class="text-xs text-stone-400 mb-4">Assign to a new organization and update its status.</p>

          <!-- Success / Error Messages -->
          <div v-if="xferSuccess" class="bg-emerald-50 border border-emerald-200 text-emerald-700 p-3 rounded-xl text-sm mb-4 flex items-center gap-2">
            <span>✅</span> Pallet transferred successfully.
          </div>
          <div v-if="xferError" class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm mb-4">
            ⚠️ {{ xferError }}
          </div>

          <!-- Form Inputs -->
          <div class="flex flex-col gap-3">
            
            <!-- Organization Code Input -->
            <div>
              <label class="block text-xs font-semibold text-stone-500 uppercase tracking-wider mb-1">
                New Holder (Org Code)
              </label>
              <input
                v-model="newHolder"
                type="text"
                placeholder="e.g. DIST-001"
                @keyup.enter="submitTransfer"
                class="w-full px-3 py-2.5 border border-stone-200 bg-stone-50 rounded-xl text-sm font-mono focus:outline-none focus:border-stone-500 focus:ring-1 focus:ring-stone-400 transition-colors"
              />
            </div>

            <!-- Status Dropdown -->
            <div>
              <label class="block text-xs font-semibold text-stone-500 uppercase tracking-wider mb-1">
                Pallet Status
              </label>
              <select
                v-model="newStatus"
                @keyup.enter="submitTransfer"
                class="w-full px-3 py-2.5 border border-stone-200 bg-stone-50 rounded-xl text-sm focus:outline-none focus:border-stone-500 focus:ring-1 focus:ring-stone-400 transition-colors"
              >
                <option value="" disabled>Select a status...</option>
                <option value="IN_TRANSIT">In Transit</option>
                <option value="AT_MARKET">At Market</option>
              </select>
            </div>

            <!-- Submit Button -->
            <button
              @click="submitTransfer"
              :disabled="!newHolder.trim() || !newStatus || xferLoading"
              class="mt-2 w-full px-4 py-3 rounded-xl font-bold text-sm transition-colors flex items-center justify-center gap-2"
              :class="(newHolder.trim() && newStatus && !xferLoading)
                ? 'bg-stone-700 text-white hover:bg-stone-800'
                : 'bg-stone-100 text-stone-400 cursor-not-allowed'"
            >
              <svg v-if="xferLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {{ xferLoading ? 'Transferring...' : 'Transfer Pallet' }}
            </button>
          </div>
        </div>

        <!-- ── BLOCKCHAIN LOGS ────────────────────────────────────── -->
        <div v-if="logs.length > 0" class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-4">
            Blockchain History ({{ logs.length }})
          </h3>
          <div class="space-y-3">
            <div
              v-for="log in logs"
              :key="log.tx_hash"
              class="flex items-start gap-3 p-3 bg-stone-50 rounded-xl"
            >
              <span class="text-xl shrink-0 mt-0.5">{{ actionConfig[log.action_type]?.emoji || '🔗' }}</span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <StatusBadge :status="log.action_type" variant="action" />
                  <StatusBadge :status="log.status" variant="tx" />
                </div>
                <p class="text-xs text-stone-500">{{ formatDate(log.timestamp) }}</p>
                <p class="font-mono text-xs text-stone-400 mt-1 truncate">{{ shortHash(log.tx_hash) }}</p>
              </div>
            </div>
          </div>
        </div>

      </template>

      <div class="h-4"></div>
    </div>
  </div>
</template>
