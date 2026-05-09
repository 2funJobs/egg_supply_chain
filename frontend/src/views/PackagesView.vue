<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { packages as packagesApi } from '../api' // Removed palletsApi as it's unused here
import { usePermissions } from '../composables/usePermissions'
import PackagesCard from '../components/PackageCard.vue'
import CreatePackageModal from '../components/CreatePackageModal.vue'

const router = useRouter()
const { canCreatePallet } = usePermissions()

const allPackages   = ref([])
const loading       = ref(true)
const error         = ref(null)
const activeFilter  = ref('ALL')
const searchQuery   = ref('')
const showModal     = ref(false)

// 1. Add the exact same filter tabs you use for Pallets
const filters = [
  { label: 'All',           value: 'ALL' },
  { label: 'In Production', value: 'IN_PRODUCTION' },
  { label: 'In Transit',    value: 'IN_TRANSIT' },
  { label: 'At Market',     value: 'AT_MARKET' },
  { label: 'Faulty',        value: 'FAULTY' },
]

// 2. Update the computed property to look inside pallet_detail
const filteredPackages = computed(() => {
  let result = allPackages.value
  
  // Apply status filter (reading from the Master Pallet's status!)
  if (activeFilter.value !== 'ALL') {
    result = result.filter((p) => p.pallet_detail?.status === activeFilter.value)
  }
  
  // Apply search text filter
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter((p) => p.package_qr_id?.toLowerCase().includes(query))
  }
  
  return result
})

const formatDate = (str) => {
  if (!str) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  }).format(new Date(str))
}

const onPackageCreated = (newPackage) => {
  allPackages.value.unshift(newPackage)
  showModal.value = false
  router.push(`/packages/${newPackage.package_qr_id}`)
}

onMounted(async () => {
  try {
    const res = await packagesApi.list()
    // FIXED: Assigned to allPackages, not allPallets
    allPackages.value = Array.isArray(res.data) ? res.data : (res.data.results ?? [])

    console.log("PACKAGE DATA:", allPackages.value[0])

} catch {
    error.value = 'Failed to load packages. Is the Django server running?'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="w-full max-w-4xl mx-auto">

    <!-- HEADER -->
    <div class="bg-gradient-to-br from-stone-700 to-stone-900 pt-10 pb-8 px-6 rounded-b-[32px] shadow-lg">
      <div class="flex justify-between items-start mb-5">
        <div>
          <h1 class="text-2xl font-black text-white">Packages</h1>
          <p class="text-stone-400 text-sm mt-1">
            {{ loading ? 'Loading…' : `${allPackages.length} packages total` }}
          </p>
        </div>
        <button
          v-if="canCreatePallet"
          @click="showModal = true"
          class="bg-amber-500 text-white px-4 py-2.5 rounded-xl font-bold text-sm
                 hover:bg-amber-600 transition-colors flex items-center gap-2 shrink-0"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          New Package
        </button>
      </div>

      <div class="relative">
        <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400"
             fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by Package QR ID…"
          class="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl
                 text-white placeholder-stone-500 focus:outline-none focus:border-amber-400
                 focus:ring-1 focus:ring-amber-400 transition-colors text-sm"
        />
      </div>
    </div>

    <!-- FILTER TABS -->
    <div class="px-5 mt-5 flex gap-2 overflow-x-auto pb-1">
      <button
        v-for="filter in filters"
        :key="filter.value"
        @click="activeFilter = filter.value"
        class="shrink-0 px-4 py-2 rounded-full text-sm font-bold transition-colors"
        :class="activeFilter === filter.value
          ? 'bg-amber-600 text-white shadow-sm'
          : 'bg-white text-stone-600 border border-stone-200 hover:border-amber-300'"
      >
        {{ filter.label }}
      </button>
    </div>

    <!-- PACKAGE LIST -->
    <div class="px-5 py-5 space-y-3">

      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
        ⚠️ {{ error }}
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 5" :key="i"
             class="bg-white rounded-2xl h-24 animate-pulse border border-stone-100"></div>
      </div>

      <div v-else-if="filteredPackages.length === 0"
           class="bg-white rounded-2xl p-12 text-center border border-stone-100 shadow-sm">
        <div class="text-5xl mb-4">📭</div>
        <p class="text-stone-600 font-bold">No packages found</p>
        <p class="text-stone-400 text-sm mt-1">
          {{ searchQuery ? 'Try a different search term' : 'No packages match this filter' }}
        </p>
      </div>

      <div v-else class="space-y-3">
        <PackagesCard
          v-for="_package in filteredPackages"
          :key="_package.package_qr_id"
          :package="_package"
          @click="router.push(`/packages/${_package.package_qr_id}`)" 
        >
          <!-- FIXED: Replaced "package.package_qr_id" with "_package.package_qr_id" above -->

          <template #footer>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 pb-4 text-xs text-stone-500">
              <span class="flex items-center gap-1.5">
                <!-- FIXED: Changed "_package,pallet" to "_package.pallet?." to prevent crashes if pallet is null -->
                <span class="w-2 h-2 rounded-full"
                      :class="_package.pallet_detail?.vet_approval ? 'bg-emerald-400' : 'bg-stone-300'"></span>
                Vet {{ _package.pallet_detail?.vet_approval ? 'Approved' : 'Pending' }}
              </span>
              <span class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full"
                      :class="_package.pallet_detail?.is_quality_maintained ? 'bg-emerald-400' : 'bg-stone-300'"></span>
                Quality {{ _package.pallet_detail?.is_quality_maintained ? 'OK' : 'Unknown' }}
              </span>
              <span v-if="_package.pallet_detail?.created_at" class="ml-auto text-stone-400">
                {{ formatDate(_package.pallet_detail.created_at) }}
              </span>
            </div>
          </template>
        </PackagesCard>
      </div>

      <div class="h-4"></div>
    </div>

    <CreatePackageModal
      v-if="showModal"
      @created="onPackageCreated"
      @close="showModal = false"
    />

  </div>
</template>