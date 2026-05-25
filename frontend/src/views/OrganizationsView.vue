<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import OrganizationCard from '@/components/OrganizationCard.vue'

// 1. Kendi oluşturduğun Auth Store'u içeri al (Yol projene göre değişebilir)
import { useAuthStore } from '@/stores/auth' 

// 2. Ham axios yerine store'da kullandığın yapılandırılmış 'api' instance'ını import et
// (Eğer api.js plugin olarak dışarıda tanımlıysa oradan çek, değilse doğrudan store'dan fetch edebilirsin)
import api from '@/api' // Kendi axios instance dosyanın yolunu buraya yaz

const router = useRouter()
const authStore = useAuthStore() // Store'u başlat

const organizations = ref([])
const isModalOpen = ref(false)
const selectedProducer = ref(null)

const certForm = ref({
  certificate_no: '',
  valid_from: '',
  valid_to: ''
})

onMounted(async () => {
  try {
    // 3. Ham axios yerine 'api' kullan. Token otomatik olarak gidecektir.
    const response = await api.get('/organizations/') 
    organizations.value = response.data
  } catch (error) {
    console.error("Organizasyonlar yüklenirken hata oluştu:", error)
  }
})

const openCertModal = (org) => {
  selectedProducer.value = org
  const today = new Date()
  const sixMonthsLater = new Date(today)
  sixMonthsLater.setMonth(today.getMonth() + 6)
  
  certForm.value.valid_from = today.toISOString().slice(0, 16)
  certForm.value.valid_to = sixMonthsLater.toISOString().slice(0, 16)
  certForm.value.certificate_no = `CER_${Math.floor(Math.random() * 10000)}`
  
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
  selectedProducer.value = null
}

const submitCertificate = async () => {
  try {
    const payload = {
      certificate_no: certForm.value.certificate_no,
      producer: selectedProducer.value.org_code,
      valid_from: new Date(certForm.value.valid_from).toISOString(),
      valid_to: new Date(certForm.value.valid_to).toISOString()
    }

    // POST işleminde de aynı şekilde 'api' kullanıyoruz
    await api.post('/certificates/', payload)
    
    alert(`${selectedProducer.value.name} için sertifika başarıyla oluşturuldu!`)
    closeModal()
  } catch (error) {
    console.error("Sertifika oluşturulurken hata:", error)
    alert("Bir hata oluştu, lütfen bilgileri kontrol edin.")
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto p-6">
    <div class="mb-8">
      <h1 class="text-3xl font-black text-stone-800">Organizasyonlar</h1>
      <p class="text-stone-500 mt-2">Sistemde kayıtlı tüm denetçi ve üretici organizasyonlar.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <OrganizationCard
        v-for="org in organizations"
        :key="org.org_code"
        :organization="org"
        @click="router.push(`/organizations/${org.org_code}`)"
      >
        <template #footer>
          <div class="px-4 pb-4 mt-2 border-t border-stone-50 pt-3">
            <button 
              @click.stop="openCertModal(org)"
              class="w-full bg-amber-100 hover:bg-amber-200 text-amber-800 font-bold text-sm py-2 rounded-lg transition-colors"
            >
              + Sertifika Ver
            </button>
          </div>
        </template>
      </OrganizationCard>
    </div>

    <div v-if="isModalOpen" class="fixed inset-0 bg-stone-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl w-full max-w-md shadow-xl overflow-hidden">
        <div class="bg-amber-50 p-4 border-b border-amber-100">
          <h3 class="font-black text-stone-800">Yeni Sertifika Düzenle</h3>
          <p class="text-xs text-stone-500 mt-1">
            Alıcı: <span class="font-bold text-amber-700">{{ selectedProducer?.name }}</span>
          </p>
        </div>

        <form @submit.prevent="submitCertificate" class="p-5 space-y-4">
          <div>
            <label class="block text-xs font-bold text-stone-600 mb-1 uppercase tracking-wide">Sertifika Numarası</label>
            <input 
              v-model="certForm.certificate_no" 
              type="text" 
              required
              placeholder="Örn: CER_101"
              class="w-full border border-stone-200 rounded-lg px-3 py-2 text-stone-800 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all"
            >
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-stone-600 mb-1 uppercase tracking-wide">Geçerlilik (Başlangıç)</label>
              <input 
                v-model="certForm.valid_from" 
                type="datetime-local" 
                required
                class="w-full border border-stone-200 rounded-lg px-3 py-2 text-sm text-stone-800 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all"
              >
            </div>
            <div>
              <label class="block text-xs font-bold text-stone-600 mb-1 uppercase tracking-wide">Geçerlilik (Bitiş)</label>
              <input 
                v-model="certForm.valid_to" 
                type="datetime-local" 
                required
                class="w-full border border-stone-200 rounded-lg px-3 py-2 text-sm text-stone-800 focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all"
              >
            </div>
          </div>

          <div class="pt-4 flex gap-3">
            <button 
              type="button" 
              @click="closeModal"
              class="flex-1 px-4 py-2 text-sm font-bold text-stone-500 hover:bg-stone-50 rounded-lg transition-colors"
            >
              İptal
            </button>
            <button 
              type="submit"
              class="flex-1 px-4 py-2 bg-stone-800 hover:bg-stone-900 text-white text-sm font-bold rounded-lg transition-all shadow-sm"
            >
              Onayla ve Ver
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>