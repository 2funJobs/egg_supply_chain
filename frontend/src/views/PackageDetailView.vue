<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { packages as packagesApi } from '../api'
import StatusBadge from '../components/StatusBadge.vue'
import QrcodeVue from 'qrcode.vue'

const route  = useRoute()
const router = useRouter()

// Automatically updates if the route parameter changes
// Make sure this matches your router config (e.g., /packages/:qrId)
const qrValue = computed(() => {
  // Generates: http://localhost:5173/scan?id=PKG-A6609C
  // window.location.origin dynamically grabs the current domain/port
  return `${window.location.origin}/scan?id=${qrId.value}`
})
const qrId = computed(() => route.params.qrId || route.params.id)

// --- Page state ---
const pkg      = ref(null)
const history  = ref([])
const loading  = ref(true)
const error    = ref(null)

// --- Helpers ---
const feedingLabels = { 
  0: 'Organic 🌿', 
  1: 'Free Range 🐔', 
  2: 'Barn 🏠', 
  3: 'Cage 🔒' 
}

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
  if (!qrId.value) return

  loading.value = true
  error.value   = null
  pkg.value     = null
  history.value = []

  try {
    // Fetch package details + blockchain logs in parallel
    const [pkgRes, histRes] = await Promise.all([
      packagesApi.get(qrId.value),
      // Catch history errors silently so the page still loads even if timeline fails
      packagesApi.history(qrId.value).catch(() => ({ data: { timeline: [] } }))
    ])
    
    pkg.value = pkgRes.data
    
    // Safely extract timeline array based on your Postman data structure
    const rawHistory = histRes.data
    history.value = Array.isArray(rawHistory) 
      ? rawHistory 
      : (rawHistory?.timeline || rawHistory?.results || [])

  } catch (err) {
    error.value = err.response?.status === 404
      ? `Package "${qrId.value}" not found.`
      : 'Failed to load package details. Is the server running?'
  } finally {
    loading.value = false
  }
}

const downloadQR = () => {
  const wrapper = document.getElementById('qr-wrapper')
  
  if (!wrapper) {
    console.error('QR Wrapper div not found.')
    return
  }

  const canvas = wrapper.querySelector('canvas')
  if (!canvas) {
    console.error('Actual canvas element not found inside the wrapper.')
    return
  }
  
  const imageUrl = canvas.toDataURL('image/png')
  const downloadLink = document.createElement('a')
  
  downloadLink.href = imageUrl
  // Uses the reactive route parameter to name the file perfectly
  downloadLink.download = `Pallet-${qrId.value}.png`
  
  document.body.appendChild(downloadLink)
  downloadLink.click()
  document.body.removeChild(downloadLink)
}

// Re-fetch data if the user navigates directly to another package ID
watch(qrId, loadData)

onMounted(loadData)
</script>

