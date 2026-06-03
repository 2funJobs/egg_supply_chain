<script setup>
import { ref, computed, onMounted } from 'vue'
import { orders as ordersApi } from '../api'
import Qrcode from 'qrcode.vue'

const EGG_EMOJI = { 0: '🌿', 1: '🌾', 2: '🏠', 3: '🔒' }

const STATUS_TABS = [
  { value: 'ASSIGNED',      label: 'Bekliyor'  },
  { value: 'IN_PRODUCTION', label: 'Üretimde'  },
  { value: 'SHIPPED',       label: 'Kargoda'   },
  { value: 'DELIVERED',     label: 'Teslim'    },
]

const allOrders     = ref([])
const loading       = ref(true)
const error         = ref(null)
const activeTab     = ref('ASSIGNED')
const accepting     = ref(null)      // order ID currently being accepted
const acceptResults = ref({})        // { [orderId]: responseData }
const cancelConfirming = ref(null)
const cancelling       = ref(null)

const cancelOrder = async (orderId) => {
  cancelling.value       = orderId
  cancelConfirming.value = null
  try {
    await ordersApi.cancel(orderId)
    // Üretici reddettiğinde assigned_producer null olur → listeden düşer
    allOrders.value = allOrders.value.filter(o => o.id !== orderId)
  } catch (e) {
    error.value = e.response?.data?.error || 'Sipariş reddedilemedi.'
  } finally {
    cancelling.value = null
  }
}

const filtered = computed(() =>
  allOrders.value.filter(o => o.status === activeTab.value)
)

const countByStatus = computed(() => {
  const counts = {}
  for (const o of allOrders.value) counts[o.status] = (counts[o.status] || 0) + 1
  return counts
})

const totalPackages = (order) =>
  order.items.reduce((sum, i) => sum + i.package_quantity, 0)

