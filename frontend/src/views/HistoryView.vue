<!-- src/views/HistoryView.vue — QR Traceability Scanner
     This page is PUBLIC — no login required.
     Consumers scan their egg package QR code and see the full supply chain journey.

     New concepts:
       - @keyup.enter: run a method when Enter is pressed
       - Template refs (not used here, but note that v-model replaces them for inputs)
       - Conditional blocks with v-if / v-else-if / v-else
       - CSS-only vertical timeline using relative/absolute positioning -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { packages as packagesApi } from '../api'
import { QrcodeStream } from 'vue-qrcode-reader'

// ── Sabitler ──────────────────────────────────────────────────────────────────

const FEEDING_TYPES = {
  0: { label: 'Organik',    emoji: '🌿', bg: 'bg-emerald-50', color: 'text-emerald-700' },
  1: { label: 'Free-Range', emoji: '🌾', bg: 'bg-amber-50',   color: 'text-amber-700'   },
  2: { label: 'Kümes',       emoji: '🏠', bg: 'bg-orange-50',  color: 'text-orange-700'  },
  3: { label: 'Cage',       emoji: '🔒', bg: 'bg-stone-50',   color: 'text-stone-700'   },
}

const CAPACITY_LABELS = { 6: '6 Eggs', 15: '15 Eggs', 30: '30 Eggs' }

const ACTION_CONFIG = {
  PROD: { color: 'bg-blue-100 text-blue-700',     emoji: '🏭' },
  TRAN: { color: 'bg-amber-100 text-amber-700',   emoji: '🚛' },
  QUAL: { color: 'bg-emerald-100 text-emerald-700', emoji: '✅' },
  RECV: { color: 'bg-purple-100 text-purple-700', emoji: '📥' },
  CERT: { color: 'bg-pink-100 text-pink-700',     emoji: '📜' },
}

// ── State ─────────────────────────────────────────────────────────────────────

const qrInput        = ref('')
const packageDetails = ref(null)
const history        = ref(null)
const loading        = ref(false)
const error          = ref(null)
const copiedHash     = ref(null)
const route  = useRoute()

// --- Scanner State ---
const showScanner = ref(false)
const cameraError = ref(null)

// ── Yardımcılar ───────────────────────────────────────────────────────────────

const formatDate = (str, short = false) => {
  if (!str) return '—'
  const opts = short
    ? { day: '2-digit', month: 'short', year: 'numeric' }
    : { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }
  return new Intl.DateTimeFormat('en-GB', opts).format(new Date(str))
}

const daysUntilExpiry = (expiryStr) => {
  if (!expiryStr) return null
  return Math.ceil((new Date(expiryStr) - new Date()) / 86_400_000)
}

const expiryMeta = (days) => {
  if (days === null) return { text: '—',            cls: 'text-stone-400'   }
  if (days < 0)     return { text: 'Expired',       cls: 'text-red-600'     }
  if (days < 7)     return { text: `${days}d left`, cls: 'text-red-500'     }
  if (days < 14)    return { text: `${days}d left`, cls: 'text-amber-600'   }
  return                   { text: `${days}d left`, cls: 'text-emerald-600' }
}

const copyHash = async (hash) => {
  try {
    await navigator.clipboard.writeText(hash)
    copiedHash.value = hash
    setTimeout(() => { copiedHash.value = null }, 1500)
  } catch { /* ignore */ }
}

// ── API ───────────────────────────────────────────────────────────────────────

onMounted(() => {
  // 1. Check if the URL has an ?id= parameter
  if (route.query.id) {
    // 2. Set the input value to the ID from the URL
    qrInput.value = route.query.id
    
    // 3. Automatically trigger your existing search function
    handleSearch()
  }
})

// --- Handle Camera Scan ---
const onDetect = (detectedCodes) => {
  const result = detectedCodes[0]
  if (!result || !result.rawValue) return

  const scannedText = result.rawValue
  let finalId = scannedText

  // Check if the scanned text is a full URL. If so, extract the 'id' parameter.
  try {
    const url = new URL(scannedText)
    if (url.searchParams.has('id')) {
      finalId = url.searchParams.get('id')
    }
  } catch (e) {
    // If it's not a URL, it will fail silently and just use the raw text (fallback)
  }

  // Update input, hide scanner, and trigger search
  qrInput.value = finalId
  showScanner.value = false
  handleSearch()
}

// --- Camera Error Handling ---
const onCameraError = (err) => {
  if (err.name === 'NotAllowedError') {
    cameraError.value = 'Camera access was denied.'
  } else if (err.name === 'NotFoundError') {
    cameraError.value = 'No camera found on this device.'
  } else {
    cameraError.value = `Camera error: ${err.message}`
  }
}

