<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePermissions } from '../composables/usePermissions'
import { useAuthStore } from '../stores/auth'
import { pallets as palletsApi, packages as packagesApi, blockchain as blockchainApi } from '../api'
import StatusBadge from '../components/StatusBadge.vue'
import { QrcodeStream } from 'vue-qrcode-reader'

const auth = useAuthStore()

// --- Transfer form state ---
const newHolder   = ref('')
const newStatus   = ref('')
const xferLoading = ref(false)
const xferError   = ref(null)
const xferSuccess = ref(false)
const lastScannedId = ref(null)
const manualId = ref('')
const showScanner = ref(false)
const cameraError = ref(null)

// --- Handle Camera Detection ---
const onDetect = async (detectedCodes) => {
  // vue-qrcode-reader v5+ returns an array of detected codes
  const result = detectedCodes[0]
  if (!result || !result.rawValue) return

  const scannedId = result.rawValue

  // Prevent multiple rapid scans of the same item while the API is loading
  if (xferLoading.value) return

  // Trigger the transfer logic with the scanned ID
  await processTransfer(scannedId)
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

const autoStatus = computed(() => {
  const role = auth.user?.role?.toLowerCase() // Assuming your token/user has a 'role' field
  
  if (role === 'distributor') return 'IN_TRANSIT'
  if (role === 'market') return 'AT_MARKET'
  
  // Fallback for edge cases (e.g., quality control roles)
  return 'IN_PRODUCTION' 
})

const handleManualSubmit = () => {
  // 1. Prevent double-submissions if an API call is already running
  if (xferLoading.value) return
  
  // 2. Ensure the input isn't completely empty or just spaces
  if (!manualId.value.trim()) {
    xferError.value = 'Lütfen geçerli bir palet ID girin.' // "Please enter a valid pallet ID"
    return
  }

  // 3. Pass the typed ID to the main processing function
  processTransfer(manualId.value)
}

// --- The Updated Transfer Submit ---
const processTransfer = async (scannedId) => {
  // 1. Ensure form fields are filled before allowing a scan to process
  const holderCode = auth.user?.orgCode
  const status = autoStatus.value
  if (!holderCode) {
    xferError.value = 'Kullanıcı organizasyon kodu bulunamadı. Tekrar giriş yapın.'
    return
  }
  xferLoading.value = true
  xferError.value   = null
  xferSuccess.value = false
  lastScannedId.value = scannedId

  try {
    // The payload is now built silently in the background
    const payload = {
      new_holder_code: holderCode,
      status: status
    }

    // Notice we use the SCANNED ID here, not the route parameter
    await palletsApi.transfer(scannedId, payload)
    
    xferSuccess.value = true
    manualId.value = ''
    // Optional: You could play a beep sound here to confirm success for the worker
    new Audio('/beep.mp3').play()

  } catch (err) {
    const data = err.response?.data
    xferError.value = typeof data === 'string'
      ? data
      : Object.values(data ?? {}).flat().join(' ') || `Transfer failed for ${scannedId}.`
  } finally {
    xferLoading.value = false
  }
}

// --- Visual & Error Helpers ---
const paintBoundingBox = (detectedCodes, ctx) => {
  // Draws a green box around the QR code on the camera view
  for (const detectedCode of detectedCodes) {
    const { boundingBox: { x, y, width, height } } = detectedCode
    ctx.lineWidth = 3
    ctx.strokeStyle = '#22c55e' // Tailwind green-500
    ctx.strokeRect(x, y, width, height)
  }
}

const onError = (err) => {
  if (err.name === 'NotAllowedError') {
    xferError.value = 'Lütfen kamera erişimine izin verin.'
  } else if (err.name === 'NotFoundError') {
    xferError.value = 'Cihazda kamera bulunamadı.'
  } else {
    xferError.value = `Camera error: ${err.message}`
  }
}

</script>

<template>
    <!-- ── HEADER ─────────────────────────────────────────────────────────── -->
<div>
    <div class="bg-gradient-to-br from-emerald-600 to-teal-800 pt-10 pb-10 px-6 rounded-b-[40px] shadow-lg relative">
      
      <div class="flex items-center gap-2 mb-1">
        <span class="text-3xl">📦</span>
        <h1 class="text-2xl font-black text-white">Transfer Pallet</h1>
      </div>
      <p class="text-emerald-200 text-sm mb-6">
        Enter a pallet QR ID or scan the code to transfer it to your organization.
      </p>

      <div class="mb-6 bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/20 flex items-center justify-between shadow-inner">
        <div>
          <p class="text-emerald-200 text-xs uppercase tracking-wider mb-1 font-semibold">Transferring to</p>
          <h2 class="text-white text-lg font-black leading-tight">{{ auth.user?.orgName || 'Your Organization' }}</h2>
          <p class="text-white/70 text-xs mt-1 font-mono bg-black/20 inline-block px-2 py-0.5 rounded border border-white/10">{{ auth.user?.orgCode }}</p>
        </div>
        <div class="text-right">
          <p class="text-emerald-200 text-xs uppercase tracking-wider mb-1 font-semibold">Action</p>
          <span class="px-3 py-1.5 bg-amber-500/20 text-amber-300 font-bold text-sm rounded-lg border border-amber-500/30">
            {{ autoStatus }}
          </span>
        </div>
      </div>

      <div class="flex gap-2 relative z-10">
        <button 
          @click="showScanner = !showScanner"
          :class="showScanner ? 'bg-white/40 border-white/50' : 'bg-white/20 border-white/30'"
          class="hover:bg-white/30 text-white p-3.5 rounded-xl transition-colors shrink-0 flex items-center justify-center border backdrop-blur-sm"
          title="Toggle Scanner"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 hover:cursor-pointer" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>

        <input
          v-model="manualId"
          @keyup.enter="handleManualSubmit"
          type="text"
          placeholder="e.g. PLT-A6609C"
          class="flex-1 px-4 py-3.5 bg-white/15 backdrop-blur-sm border border-white/30 rounded-xl
                 text-white placeholder-emerald-300 focus:outline-none focus:border-white
                 focus:ring-1 focus:ring-white transition-colors text-sm uppercase tracking-wider font-mono"
        />
        
        <button
          @click="handleManualSubmit"
          :disabled="xferLoading || !manualId.trim()"
          class="bg-emerald-50 text-emerald-700 font-black px-5 py-3.5 rounded-xl
                 hover:bg-zinc-300 transition-colors shrink-0
                 disabled:opacity-50 disabled:cursor-not-allowed hover:cursor-pointer"
        >
          {{ xferLoading && !showScanner ? '...' : 'Transfer' }}
        </button>
      </div>

      <div 
        v-if="showScanner" 
        class="mt-4 bg-black/40 backdrop-blur-md rounded-xl p-3 border border-white/20 overflow-hidden shadow-inner relative"
      >
        <div class="flex justify-between items-center mb-2 px-1">
          <span class="text-xs font-semibold text-emerald-100 uppercase tracking-widest flex items-center gap-2">
            <span v-if="xferLoading" class="animate-pulse w-2 h-2 bg-emerald-400 rounded-full"></span>
            {{ xferLoading ? 'Processing...' : 'Point camera at pallet' }}
          </span>
          <button @click="showScanner = false" class="text-white hover:text-emerald-300 text-sm font-bold transition-colors">✕ Close</button>
        </div>
        
        <div class="flex justify-center w-full pb-2 relative">
          <div class="w-100 max-w-full rounded-2xl overflow-hidden relative aspect-square bg-black border-2 border-white/10 shadow-xl">
            
            <div v-if="xferLoading" class="absolute inset-0 bg-black/70 z-10 flex flex-col items-center justify-center text-white backdrop-blur-sm">
               <span class="animate-pulse font-semibold tracking-wide">Transferring...</span>
               <span class="text-xs font-mono text-emerald-300 mt-2">{{ lastProcessedId }}</span>
            </div>

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

      <div v-if="xferError" class="mt-4 bg-red-500/20 backdrop-blur-md text-red-100 p-4 rounded-xl border border-red-500/50 text-sm font-medium shadow-sm">
        {{ xferError }}
      </div>
      <div v-if="xferSuccess" class="mt-4 bg-emerald-500/30 backdrop-blur-md text-white p-4 rounded-xl border border-emerald-400/50 text-sm font-medium shadow-sm flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-emerald-300" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        </svg>
        Transferred: <strong class="font-mono text-emerald-100">{{ lastProcessedId }}</strong>
      </div>

    </div>
  </div>
</template>