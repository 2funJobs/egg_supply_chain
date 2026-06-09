<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { orders as ordersApi, orderItems as orderItemsApi } from '../api'

// ── Sabitler ──────────────────────────────────────────────────────────────────

const EGG_TYPES = [
  { value: 0, label: 'Organik',         emoji: '🌿', desc: 'Sertifikalı organik beslenme', bg: 'bg-emerald-50', border: 'border-emerald-200', dot: 'bg-emerald-500' },
  { value: 1, label: 'Serbest Gezinen', emoji: '🌾', desc: 'Açık alan erişimi',             bg: 'bg-amber-50',   border: 'border-amber-200',   dot: 'bg-amber-500'   },
  { value: 2, label: 'Kümesli',         emoji: '🏠', desc: 'Kapalı kümes ortamı',           bg: 'bg-orange-50',  border: 'border-orange-200',  dot: 'bg-orange-500'  },
  { value: 3, label: 'Kafesli',         emoji: '🔒', desc: 'Standart üretim',               bg: 'bg-stone-50',   border: 'border-stone-200',   dot: 'bg-stone-400'   },
]

const CAPACITIES = [
  { value: 6,  label: "6'lı Paket"  },
  { value: 15, label: "15'li Paket" },
  { value: 30, label: "30'lu Paket" },
]

const STATUS_STEPS = [
  { key: 'ASSIGNED',      label: 'Atandı'      },
  { key: 'IN_PRODUCTION', label: 'Hazırlanıyor' },
  { key: 'SHIPPED',       label: 'Yolda'        },
  { key: 'DELIVERED',     label: 'Teslim'       },
]
const STATUS_ORDER = STATUS_STEPS.map(s => s.key)

