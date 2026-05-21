<!-- src/views/HistoryView.vue — QR Traceability Scanner
     This page is PUBLIC — no login required.
     Consumers scan their egg package QR code and see the full supply chain journey.

     New concepts:
       - @keyup.enter: run a method when Enter is pressed
       - Template refs (not used here, but note that v-model replaces them for inputs)
       - Conditional blocks with v-if / v-else-if / v-else
       - CSS-only vertical timeline using relative/absolute positioning -->
<script setup>
import { ref } from 'vue'
import { packages as packagesApi } from '../api'


const qrInput = ref('')
const history = ref(null)
const loading = ref(false)
const error = ref(null)

const actionConfig = {
  PROD: { label: 'Production',   color: 'bg-blue-100 text-blue-700',    dot: 'bg-blue-500',    emoji: '🏭' },
  TRAN: { label: 'Transfer',     color: 'bg-amber-100 text-amber-700',   dot: 'bg-amber-500',   emoji: '🚛' },
  QUAL: { label: 'Quality Check',color: 'bg-emerald-100 text-emerald-700',dot:'bg-emerald-500', emoji: '✅' },
  RECV: { label: 'Received',     color: 'bg-purple-100 text-purple-700', dot: 'bg-purple-500',  emoji: '📥' },
  CERT: { label: 'Certificate',  color: 'bg-pink-100 text-pink-700',     dot: 'bg-pink-500',    emoji: '📜' },
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(dateStr))
}

// const fetchPackageHistory = async (packageId) => {
//   if (!packageId) return
  
//   // 1. Reset state before fetching
//   loading.value = true
//   error.value = null
//   history.value = null 

//   try {
//     // 2. Make the API request using your centralized api.js
//     const response = await packages.history(packageId)
    
//     // 3. Assign the returned data to the history ref
//     // (Depending on your Django pagination, this might be response.data.results)
//     history.value = response.data

//   } catch (err) {
//     console.error("Failed to load timeline data:", err)
//     // Grab the error message from the backend if it exists
//     error.value = err.response?.data?.detail || "Could not find history for this package."
//   } finally {
//     // 4. Turn off loading state regardless of success or failure
//     loading.value = false
//   }
// }