const formatDate = (str) => {
  if (!str) return '—'
  return new Intl.DateTimeFormat('tr-TR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(str))
}

const fetchOrders = async () => {
  try {
    const res = await ordersApi.list()
    allOrders.value = Array.isArray(res.data) ? res.data : (res.data.results ?? [])
  } catch {
    error.value = 'Siparişler yüklenemedi.'
  } finally {
    loading.value = false
  }
}

const acceptOrder = async (order) => {
  accepting.value = order.id
  error.value = null
  try {
    const res = await ordersApi.accept(order.id)
    acceptResults.value[order.id] = res.data
    // Update locally so the order moves to the correct tab
    const idx = allOrders.value.findIndex(o => o.id === order.id)
    if (idx !== -1) allOrders.value[idx] = { ...allOrders.value[idx], status: 'IN_PRODUCTION' }
    activeTab.value = 'IN_PRODUCTION'
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.error || 'Sipariş kabul edilemedi.'
  } finally {
    accepting.value = null
  }
}

// Download logic with dynamic targeting
const downloadQR = (qrValue) => {
  // Target the specific canvas using the dynamically generated ID
  const canvasId = `pallet-qr-canvas-${qrValue}`
  const canvas = document.getElementById(canvasId)
  
  if (!canvas) {
    console.error(`QR Code canvas not found for ID: ${canvasId}`)
    return
  }

  // Convert canvas to image and trigger download
  const imageUrl = canvas.toDataURL('image/png')
  const downloadLink = document.createElement('a')
  
  downloadLink.href = imageUrl
  downloadLink.download = `Pallet-${qrValue}.png`
  
  document.body.appendChild(downloadLink)
  downloadLink.click()
  document.body.removeChild(downloadLink)
}

onMounted(fetchOrders)
</script>

<template>
  <div class="w-full max-w-4xl mx-auto">

    <!-- HEADER -->
    <div class="bg-gradient-to-br from-stone-700 to-stone-900 pt-10 pb-10 px-6 rounded-b-[32px] shadow-lg">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-black text-white">Gelen Siparişler</h1>
          <p class="text-stone-400 text-sm mt-1">
            {{ loading ? 'Yükleniyor…' : `${allOrders.length} sipariş toplam` }}
          </p>
        </div>
        <div v-if="countByStatus['ASSIGNED']"
             class="bg-orange-500 text-white px-3 py-1.5 rounded-xl font-black text-sm animate-pulse">
          {{ countByStatus['ASSIGNED'] }} bekliyor
        </div>
      </div>
    </div>

    <!-- ERROR -->
    <div v-if="error"
         class="mx-5 mt-4 bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex justify-between items-center">
      ⚠️ {{ error }}
      <button @click="error = null" class="font-bold ml-3">✕</button>
    </div>

    <!-- STATUS TABS -->
    <div class="px-5 mt-5 flex gap-2 overflow-x-auto pb-1">
      <button
        v-for="tab in STATUS_TABS"
        :key="tab.value"
        @click="activeTab = tab.value"
        class="shrink-0 px-4 py-2 rounded-full text-sm font-bold transition-colors flex items-center gap-1.5"
        :class="activeTab === tab.value
          ? 'bg-stone-800 text-white shadow-sm'
          : 'bg-white text-stone-600 border border-stone-200 hover:border-stone-400'"
      >
        {{ tab.label }}
        <span
          v-if="countByStatus[tab.value]"
          class="text-xs font-black px-1.5 py-0.5 rounded-full"
          :class="activeTab === tab.value
            ? 'bg-white/20 text-white'
            : 'bg-stone-100 text-stone-600'"
        >{{ countByStatus[tab.value] }}</span>
      </button>
    </div>

    <!-- ORDER LIST -->
    <div class="px-5 py-5 space-y-4">

      <div v-if="loading" class="space-y-4">
        <div v-for="i in 3" :key="i"
             class="bg-white rounded-2xl h-44 animate-pulse border border-stone-100" />
      </div>

      <div v-else-if="filtered.length === 0"
           class="bg-white rounded-2xl p-12 text-center border border-stone-100 shadow-sm">
        <div class="text-5xl mb-4">📭</div>
        <p class="text-stone-600 font-bold">Sipariş yok</p>
        <p class="text-stone-400 text-sm mt-1">Bu kategoride henüz sipariş bulunmuyor.</p>
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="order in filtered"
          :key="order.id"
          class="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden"
        >
          <!-- Card header -->
          <div class="px-5 pt-4 pb-3 flex items-start justify-between border-b border-stone-50">
            <div>
              <span class="font-mono text-xs text-stone-400 font-bold tracking-wider">{{ order.id }}</span>
              <div class="flex items-center gap-2 mt-0.5">
                <svg class="w-4 h-4 text-stone-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
                <span class="font-bold text-stone-800 text-sm">{{ order.market_detail?.name ?? '—' }}</span>
              </div>
            </div>
            <span class="text-xs text-stone-400 shrink-0 mt-1">{{ formatDate(order.created_at) }}</span>
          </div>

          <!-- Items -->
          <div class="px-5 py-4">
            <p class="text-xs font-bold text-stone-400 uppercase tracking-wider mb-2">İçerik</p>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="item in order.items"
                :key="item.id"
                class="bg-stone-50 border border-stone-200 rounded-lg px-2.5 py-1.5 flex items-center gap-1.5 text-xs"
              >
                <span>{{ EGG_EMOJI[item.feeding_type] ?? '🥚' }}</span>
                <span class="font-semibold text-stone-700">{{ item.feeding_type_display }}</span>
                <span class="text-stone-300">·</span>
                <span class="text-stone-500">{{ item.capacity_display }}</span>
                <span class="text-stone-300">·</span>
                <span class="font-bold text-stone-700">{{ item.package_quantity }} adet</span>
              </div>
            </div>
            <p class="text-xs text-stone-400 mt-2.5">
              Toplam: <strong class="text-stone-600">{{ totalPackages(order) }} paket</strong>
            </p>
          </div>

          <!-- Footer -->
          <div class="px-5 pb-4">

            <!-- Success result (just accepted this session) -->
            <div
              v-if="acceptResults[order.id]"
              class="bg-emerald-50 border border-emerald-200 rounded-xl p-4"
            >
              <div class="flex items-center gap-2 text-emerald-700 font-bold text-sm mb-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                Sipariş Kabul Edildi — Üretim Başladı
              </div>
              <div class="text-xs text-emerald-700 space-y-1">
                <div>Palet: <strong class="font-mono">{{ acceptResults[order.id].pallet_qr }}</strong></div>
                <div>Üretilen paket: <strong>{{ acceptResults[order.id].total_packages }}</strong></div>
                <div>Sertifika: <strong>{{ acceptResults[order.id].certificate_used }}</strong></div>
              </div>
            </div>

            <!-- Accept button -->
            <div
              v-else-if="cancelConfirming === order.id"
              class="bg-red-50 border border-red-200 rounded-xl p-4"
            >
              <p class="text-sm font-bold text-red-700 mb-3">
                Bu siparişi reddetmek istediğinizden emin misiniz?
              </p>
              <div class="flex gap-2">
                <button
                  @click="cancelOrder(order.id)"
                  :disabled="cancelling === order.id"
                  class="justify-center justify-items-center mx-auto w-50 bg-red-500 text-white py-2.5 rounded-xl font-bold text-sm
                        hover:bg-red-600 transition-colors disabled:opacity-60"
                >
                  {{ cancelling === order.id ? 'Reddediliyor…' : 'Evet, Reddet' }}
                </button>
                <button
                  @click="cancelConfirming = null"
                  class="justify-center justify-items-center mx-auto w-50 bg-white border border-stone-200 text-stone-600 py-2.5 rounded-xl font-bold text-sm hover:bg-stone-50 transition-colors"
                >
                  Vazgeç
                </button>
              </div>
            </div>

            <!-- Kabul Et + Reddet butonları -->
            <template v-else-if="order.status === 'ASSIGNED'">
              <button
                @click="acceptOrder(order)"
                :disabled="accepting === order.id"
                class="w-50 bg-orange-500 text-white py-3.5 rounded-xl font-bold text-sm
                      hover:bg-orange-600 transition-colors disabled:opacity-60
                      flex items-center justify-center gap-2"
              >
                <svg v-if="accepting !== order.id" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                {{ accepting === order.id ? 'İşleniyor…' : 'Siparişi Kabul Et' }}
              </button>
              <button
                @click="cancelConfirming = order.id"
                class="justify-center justify-items-center mx-auto w-50 mt-2 bg-white border-2 border-red-200 text-red-500 py-3 rounded-xl
                      font-bold text-sm hover:bg-red-50 hover:border-red-300 transition-colors"
              >
                Reddet
              </button>
            </template>
            <!--  -->
          </div>
        </div>
      </div>

      <div class="h-4" />
    </div>
  </div>
</template>