const STATUS_META = {
  ASSIGNED:      { label: 'Üreticiye Atandı', color: 'text-amber-600',   bg: 'bg-amber-50',   border: 'border-amber-200'   },
  IN_PRODUCTION: { label: 'Hazırlanıyor',     color: 'text-orange-600',  bg: 'bg-orange-50',  border: 'border-orange-200'  },
  SHIPPED:       { label: 'Yolda',            color: 'text-blue-600',    bg: 'bg-blue-50',    border: 'border-blue-200'    },
  DELIVERED:     { label: 'Teslim Edildi',    color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  CANCELLED:     { label: 'İptal Edildi', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
}

// ── State ─────────────────────────────────────────────────────────────────────

const activeView     = ref('cart')
const error          = ref(null)
const cancelConfirming = ref(null)   // onay beklenen sipariş ID'si
const cancelling       = ref(null)   // istek atılan sipariş ID'si

const confirmCancel = (orderId) => { cancelConfirming.value = orderId }
const abortCancel   = ()        => { cancelConfirming.value = null    }

const cancelOrder = async (orderId) => {
  cancelling.value       = orderId
  cancelConfirming.value = null
  try {
    await ordersApi.cancel(orderId)
    await fetchAllOrders()
  } catch (e) {
    error.value = e.response?.data?.error || 'Sipariş iptal edilemedi.'
  } finally {
    cancelling.value = null
  }
}

// Sepet
const cart           = ref(null)
const loading        = ref(true)
const selected       = ref(null)    // { feedingType, label, capacity, quantity }
const saving         = ref(false)
const checkingOut    = ref(false)
const checkoutResult = ref(null)

// Geçmiş
const allOrders      = ref([])
const historyLoading = ref(false)

// ── Computed ──────────────────────────────────────────────────────────────────

const cartItemCount = computed(() =>
  cart.value?.items?.reduce((sum, i) => sum + i.package_quantity, 0) ?? 0
)

const submittedOrders = computed(() =>
  allOrders.value.filter(o => o.status !== 'DRAFT')
)

// Aktif siparişler: badge için (henüz teslim edilmemiş)
const activeOrderCount = computed(() =>
  allOrders.value.filter(o =>
    ['ASSIGNED', 'IN_PRODUCTION', 'SHIPPED'].includes(o.status)
  ).length
)

// ── Yardımcılar ───────────────────────────────────────────────────────────────

const emojiFor  = (feedingType) => EGG_TYPES.find(e => e.value === feedingType)?.emoji ?? '🥚'
const stepIndex = (status)      => STATUS_ORDER.indexOf(status)

const formatDate = (str) => str
  ? new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short' }).format(new Date(str))
  : '—'

// ── Sepet işlemleri ───────────────────────────────────────────────────────────

const fetchCart = async () => {
  try {
    const res  = await ordersApi.myCart()
    cart.value = res.data
  } catch {
    error.value = 'Sepet yüklenemedi.'
  } finally {
    loading.value = false
  }
}

const openSelector = (egg) => {
  selected.value = { feedingType: egg.value, label: egg.label, capacity: 6, quantity: 1 }
}

const addToCart = async () => {
  if (!selected.value || !cart.value) return
  saving.value = true
  try {
    await orderItemsApi.create({
      order:            cart.value.id,
      feeding_type:     selected.value.feedingType,
      capacity:         selected.value.capacity,
      package_quantity: selected.value.quantity,
    })
    await fetchCart()
    selected.value = null
  } catch {
    error.value = 'Ürün eklenemedi.'
  } finally {
    saving.value = false
  }
}

const removeItem = async (itemId) => {
  try {
    await orderItemsApi.remove(itemId)
    await fetchCart()
  } catch {
    error.value = 'Ürün silinemedi.'
  }
}

const checkout = async () => {
  if (!cart.value) return
  checkingOut.value = true
  try {
    const res        = await ordersApi.checkout(cart.value.id)
    checkoutResult.value = res.data
    // Sepet + geçmişi paralel güncelle — history tab hazır olsun
    await Promise.all([fetchCart(), fetchAllOrders()])
  } catch {
    error.value = 'Sipariş gönderilemedi.'
  } finally {
    checkingOut.value = false
  }
}

// ── Geçmiş işlemleri ──────────────────────────────────────────────────────────

const fetchAllOrders = async () => {
  historyLoading.value = true
  try {
    const res       = await ordersApi.list()
    allOrders.value = Array.isArray(res.data) ? res.data : (res.data.results ?? [])
  } catch {
    // Kritik değil, sessiz geç
  } finally {
    historyLoading.value = false
  }
}

// Tab her açıldığında taze veri çek
watch(activeView, (v) => { if (v === 'history') fetchAllOrders() })

onMounted(fetchCart)
</script>

<template>
  <div class="w-full max-w-4xl mx-auto pb-32">

    <!-- ── HEADER ─────────────────────────────────────────────────────────── -->
    <div class="bg-gradient-to-br from-orange-500 to-orange-700 pt-10 pb-0 px-6 rounded-b-[32px] shadow-lg">

      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-black text-white">Siparişler</h1>
          <p class="text-orange-200 text-sm mt-1">
            {{ activeView === 'cart' ? 'Sepete ürün ekleyin' : 'Siparişlerinizi takip edin' }}
          </p>
        </div>
        <!-- Sepet badge: sadece sepet tabında ve dolu olduğunda -->
        <div
          v-if="activeView === 'cart' && cartItemCount > 0"
          class="bg-white text-orange-600 px-3 py-1.5 rounded-xl font-black text-sm flex items-center gap-2 shadow"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/>
          </svg>
          {{ cartItemCount }} paket
        </div>
      </div>

      <!-- Tab butonları -->
      <div class="flex">
        <button
          @click="activeView = 'cart'"
          class="flex-1 py-3 text-sm font-bold transition-colors border-b-2 hover:cursor-pointer"
          :class="activeView === 'cart'
            ? 'border-white text-white'
            : 'border-transparent text-orange-200 hover:text-white'"
        >
          Sepet
        </button>
        <button
          @click="activeView = 'history'"
          class="flex-1 py-3 text-sm font-bold transition-colors border-b-2 flex items-center justify-center gap-2 hover:cursor-pointer"
          :class="activeView === 'history'
            ? 'border-white text-white'
            : 'border-transparent text-orange-200 hover:text-white'"
        >
          Siparişlerim
          <span
            v-if="activeOrderCount > 0"
            class="text-xs font-black px-1.5 py-0.5 rounded-full"
            :class="activeView === 'history' ? 'bg-white/25 text-white' : 'bg-white/15 text-orange-100'"
          >{{ activeOrderCount }}</span>
        </button>
      </div>
    </div>

    <!-- ── HATA BANNER (her iki tabda görünür) ────────────────────────────── -->
    <div
      v-if="error"
      class="mx-5 mt-4 bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex justify-between items-center"
    >
      ⚠️ {{ error }}
      <button @click="error = null" class="font-bold ml-3">✕</button>
    </div>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!--  SEPET GÖRÜNÜMÜ                                                     -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <template v-if="activeView === 'cart'">

      <!-- Sipariş başarı ekranı -->
      <div
        v-if="checkoutResult"
        class="mx-5 mt-6 bg-emerald-50 border border-emerald-200 rounded-2xl p-8 text-center"
      >
        <div class="text-5xl mb-3">✅</div>
        <div class="font-black text-emerald-800 text-lg">Sipariş Alındı!</div>
        <div class="text-emerald-700 text-sm mt-2 leading-relaxed">
          <strong>{{ checkoutResult.producer }}</strong> çiftliğine yönlendirildi.
          <br>Mesafe: {{ checkoutResult.distance_km }} km
        </div>
        <div class="flex gap-3 justify-center mt-5">
          <button
            @click="() => { checkoutResult = null; activeView = 'history' }"
            class="bg-emerald-600 text-white px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-emerald-700 transition-colors"
          >
            Siparişimi Takip Et →
          </button>
          <button
            @click="checkoutResult = null"
            class="bg-white border border-emerald-200 text-emerald-700 px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-emerald-50 transition-colors"
          >
            Yeni Sipariş Ver
          </button>
        </div>
      </div>

      <template v-else>
        <!-- Yumurta tipi seçim grid'i -->
        <div class="px-5 pt-6 pb-2">
          <p class="text-xs font-bold text-stone-400 uppercase tracking-wider mb-4">Yumurta Tipi Seçin</p>
          <div class="grid grid-cols-2 gap-3">
            <button
              v-for="egg in EGG_TYPES"
              :key="egg.value"
              @click="openSelector(egg)"
              class="text-left rounded-2xl p-5 border-2 transition-all active:scale-95 hover:shadow-md hover:cursor-pointer"
              :class="[egg.bg, egg.border]"
            >
              <div class="text-3xl mb-2">{{ egg.emoji }}</div>
              <div class="font-bold text-stone-800 text-sm">{{ egg.label }}</div>
              <div class="text-xs text-stone-500 mt-0.5 leading-snug">{{ egg.desc }}</div>
              <div class="mt-3 flex justify-end">
                <div
                  class="w-7 h-7 rounded-full flex items-center justify-center text-white font-bold text-lg"
                  :class="egg.dot"
                >+</div>
              </div>
            </button>
          </div>
        </div>

        <!-- Sepetteki ürünler -->
        <div v-if="!loading && cart?.items?.length" class="px-5 mt-6">
          <p class="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3">Sepetiniz</p>
          <div class="space-y-2">
            <div
              v-for="item in cart.items"
              :key="item.id"
              class="bg-white rounded-xl px-4 py-3.5 flex items-center justify-between border border-stone-100 shadow-sm"
            >
              <div class="flex items-center gap-3">
                <span class="text-2xl">{{ emojiFor(item.feeding_type) }}</span>
                <div>
                  <div class="font-semibold text-stone-800 text-sm">{{ item.feeding_type_display }}</div>
                  <div class="text-xs text-stone-500">{{ item.capacity_display }} · {{ item.package_quantity }} paket</div>
                </div>
              </div>
              <button @click="removeItem(item.id)" class="text-stone-300 hover:text-red-500 transition-colors p-1">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="!loading" class="px-5 mt-4 text-center text-stone-400 text-sm py-6">
          Sepetiniz boş. Yukarıdan ürün ekleyin.
        </div>
      </template>

    </template>

    <!-- ════════════════════════════════════════════════════════════════════ -->
    <!--  SİPARİŞ TAKİP GÖRÜNÜMÜ                                             -->
    <!-- ════════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <div class="px-5 py-5 space-y-4">

        <!-- Skeleton -->
        <div v-if="historyLoading" class="space-y-4">
          <div
            v-for="i in 3" :key="i"
            class="bg-white rounded-2xl h-44 animate-pulse border border-stone-100"
          />
        </div>

        <!-- Boş durum -->
        <div
          v-else-if="submittedOrders.length === 0"
          class="bg-white rounded-2xl p-12 text-center border border-stone-100 shadow-sm mt-2"
        >
          <div class="text-5xl mb-4">📋</div>
          <p class="text-stone-600 font-bold">Henüz sipariş yok</p>
          <p class="text-stone-400 text-sm mt-1">Sepet sekmesinden ilk siparişinizi verin.</p>
          <button
            @click="activeView = 'cart'"
            class="mt-5 bg-orange-500 text-white px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-orange-600 transition-colors"
          >
            Sipariş Ver
          </button>
        </div>

        <!-- Sipariş kartları -->
        <div v-else class="space-y-4">
          <div
            v-for="order in submittedOrders"
            :key="order.id"
            class="bg-white rounded-2xl border overflow-hidden shadow-sm"
            :class="STATUS_META[order.status]?.border ?? 'border-stone-100'"
          >
            <!-- Başlık -->
            <div class="px-5 pt-4 pb-3 flex items-start justify-between">
              <div>
                <span class="font-mono text-xs text-stone-400 font-bold tracking-wider">{{ order.id }}</span>
                <div
                  class="inline-flex items-center gap-1.5 mt-1 px-2.5 py-1 rounded-full text-xs font-bold"
                  :class="[STATUS_META[order.status]?.bg, STATUS_META[order.status]?.color]"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-current" />
                  {{ STATUS_META[order.status]?.label ?? order.status }}
                </div>
              </div>
              <span class="text-xs text-stone-400 shrink-0 mt-1">{{ formatDate(order.created_at) }}</span>
            </div>

            <!-- Üretici -->
            <div v-if="order.assigned_producer_detail" class="px-5 pb-3 flex items-center gap-2 text-sm text-stone-600">
              <svg class="w-4 h-4 text-stone-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
              </svg>
              <span class="font-medium">{{ order.assigned_producer_detail.name }}</span>
            </div>

            <!-- Ürün özeti -->
            <div class="px-5 pb-4 flex flex-wrap gap-1.5">
              <span
                v-for="item in order.items"
                :key="item.id"
                class="bg-stone-50 border border-stone-200 rounded-lg px-2 py-1 text-xs text-stone-600"
              >
                {{ emojiFor(item.feeding_type) }}
                {{ item.feeding_type_display }} · {{ item.package_quantity }} adet
              </span>
            </div>

            <!-- Durum adım göstergesi -->
            <div v-if="order.status !== 'CANCELLED'" class="px-5 pb-5 pt-4 border-t border-stone-50">
              <div class="px-5 pb-5 pt-4 border-t border-stone-50">
                <div class="flex items-start">
                  <template v-for="(step, i) in STATUS_STEPS" :key="step.key">
                    <div class="flex flex-col items-center">
                      <div
                        class="w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-colors"
                        :class="stepIndex(order.status) >= i
                          ? 'bg-orange-500 text-white shadow-sm'
                          : 'bg-stone-100 text-stone-400'"
                      >
                        <!-- Tamamlanmış adım -->
                        <svg
                          v-if="stepIndex(order.status) > i"
                          class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                        >
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                        </svg>
                        <!-- Aktif / bekleyen adım -->
                        <span v-else class="text-xs font-bold">{{ i + 1 }}</span>
                      </div>
                      <span class="text-[10px] text-stone-500 mt-1.5 text-center w-14 leading-tight">
                        {{ step.label }}
                      </span>
                    </div>
                    <!-- Adımlar arası çizgi -->
                    <div
                      v-if="i < STATUS_STEPS.length - 1"
                      class="flex-1 h-0.5 mt-3.5 mx-1 transition-colors"
                      :class="stepIndex(order.status) > i ? 'bg-orange-400' : 'bg-stone-200'"
                    />
                  </template>
                </div>
              </div>
            </div>
            <!--  -->
            <div v-else class="px-5 pb-4 pt-3 border-t border-red-50 flex items-center gap-2 text-sm text-red-500">
              <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
              Bu sipariş iptal edildi.
            </div>

            <!-- İptal butonu: yalnızca ASSIGNED siparişlerde -->
            <div v-if="order.status === 'ASSIGNED'" class="px-5 pb-5">

              <!-- Onay sorusu -->
              <div
                v-if="cancelConfirming === order.id"
                class="bg-red-50 border border-red-200 rounded-xl p-4"
              >
                <p class="text-sm font-bold text-red-700 mb-3">
                  Siparişi iptal etmek istediğinizden emin misiniz?
                </p>
                <div class="flex gap-2">
                  <button
                    @click="cancelOrder(order.id)"
                    :disabled="cancelling === order.id"
                    class="flex-1 bg-red-500 text-white py-2.5 rounded-xl font-bold text-sm
                          hover:bg-red-600 transition-colors disabled:opacity-60"
                  >
                    {{ cancelling === order.id ? 'İptal ediliyor…' : 'Evet, İptal Et' }}
                  </button>
                  <button
                    @click="abortCancel"
                    class="flex-1 bg-white border border-stone-200 text-stone-600 py-2.5 rounded-xl font-bold text-sm hover:bg-stone-50 transition-colors"
                  >
                    Vazgeç
                  </button>
                </div>
              </div>

              <!-- İlk iptal butonu -->
              <button
                v-else
                @click="confirmCancel(order.id)"
                class="flex items-center gap-1.5 text-red-50 hover:text-red-50 text-sm font-bold transition-colors bg-red-500 p-2 rounded-xl border-2 hover:cursor-pointer hover:bg-red-700"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
                Siparişi İptal Et
              </button>

            </div>
            <!--  -->
          </div>
        </div>

        <div class="h-4" />
      </div>
    </template>

    <!-- ── ÜRÜN SEÇİCİ BOTTOM SHEET ──────────────────────────────────────── -->
    <Transition name="fade">
      <div v-if="selected" class="fixed inset-0 z-50">
        <div class="absolute inset-0 bg-black/50" @click="selected = null" />
        <div class="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl px-6 pt-5 pb-10 shadow-2xl max-w-lg mx-auto">

          <div class="w-10 h-1 bg-stone-200 rounded-full mx-auto mb-5" />
          <h3 class="font-black text-stone-800 text-lg mb-6">{{ selected.label }}</h3>

          <!-- Paket büyüklüğü -->
          <div class="mb-6">
            <p class="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3">Paket Büyüklüğü</p>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="cap in CAPACITIES"
                :key="cap.value"
                @click="selected.capacity = cap.value"
                class="py-3 rounded-xl font-bold text-sm border-2 transition-colors"
                :class="selected.capacity === cap.value
                  ? 'bg-orange-500 text-white border-orange-500'
                  : 'bg-white text-stone-700 border-stone-200 hover:border-orange-300'"
              >
                {{ cap.label }}
              </button>
            </div>
          </div>

          <!-- Adet stepper -->
          <div class="mb-7">
            <p class="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3">Paket Adedi</p>
            <div class="flex items-center gap-4">
              <button
                @click="selected.quantity = Math.max(1, selected.quantity - 1)"
                class="w-11 h-11 rounded-xl border-2 border-stone-200 flex items-center justify-center text-xl font-bold text-stone-600 hover:border-orange-300 transition-colors"
              >−</button>
              <span class="text-2xl font-black text-stone-800 w-12 text-center">{{ selected.quantity }}</span>
              <button
                @click="selected.quantity++"
                class="w-11 h-11 rounded-xl border-2 border-stone-200 flex items-center justify-center text-xl font-bold text-stone-600 hover:border-orange-300 transition-colors"
              >+</button>
              <span class="text-stone-400 text-sm">× {{ selected.capacity }} yumurta</span>
            </div>
          </div>

          <button
            @click="addToCart"
            :disabled="saving"
            class="w-full bg-orange-500 text-white py-4 rounded-2xl font-bold text-base hover:bg-orange-600 transition-colors disabled:opacity-60"
          >
            {{ saving ? 'Ekleniyor…' : `Sepete Ekle — ${selected.quantity} paket` }}
          </button>
        </div>
      </div>
    </Transition>

    <!-- ── ONAY ÇUBUĞU (yalnızca sepet tabında, dolu sepette) ─────────────── -->
    <Transition name="slide-up">
      <div
        v-if="activeView === 'cart' && cartItemCount > 0 && !checkoutResult"
        class="fixed bottom-0 left-0 right-0 bg-white border-t border-stone-100 px-5 py-4 shadow-xl"
      >
        <button
          @click="checkout"
          :disabled="checkingOut"
          class="w-full max-w-lg mx-auto block bg-orange-500 text-white py-4 rounded-2xl font-black text-base hover:bg-orange-600 transition-colors disabled:opacity-60"
        >
          {{ checkingOut ? 'Sipariş gönderiliyor…' : `Siparişi Onayla — ${cartItemCount} paket` }}
        </button>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.fade-enter-active,   .fade-leave-active   { transition: opacity 0.2s ease; }
.fade-enter-from,     .fade-leave-to       { opacity: 0; }

.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.25s ease; }
.slide-up-enter-from,   .slide-up-leave-to     { transform: translateY(100%); }
</style>