<template>
  <div class="w-full max-w-2xl mx-auto">

    <!-- ============================================================
         HEADER
         ============================================================ -->
    <!-- Using a stone gradient to differentiate Packages from Pallets visually -->
    <div class="bg-gradient-to-br from-stone-700 to-stone-900 pt-10 pb-8 px-6 rounded-b-[32px] shadow-lg">

      <!-- Back button + title -->
      <div class="flex items-center gap-3 mb-5">
        <button
          @click="router.push('/packages')"
          class="bg-white/10 hover:bg-white/20 transition-colors p-2 rounded-xl"
        >
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="min-w-0">
          <p class="text-stone-400 text-xs font-semibold uppercase tracking-wider">Package Detail</p>
          <h1 class="text-white font-black font-mono text-lg truncate">{{ qrId }}</h1>
        </div>
      </div>

      <!-- Status row (Pulled from Master Pallet) -->
      <div v-if="pkg?.pallet_detail && !loading" class="flex items-center gap-3 flex-wrap">
        <StatusBadge :status="pkg.pallet_detail.status" variant="pallet" />
        <span
          class="text-xs font-bold px-2.5 py-1 rounded-full"
          :class="pkg.pallet_detail.vet_approval ? 'bg-emerald-400/20 text-emerald-200' : 'bg-white/10 text-white/50'"
        >
          {{ pkg.pallet_detail.vet_approval ? '✓ Vet Approved' : '○ Vet Pending' }}
        </span>
        <span
          class="text-xs font-bold px-2.5 py-1 rounded-full"
          :class="pkg.pallet_detail.is_quality_maintained ? 'bg-emerald-400/20 text-emerald-200' : 'bg-white/10 text-white/50'"
        >
          {{ pkg.pallet_detail.is_quality_maintained ? '✓ Quality OK' : '○ Quality Unknown' }}
        </span>
      </div>

      <!-- Skeleton header state -->
      <div v-else-if="loading" class="flex gap-2">
        <div class="h-7 w-28 bg-white/10 rounded-full animate-pulse"></div>
        <div class="h-7 w-32 bg-white/10 rounded-full animate-pulse"></div>
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
        <button @click="router.push('/packages')" class="mt-3 text-red-600 font-bold underline text-xs">
          ← Back to Packages
        </button>
      </div>

      <!-- Full-page skeleton -->
      <template v-if="loading">
        <div class="bg-white rounded-2xl h-40 animate-pulse border border-stone-100"></div>
        <div class="bg-white rounded-2xl h-48 animate-pulse border border-stone-100"></div>
        <div class="bg-white rounded-2xl h-64 animate-pulse border border-stone-100"></div>
      </template>

      <template v-if="pkg && !loading">
        <!--  -->
        <div v-if="!loading && !error" class="flex flex-col items-center gap-3 bg-gray-50 p-2 rounded-xl border border-gray-100 w-fit m-2">
          
          <div id="qr-wrapper" class="w-29 h-29 shrink-0 bg-white p-2 rounded-xl shadow-sm flex justify-center items-center">
            <div v-if="!loading" class="w-29 h-29 shrink-0 bg-white p-2 rounded-xl shadow-md">
            <qrcode-vue 
              :value="qrValue" 
              :size="100" 
              level="H" 
              class="rounded"
            />
            </div>
          </div>

          <button 
            @click="downloadQR" 
            class="w-full flex justify-center items-center gap-2 bg-amber-600 text-white px-4 py-2 rounded-lg shadow-sm hover:bg-amber-700 transition-colors text-sm font-medium cursor-pointer"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            QR İndir
          </button>
        </div>
        <!--  -->
        <!-- ── PACKAGE SPECS GRID ────────────────────────────────── -->
        <div class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-4 flex items-center gap-2">
            <span>🥚</span> Egg Specifications
          </h3>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Laying Date</p>
              <p class="text-sm font-bold text-stone-800">{{ formatDate(pkg.laying_date).split(',')[0] }}</p>
            </div>
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Expiry Date</p>
              <p class="text-sm font-bold text-stone-800">{{ formatDate(pkg.expiry_date).split(',')[0] }}</p>
            </div>
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Capacity</p>
              <p class="text-sm font-bold text-stone-800">{{ pkg.capacity }} Eggs</p>
            </div>
            <div class="bg-stone-50 rounded-xl p-3">
              <p class="text-xs text-stone-400 mb-1">Feeding Type</p>
              <p class="text-sm font-bold text-stone-800 truncate">
                {{ feedingLabels[pkg.feeding_type] || `Type ${pkg.feeding_type}` }}
              </p>
            </div>
          </div>
        </div>

        <!-- ── MASTER PALLET INFO ────────────────────────────────── -->
        <div v-if="pkg.pallet_detail" class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest flex items-center gap-2">
              <span>📦</span> Master Pallet
            </h3>
            <!-- Link to the Pallet Detail Page -->
            <router-link 
              :to="`/pallets/${pkg.pallet_detail.master_qr_id}`"
              class="text-xs font-bold text-amber-600 hover:text-amber-700 underline"
            >
              View Pallet ➔
            </router-link>
          </div>

          <div class="bg-stone-50 border border-stone-100 rounded-xl p-4">
            <p class="text-xs text-stone-400 mb-1">Pallet QR ID</p>
            <p class="font-mono text-sm font-bold text-stone-800 mb-4">{{ pkg.pallet_detail.master_qr_id }}</p>

            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-stone-200">
              <div>
                <p class="text-[10px] text-stone-400 uppercase tracking-wider font-bold mb-0.5">Producer</p>
                <p class="text-xs font-bold text-stone-700 truncate">
                  {{ pkg.pallet_detail.producer_detail?.name || pkg.pallet_detail.producer || '—' }}
                </p>
              </div>
              <div>
                <p class="text-[10px] text-stone-400 uppercase tracking-wider font-bold mb-0.5">Current Holder</p>
                <p class="text-xs font-bold text-stone-700 truncate">
                  {{ pkg.pallet_detail.current_holder_detail?.name || pkg.pallet_detail.current_holder || '—' }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- ── BLOCKCHAIN LOGS ────────────────────────────────────── -->
        <div class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm">
          <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-4">
            Blockchain History ({{ history.length }})
          </h3>
          
          <div v-if="history.length === 0" class="text-center py-6 bg-stone-50 rounded-xl">
            <span class="text-2xl mb-1 block">⛓️</span>
            <p class="text-xs text-stone-500 font-medium">No blockchain records yet.</p>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="log in history"
              :key="log.tx_hash"
              class="flex items-start gap-3 p-3 bg-stone-50 rounded-xl"
            >
              <span class="text-xl shrink-0 mt-0.5">{{ actionConfig[log.action_type]?.emoji || '🔗' }}</span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <!-- Uses your existing StatusBadge components! -->
                  <StatusBadge :status="log.action_type" variant="action" />
                  <StatusBadge :status="log.status" variant="tx" />
                </div>
                <p class="text-xs text-stone-500">{{ formatDate(log.timestamp) }}</p>
                <p class="font-mono text-[10px] text-stone-400 mt-1 truncate">{{ shortHash(log.tx_hash) }}</p>
              </div>
            </div>
          </div>
        </div>

      </template>

      <div class="h-4"></div>
    </div>
  </div>
</template>