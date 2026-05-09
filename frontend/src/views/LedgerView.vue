<script setup>
import { ref, computed, onMounted } from 'vue'
import { blockchain as blockchainApi } from '../api'
import StatusBadge from '../components/StatusBadge.vue'

const logs = ref([])
const loading = ref(true)
const error = ref(null)
const activeFilter = ref('ALL')

const actionTypes = ['ALL', 'PROD', 'TRAN', 'QUAL', 'RECV', 'CERT']

const actionConfig = {
  PROD: { label: 'Production',   emoji: '🏭' },
  TRAN: { label: 'Transfer',     emoji: '🚛' },
  QUAL: { label: 'Quality',      emoji: '✅' },
  RECV: { label: 'Received',     emoji: '📥' },
  CERT: { label: 'Certificate',  emoji: '📜' },
}

const filteredLogs = computed(() => {
  if (activeFilter.value === 'ALL') return logs.value
  return logs.value.filter((l) => l.action_type === activeFilter.value)
})

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(dateStr))
}

const shortHash = (hash) => {
  if (!hash || hash.length < 16) return hash || '—'
  return `${hash.slice(0, 10)}…${hash.slice(-8)}`
}

onMounted(async () => {
  try {
    const res = await blockchainApi.list()
    logs.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
  } catch {
    error.value = 'Failed to load blockchain logs.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="w-full max-w-4xl mx-auto">

    <!-- HEADER -->
    <div class="bg-gradient-to-br from-violet-700 to-purple-900 pt-10 pb-8 px-6 rounded-b-[32px] shadow-lg">
      <h1 class="text-2xl font-black text-white mb-1">Blockchain Ledger</h1>
      <p class="text-violet-300 text-sm">Immutable transaction history on Hyperledger Fabric</p>

      <div class="mt-5 bg-white/10 rounded-2xl px-4 py-4 border border-white/20 flex items-center gap-3">
        <span class="text-3xl">🔗</span>
        <div class="flex-1">
          <p class="text-white font-bold text-sm">Hyperledger Fabric</p>
          <p class="text-violet-300 text-xs">
            {{ loading ? 'Loading…' : `${logs.length} transactions on chain` }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse"></span>
          <span class="text-emerald-400 text-xs font-bold">Active</span>
        </div>
      </div>
    </div>

    <!-- FILTER TABS -->
    <div class="px-5 mt-5 flex gap-2 overflow-x-auto pb-1">
      <button
        v-for="type in actionTypes"
        :key="type"
        @click="activeFilter = type"
        class="shrink-0 px-4 py-2 rounded-full text-sm font-bold transition-colors"
        :class="activeFilter === type
          ? 'bg-violet-600 text-white shadow-sm'
          : 'bg-white text-stone-600 border border-stone-200 hover:border-violet-300'"
      >
        {{ type === 'ALL' ? 'All' : `${actionConfig[type].emoji} ${actionConfig[type].label}` }}
      </button>
    </div>

    <!-- TRANSACTION LIST -->
    <div class="px-5 py-5 space-y-3">

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
        ⚠️ {{ error }}
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 6" :key="i" class="bg-white rounded-2xl h-28 animate-pulse border border-stone-100"></div>
      </div>

      <div v-else-if="filteredLogs.length === 0"
           class="bg-white rounded-2xl p-12 text-center border border-stone-100 shadow-sm">
        <div class="text-5xl mb-4">📭</div>
        <p class="text-stone-600 font-bold">No transactions found</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="log in filteredLogs"
          :key="log.tx_hash"
          class="bg-white rounded-2xl p-5 border border-stone-100 shadow-sm hover:shadow-md transition-shadow"
        >
          <!-- Top row: action type + timestamp + tx status
               StatusBadge used twice here: once for action type, once for tx status.
               The variant prop tells the component which color map to use. -->
          <div class="flex items-start justify-between gap-3 mb-3">
            <div class="flex items-center gap-3">
              <span class="text-2xl">{{ actionConfig[log.action_type]?.emoji || '🔗' }}</span>
              <div>
                <StatusBadge :status="log.action_type" variant="action" />
                <p class="text-xs text-stone-400 mt-1">{{ formatDate(log.timestamp) }}</p>
              </div>
            </div>
            <StatusBadge :status="log.status" variant="tx" class="shrink-0" />
          </div>

          <!-- Tx hash -->
          <div class="bg-stone-50 rounded-xl px-3 py-2 font-mono text-xs text-stone-500
                      flex items-center justify-between gap-2">
            <span class="truncate">{{ log.tx_hash }}</span>
            <span class="shrink-0 text-stone-300 hidden sm:block">{{ shortHash(log.tx_hash) }}</span>
          </div>

          <!-- Org + block number -->
          <div class="flex items-center gap-3 mt-3 text-xs text-stone-400">
            <span class="truncate">{{ log.organization?.name || log.organization || '—' }}</span>
            <span v-if="log.block_number" class="ml-auto shrink-0 font-mono">
              Block #{{ log.block_number }}
            </span>
          </div>
        </div>
      </div>

      <div class="h-4"></div>
    </div>
  </div>
</template>