// --- Drawing Box on Scanner ---
const paintBoundingBox = (detectedCodes, ctx) => {
  for (const detectedCode of detectedCodes) {
    const { boundingBox: { x, y, width, height } } = detectedCode
    ctx.lineWidth = 3
    ctx.strokeStyle = '#10b981' // emerald-500
    ctx.strokeRect(x, y, width, height)
  }
}

const handleSearch = async () => {
  const id = qrInput.value.trim().toUpperCase()
  if (!id) return

  error.value          = null
  history.value        = null
  packageDetails.value = null
  loading.value        = true
  cameraError.value    = null

  try {
    const { data }       = await packagesApi.history(id)
    packageDetails.value = data.package_details ?? null
    history.value        = data.timeline ?? []
    if (history.value.length === 0) throw { response: { status: 404 } }
  } catch (err) {
    error.value = err.response?.status === 404
      ? `Package "${id}" not found. Please check the QR code.`
      : 'Could not fetch traceability data. Make sure the server is running.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-2xl mx-auto">

    <!-- ── HEADER ─────────────────────────────────────────────────────────── -->
    <div class="bg-gradient-to-br from-emerald-600 to-teal-800 pt-10 pb-10 px-6 rounded-b-[40px] shadow-lg">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-3xl">🔍</span>
        <h1 class="text-2xl font-black text-white">Trace Your Eggs</h1>
      </div>
      <p class="text-emerald-200 text-sm mb-6">
        Enter a package QR ID to see its complete journey from farm to table.
      </p>
      <!-- INPUT -->
      <div class="flex gap-2">
        <button 
          @click="showScanner = !showScanner"
          class="bg-white/20 hover:bg-white/30 text-white p-3.5 rounded-xl transition-colors shrink-0 flex items-center justify-center border border-white/30 backdrop-blur-sm"
          title="Scan QR Code"
        >
          <!-- Camera SVG Icon -->
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
        <input
          v-model="qrInput"
          @keyup.enter="handleSearch"
          type="text"
          placeholder="e.g. PKG-A6609C"
          class="flex-1 px-4 py-3.5 bg-white/15 backdrop-blur-sm border border-white/30 rounded-xl
                 text-white placeholder-emerald-300 focus:outline-none focus:border-white
                 focus:ring-1 focus:ring-white transition-colors text-sm uppercase tracking-wider"
        />
        <button
          @click="handleSearch"
          :disabled="loading || !qrInput.trim()"
          class="bg-white text-emerald-700 font-black px-5 py-3.5 rounded-xl
                 hover:bg-emerald-50 transition-colors shrink-0
                 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ loading ? '…' : 'Trace' }}
        </button>
      </div>
      <!--  -->
      <!-- Scanner Dropdown Area -->
      <div 
        v-if="showScanner" 
        class="mt-4 bg-black/40 backdrop-blur-md rounded-xl p-3 border border-white/20 overflow-hidden shadow-inner"
      >
        <div class="flex justify-between items-center mb-2 px-1">
          <span class="text-xs font-semibold text-emerald-100 uppercase tracking-widest">Point camera at package</span>
          <button @click="showScanner = false" class="text-white hover:text-emerald-300 text-sm font-bold">✕ Close</button>
        </div>
        
        <div class="flex justify-center w-full pb-2">
          <div class="w-100 max-w-full rounded-2xl overflow-hidden relative aspect-square bg-black border-2 border-white/10 shadow-xl">
            <qrcode-stream 
              @detect="onDetect" 
              @error="onCameraError"
              :track="paintBoundingBox"
            />
        </div>
        </div>
        
        <div v-if="cameraError" class="mt-3 p-2 bg-red-500/80 text-white text-xs rounded text-center">
          {{ cameraError }}
        </div>
      </div>
      <!--  -->
    </div>

    <div class="px-5 py-6 space-y-5">

      <!-- Hata -->
      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex gap-3">
        <span class="shrink-0 text-lg">⚠️</span>
        <p>{{ error }}</p>
      </div>

      <!-- Skeleton -->
      <div v-if="loading" class="space-y-4">
        <div class="bg-white rounded-2xl h-40 animate-pulse border border-stone-100" />
        <div class="bg-white rounded-2xl h-80 animate-pulse border border-stone-100" />
      </div>

      <!-- ── PAKET BİLGİ KARTI ─────────────────────────────────────────────── -->
      <div
        v-if="packageDetails && !loading"
        class="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden"
      >
        <!-- Üst alan: besleme tipi + QR -->
        <div
          class="px-5 pt-5 pb-4 border-b border-black/5"
          :class="FEEDING_TYPES[packageDetails.feeding_type]?.bg ?? 'bg-stone-50'"
        >
          <div class="flex items-start justify-between">
            <div>
              <span class="text-3xl">{{ FEEDING_TYPES[packageDetails.feeding_type]?.emoji ?? '🥚' }}</span>
              <h2 class="font-black text-stone-800 text-xl mt-1">
                {{ FEEDING_TYPES[packageDetails.feeding_type]?.label ?? 'Unknown' }} Eggs
              </h2>
              <span class="font-mono text-xs text-stone-400 mt-0.5 block">
                {{ packageDetails.package_qr_id }}
              </span>
            </div>
            <div class="text-right">
              <div class="text-sm font-bold text-stone-600">
                {{ CAPACITY_LABELS[packageDetails.capacity] ?? `${packageDetails.capacity} eggs` }}
              </div>
              <div
                class="text-sm font-black mt-1"
                :class="expiryMeta(daysUntilExpiry(packageDetails.expiry_date)).cls"
              >
                {{ expiryMeta(daysUntilExpiry(packageDetails.expiry_date)).text }}
              </div>
            </div>
          </div>
        </div>

        <!-- Palet -->
        <div class="px-5 py-3 flex items-center gap-2 border-b border-stone-50">
          <svg class="w-4 h-4 text-stone-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
          </svg>
          <span class="text-xs text-stone-400 font-bold uppercase tracking-wider">Pallet</span>
          <span class="font-mono text-sm font-bold text-stone-700 ml-auto">{{ packageDetails.pallet }}</span>
        </div>

        <!-- Tarihler -->
        <div class="px-5 py-4 grid grid-cols-2 divide-x divide-stone-100">
          <div class="pr-4">
            <span class="text-[10px] font-bold text-stone-400 uppercase tracking-wider block mb-1">Laying Date</span>
            <span class="text-sm font-bold text-stone-700">{{ formatDate(packageDetails.laying_date, true) }}</span>
          </div>
          <div class="pl-4">
            <span class="text-[10px] font-bold text-stone-400 uppercase tracking-wider block mb-1">Best Before</span>
            <span class="text-sm font-bold text-stone-700">{{ formatDate(packageDetails.expiry_date, true) }}</span>
          </div>
        </div>
      </div>

      <!-- ── TİMLİNE ─────────────────────────────────────────────────────────── -->
      <div v-if="history && history.length > 0 && !loading">
        <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-5">
          Supply Chain Journey · {{ history.length }} records
        </h3>

        <div class="relative">
          <!-- Dikey çizgi -->
          <div class="absolute left-5 top-5 bottom-5 w-0.5 bg-stone-200 rounded-full" />

          <div class="space-y-4">
            <div
              v-for="(event, index) in history"
              :key="index"
              class="relative flex items-start gap-4"
            >
              <!-- Nokta -->
              <div
                class="relative z-10 w-10 h-10 rounded-full flex items-center justify-center
                       text-lg shadow-md border-2 border-white shrink-0"
                :class="ACTION_CONFIG[event.action_type]?.color.split(' ')[0] ?? 'bg-stone-100'"
              >
                {{ ACTION_CONFIG[event.action_type]?.emoji ?? '🔗' }}
              </div>

              <!-- Kart -->
              <div class="flex-1 bg-white rounded-2xl p-4 border border-stone-100 shadow-sm mb-2">

                <!-- Badge'ler -->
                <div class="flex items-start justify-between gap-2 mb-3">
                  <span
                    class="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider"
                    :class="ACTION_CONFIG[event.action_type]?.color ?? 'bg-stone-100 text-stone-600'"
                  >
                    {{ event.action_type_display }}
                  </span>
                  <span
                    class="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider shrink-0"
                    :class="event.status === 'SUCCESS'
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-red-100 text-red-700'"
                  >
                    {{ event.status_display }}
                  </span>
                </div>

                <!-- Organizasyon + zaman -->
                <p class="text-sm font-bold text-stone-800">{{ event.organization_name }}</p>
                <p class="text-xs text-stone-400 mt-0.5">{{ formatDate(event.timestamp) }}</p>

                <!-- ── Payload alanı ── -->
                <div class="mt-3 bg-stone-50 border border-stone-100 rounded-xl p-3 text-xs space-y-2">

                  <!-- PALLET_CREATED -->
                  <template v-if="event.payload?.action === 'PALLET_CREATED'">
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 uppercase tracking-wider text-[10px]">Certificate</span>
                      <span class="font-mono font-bold text-stone-700">{{ event.payload.certificate_no }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 uppercase tracking-wider text-[10px]">Inspector</span>
                      <span class="font-bold text-stone-700">{{ event.payload.inspector_org }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 uppercase tracking-wider text-[10px]">Departure</span>
                      <span class="font-bold text-stone-700">{{ formatDate(event.payload.departure_date, true) }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 uppercase tracking-wider text-[10px]">Order</span>
                      <span class="font-mono font-bold text-stone-700">{{ event.payload.fulfillment_for_order }}</span>
                    </div>
                    <div
                      v-if="event.payload.auto_vet_approval"
                      class="flex items-center gap-1.5 text-emerald-600 font-bold pt-1.5 border-t border-stone-200"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                      </svg>
                      Veterinary Approved
                    </div>
                  </template>

                  <!-- BULK_PACKAGES_CREATED -->
                  <template v-else-if="event.payload?.action === 'BULK_PACKAGES_CREATED'">
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 uppercase tracking-wider text-[10px]">Pallet</span>
                      <span class="font-mono font-bold text-stone-700">{{ event.payload.pallet_qr }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 uppercase tracking-wider text-[10px]">Packages Minted</span>
                      <span class="font-black text-blue-600 text-sm">{{ event.payload.total_packages_minted }}</span>
                    </div>
                  </template>

                  <!-- TRANSFER / RECEIVED -->
                  <template v-else-if="event.action_type === 'TRAN' || event.action_type === 'RECV'">
                    <!-- From → To -->
                    <div class="flex items-center gap-2 bg-white rounded-lg p-2 border border-stone-100">
                      <div class="flex-1 text-center">
                        <span class="text-[10px] text-stone-400 uppercase tracking-wider block mb-0.5">From</span>
                        <span class="font-bold text-stone-700 text-xs leading-tight">{{ event.payload.transfer_from_org }}</span>
                      </div>
                      <svg class="w-4 h-4 text-stone-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
                      </svg>
                      <div class="flex-1 text-center">
                        <span class="text-[10px] text-stone-400 uppercase tracking-wider block mb-0.5">To</span>
                        <span class="font-bold text-stone-700 text-xs leading-tight">{{ event.payload.transfer_to_org_name }}</span>
                      </div>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 uppercase tracking-wider text-[10px]">Status Update</span>
                      <span class="font-mono font-bold text-blue-600">{{ event.payload.new_status }}</span>
                    </div>
                    <div
                      v-if="event.payload.notes"
                      class="text-stone-400 italic pt-1.5 border-t border-stone-200"
                    >
                      "{{ event.payload.notes }}"
                    </div>
                  </template>

                  <!-- Fallback: bilinmeyen payload -->
                  <template v-else>
                    <div
                      v-for="(val, key) in event.payload"
                      :key="key"
                      class="flex justify-between items-start gap-2"
                    >
                      <span class="text-stone-400 uppercase tracking-wider text-[10px] shrink-0">{{ key }}</span>
                      <span class="font-medium text-stone-600 text-right break-all">{{ val }}</span>
                    </div>
                  </template>

                </div>

                <!-- TX Hash + kopyala -->
                <button
                  @click="copyHash(event.tx_hash)"
                  class="w-full mt-3 bg-stone-50 border border-stone-100 rounded-lg px-3 py-2
                         flex items-center gap-2 hover:bg-stone-100 transition-colors"
                  title="Copy transaction hash"
                >
                  <span class="font-mono text-[10px] text-stone-400 truncate flex-1 text-left">
                    {{ event.tx_hash }}
                  </span>
                  <div class="flex items-center gap-1.5 shrink-0 text-[10px] text-stone-400">
                    <span>Block #{{ event.block_number }}</span>
                    <span>{{ copiedHash === event.tx_hash ? '✅' : '📋' }}</span>
                  </div>
                </button>

              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Boş timeline -->
      <div
        v-else-if="history && history.length === 0 && !loading"
        class="bg-white rounded-2xl p-10 text-center border border-stone-100 shadow-sm"
      >
        <div class="text-4xl mb-3">📭</div>
        <p class="text-stone-600 font-bold">No history recorded</p>
        <p class="text-stone-400 text-sm mt-1">This package has no blockchain transactions yet.</p>
      </div>

      <!-- Varsayılan (arama öncesi) -->
      <div v-else-if="!loading && !error && !history" class="text-center py-14">
        <div class="text-7xl mb-5">🥚</div>
        <p class="text-stone-700 font-black text-xl">Know Your Eggs</p>
        <p class="text-stone-400 text-sm mt-2 leading-relaxed">
          Scan the QR code on your egg package<br>or enter the ID above to trace its journey.
        </p>
      </div>

      <div class="h-4" />
    </div>
  </div>
</template>