const handleSearch = async () => {
  const id = qrInput.value.trim()
  if (!id) return

  // Reset state before each search
  error.value = null
  history.value = null
  loading.value = true

  try {
    // 1. Fetch ONLY the public blockchain history
    const histRes = await packagesApi.history(id)
    
    // 2. Extract the timeline
    const rawHistory = histRes.data
    history.value = Array.isArray(rawHistory) ? rawHistory : (rawHistory?.timeline || [])

    // Optional: If history is completely empty, you can treat it as a 404
    if (history.value.length === 0) {
      throw { response: { status: 404 } }
    }

  } catch (err) {
    if (err.response?.status === 404) {
      error.value = `Package "${id}" not found. Please check the QR code.`
    } else {
      error.value = 'Could not fetch traceability data. Make sure the server is running.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-2xl mx-auto">

    <!-- ============================================================
         HEADER — green theme for "fresh from farm"
         ============================================================ -->
    <div class="bg-gradient-to-br from-emerald-600 to-teal-800 pt-10 pb-10 px-6 rounded-b-[40px] shadow-lg">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-3xl">🔍</span>
        <h1 class="text-2xl font-black text-white">Trace Your Eggs</h1>
      </div>
      <p class="text-emerald-200 text-sm mb-6">
        Enter a package QR ID to see its complete journey from farm to table.
      </p>

      <!-- Search bar
           @keyup.enter is a shorthand for pressing the Enter key on the keyboard.
           This way the user doesn't have to click the button. -->
      <div class="flex gap-2">
        <input
          v-model="qrInput"
          @keyup.enter="handleSearch"
          type="text"
          placeholder="e.g. PKG-2024-001"
          class="flex-1 px-4 py-3.5 bg-white/15 backdrop-blur-sm border border-white/30 rounded-xl
                 text-white placeholder-emerald-300 focus:outline-none focus:border-white
                 focus:ring-1 focus:ring-white transition-colors text-sm"
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
    </div>

    <!-- ============================================================
         RESULTS AREA
         ============================================================ -->
    <div class="px-5 py-6 space-y-5">

      <!-- Error message -->
      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex gap-3">
        <span class="shrink-0 text-lg">⚠️</span>
        <p>{{ error }}</p>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-4">
        <div class="bg-white rounded-2xl h-36 animate-pulse border border-stone-100"></div>
        <div class="bg-white rounded-2xl h-72 animate-pulse border border-stone-100"></div>
      </div>

      <!-- Package info card — shown after a successful search -->

      <!-- ============================================================
           TIMELINE — vertical list of blockchain events
           The trick: a pseudo-line is drawn using a thin absolute div,
           and each event's dot sits on top of it.
           ============================================================ -->
      <div v-if="history && history.length > 0">
        <h3 class="text-xs font-black text-stone-400 uppercase tracking-widest mb-5">
          Supply Chain Journey
        </h3>

        <!-- relative on the container + absolute on the line child -->
        <div class="relative">
          <!-- The vertical connector line -->
          <div class="absolute left-5 top-5 bottom-5 w-0.5 bg-stone-200 rounded-full"></div>

          <div class="space-y-4">
            <div
              v-for="(event, index) in history"
              :key="index"
              class="relative flex items-start gap-4"
            >
              <!-- Timeline dot — sits on the vertical line -->
              <div
                class="relative z-10 w-10 h-10 rounded-full flex items-center justify-center
                       text-lg shadow-md border-2 border-white shrink-0"
                :class="actionConfig[event.action_type]?.color?.split(' ')[0] || 'bg-stone-100'"
              >
                {{ actionConfig[event.action_type]?.emoji || '🔗' }}
              </div>

            <!-- Event card -->
              <div class="flex-1 bg-white rounded-2xl p-4 border border-stone-100 shadow-sm mb-2">
                
                <!-- Header: Badges -->
                <div class="flex items-start justify-between gap-2 mb-2">
                  <!-- Use action_type_display for a human-readable badge -->
                  <span class="px-2 py-1 bg-stone-100 text-stone-600 rounded text-[10px] font-black uppercase tracking-wider">
                    {{ event.action_type_display }}
                  </span>
                  <span 
                    class="px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider shrink-0"
                    :class="event.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'"
                  >
                    {{ event.status_display }}
                  </span>
                </div>

                <!-- Organization & Time -->
                <p class="text-sm font-bold text-stone-800">
                  {{ event.organization_name || 'Unknown Organization' }}
                </p>
                <p class="text-xs text-stone-400 mt-0.5">{{ formatDate(event.timestamp) }}</p>

                <!-- ==========================================
                    DYNAMIC PAYLOAD DATA (The "Good UI" part)
                    ========================================== -->
                <div class="mt-3 bg-stone-50 border border-stone-100 rounded-xl p-3 text-xs text-stone-600 space-y-2">
                  
                  <!-- IF PRODUCTION (Package Info) -->
                  <template v-if="event.action_type === 'PROD' && event.payload.action === 'PACKAGE_CREATED'">
                    <div class="grid grid-cols-2 gap-2">
                      <div><span class="text-stone-400 block mb-0.5 text-[10px] uppercase">Laying Date</span> <span class="font-medium">{{ event.payload.laying_date }}</span></div>
                      <div><span class="text-stone-400 block mb-0.5 text-[10px] uppercase">Expiry Date</span> <span class="font-medium">{{ event.payload.expiry_date }}</span></div>
                      <div><span class="text-stone-400 block mb-0.5 text-[10px] uppercase">Class</span> <span class="font-medium">{{ event.payload.quality_class }}</span></div>
                      <div><span class="text-stone-400 block mb-0.5 text-[10px] uppercase">Feeding</span> <span class="font-medium">{{ event.payload.feeding_type }}</span></div>
                    </div>
                  </template>

                  <!-- IF PRODUCTION (Pallet Info) -->
                  <template v-else-if="event.action_type === 'PROD' && event.payload.action === 'PALLET_CREATED'">
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 text-[10px] uppercase">Vet Certificate</span>
                      <span class="font-mono font-medium">{{ event.payload.certificate_no }}</span>
                    </div>
                    <div v-if="event.payload.auto_vet_approval" class="mt-1 text-emerald-600 font-medium flex items-center gap-1">
                      <span>✓</span> Auto-Approved
                    </div>
                  </template>

                  <!-- IF TRANSFER OR RECEIVED -->
                  <template v-else-if="event.action_type === 'TRAN' || event.action_type === 'RECV'">
                    <div class="flex items-center gap-2 mb-2 bg-white p-2 rounded border border-stone-100">
                      <div class="flex-1 text-center font-bold">{{ event.payload.transfer_from_org }}</div>
                      <div class="text-stone-300">➔</div>
                      <!-- Assuming you might map org codes to names later, but for now show code -->
                      <div class="flex-1 text-center font-bold text-stone-500">Org: {{ event.payload.transfer_to_org_code }}</div>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-stone-400 text-[10px] uppercase">Status Update</span>
                      <span class="font-mono font-medium text-blue-600">{{ event.payload.new_status }}</span>
                    </div>
                  </template>
                </div>

                <!-- Tx hash in monospace -->
                <div class="bg-stone-50 border border-stone-100 rounded-lg px-3 py-2 mt-3 font-mono text-[10px] text-stone-400 overflow-hidden flex justify-between items-center group cursor-copy" title="Copy Hash">
                  <span class="block truncate mr-2">{{ event.tx_hash }}</span>
                  <span class="opacity-0 group-hover:opacity-100 transition-opacity">📋</span>
                </div>

              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty history state -->
      <div
        v-else-if="history && history.length === 0"
        class="bg-white rounded-2xl p-10 text-center border border-stone-100 shadow-sm"
      >
        <div class="text-4xl mb-3">📭</div>
        <p class="text-stone-600 font-bold">No history recorded</p>
        <p class="text-stone-400 text-sm mt-1">This package has no blockchain transactions yet.</p>
      </div>

      <!-- Default state — shown before any search -->
      <div
        v-else-if="!loading && !error"
        class="text-center py-14"
      >
        <div class="text-7xl mb-5">🥚</div>
        <p class="text-stone-700 font-black text-xl">Know Your Eggs</p>
        <p class="text-stone-400 text-sm mt-2 leading-relaxed">
          Scan the QR code on your egg package<br>or enter the ID above to trace its journey.
        </p>
      </div>

      <div class="h-4"></div>
    </div>
  </div>
</template>
