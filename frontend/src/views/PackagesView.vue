<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { packages as packagesApi, pallets as palletsApi } from '../api' 
import { usePermissions } from '../composables/usePermissions'
import { useAuthStore } from '../stores/auth'
import PackagesCard from '../components/PackageCard.vue'
import CreatePackageModal from '../components/CreatePackageModal.vue'

const router = useRouter()
const { canCreatePallet } = usePermissions()
const auth = useAuthStore()

const allPackages   = ref([])
const loading       = ref(true)
const error         = ref(null)
const activeFilter  = ref('ALL')
const searchQuery   = ref('')
const showModal     = ref(false)

const filters = [
  { label: 'All',           value: 'ALL' },
  { label: 'In Production', value: 'IN_PRODUCTION' },
  { label: 'In Transit',    value: 'IN_TRANSIT' },
  { label: 'At Market',     value: 'AT_MARKET' },
  { label: 'Faulty',        value: 'FAULTY' },
]

const filteredPackages = computed(() => {
  let result = allPackages.value
  
  if (activeFilter.value !== 'ALL') {
    result = result.filter((p) => p.pallet_detail?.status === activeFilter.value)
  }
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

// 1. Moved the fetching logic into its own function so we can control exactly WHEN it runs
const fetchData = async (userOrg) => {
  loading.value = true
  
  try {
    // 2. Changed parameters to 'producer' instead of 'producer__org_code'
    const [pkgRes, palletRes] = await Promise.all([
      packagesApi.list({ pallet__producer: userOrg }), 
      palletsApi.list({ producer: userOrg }) 
    ])

    let rawPackages = Array.isArray(pkgRes.data) ? pkgRes.data : (pkgRes.data.results ?? [])
    let rawPallets = Array.isArray(palletRes.data) ? palletRes.data : (palletRes.data.results ?? [])

    // 3. FRONTEND SAFETY FILTER (The Ultimate Backup)
    // If Django ignores our parameters and sends everything, Vue will delete the rest here.
    rawPallets = rawPallets.filter(pallet => pallet.producer === userOrg)

    const palletsDict = {}
    rawPallets.forEach(pallet => {
      palletsDict[pallet.master_qr_id] = pallet 
    })

    // 4. Map the packages, but ONLY keep packages that successfully found a matching pallet
    const mappedPackages = rawPackages.map(pkg => ({
      ...pkg,
      pallet_detail: palletsDict[pkg.pallet] || null 
    }))
    
    // Filter out any packages where the pallet wasn't found (meaning it belonged to another producer)
    allPackages.value = mappedPackages.filter(pkg => pkg.pallet_detail !== null)

  } catch (err) {
    console.error(err)
    error.value = 'Failed to load data. Is the Django server running?'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // 5. Check if auth exists immediately
  if (auth.user?.orgCode) {
    fetchData(auth.user.orgCode)
  } else {
    // If it doesn't exist yet, wait for the auth store to finish loading, then fetch!
    const unwatch = watch(() => auth.user?.orgCode, (newOrgCode) => {
      if (newOrgCode) {
        fetchData(newOrgCode)
        unwatch() // Stop watching once we have the data
      }
    })
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
        >
          <!-- FIXED: Replaced "package.package_qr_id" with "_package.package_qr_id" above -->

          <template #footer>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 pb-4 text-xs text-stone-500">
              <span class="font-bold flex items-center gap-1.5">
                İlgili Palet: <p class="text-s font-medium text-stone-800"> {{ _package.pallet }}</p>
              </span>
              <span class="font-bold flex items-center gap-1.5">
                Yumurtlama Tarihi: <p class="text-s font-medium text-stone-800"> {{ _package.laying_date }}</p>
              </span>
              <span class="font-bold flex items-center gap-1.5">
                <button 
                  @click="router.push(`/packages/${_package.package_qr_id}`)" 
                  class="text-s font-medium text-stone-200 bg-amber-600 p-2 md:py-3 md:px-4 rounded-full md:rounded-xl
                  shadow-lg flex items-center justify-center gap-2
                  hover:bg-amber-700 transition-colors cursor-pointer"
                  >
                Detay
                </button>
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