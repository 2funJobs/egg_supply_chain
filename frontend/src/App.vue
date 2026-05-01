<script setup>
import { ref, onMounted } from 'vue'

// --- DEVLET (STATE) YÖNETİMİ ---
const isAuthenticated = ref(false)
const userRole = ref('')
const orgCode = ref('')

// Login Formu Değişkenleri
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

// --- SAYFA YÜKLENDİĞİNDE ÇALIŞACAK KONTROL ---
onMounted(() => {
  const token = localStorage.getItem('access_token')
  if (token) {
    // 1. Token varsa kullanıcı giriş yapmış demektir
    isAuthenticated.value = true
    
    // 2. Token'ın içindeki Payload'u (Şifresiz kısmı) okuyarak kim olduğunu anlıyoruz
    try {
      const payloadBase64 = token.split('.')[1]
      const decodedJson = atob(payloadBase64)
      const payload = JSON.parse(decodedJson)
      
      // Django'da token'ın içine mühürlediğimiz o özel veriler:
      userRole.value = payload.role || 'Bilinmeyen Rol'
      orgCode.value = payload.org_code || 'Bilinmeyen Kurum'
    } catch (error) {
      console.error("Token çözümlenemedi:", error)
      handleLogout() // Token bozuksa güvenli çıkış yap
    }
  }
})

// --- GİRİŞ İŞLEMİ ---
const handleLogin = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch('http://localhost:8000/api/v1/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value, password: password.value })
    })

    const data = await response.json()

    if (!response.ok) throw new Error(data.detail || 'E-posta veya şifre hatalı.')

    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    
    // Giriş başarılıysa sayfayı manuel olarak "Yenile" (Böylece onMounted tekrar çalışır ve token'ı okur)
    window.location.reload()

  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

// --- ÇIKIŞ İŞLEMİ ---
const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  isAuthenticated.value = false
  window.location.reload()
}
</script>

<template>
  <div>
    <!-- EĞER GİRİŞ YAPILDIYSA: DASHBOARD EKRANINI GÖSTER -->
    <div v-if="isAuthenticated" class="min-h-screen bg-slate-100 font-sans text-slate-800">
      
      <!-- Üst Menü (Navbar) -->
      <nav class="bg-white shadow-sm border-b border-slate-200 px-6 py-4 flex justify-between items-center">
        <div class="flex items-center space-x-3">
          <div class="h-10 w-10 bg-emerald-600 rounded-lg flex items-center justify-center text-white text-xl">
            📦
          </div>
          <div>
            <h1 class="font-bold text-lg leading-tight">Hyperledger Tedarik Ağı</h1>
            <p class="text-xs text-slate-500 font-medium tracking-wide">
              Rol: <span class="text-emerald-600">{{ userRole }}</span> | Kurum: {{ orgCode }}
            </p>
          </div>
        </div>
        
        <button @click="handleLogout" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium rounded-md transition-colors text-sm">
          Çıkış Yap
        </button>
      </nav>

      <!-- Ana İçerik Alanı -->
      <main class="max-w-7xl mx-auto px-6 py-8">
        
        <div class="mb-8">
          <h2 class="text-2xl font-bold text-slate-800">Operasyon Merkezi</h2>
          <p class="text-slate-500 mt-1">Hoş geldiniz. Kurumunuza ait yetkilerle aşağıdaki işlemleri gerçekleştirebilirsiniz.</p>
        </div>

        <!-- Rol Bazlı Kartlar (Sadece PRODUCER - Çiftçi isen görünür) -->
        <div v-if="userRole === 'PRODUCER'" class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Palet Üretim Kartı -->
          <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 hover:shadow-md transition-shadow">
            <div class="h-12 w-12 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center text-2xl mb-4">
              🥚
            </div>
            <h3 class="text-lg font-semibold mb-2">Yeni Palet Üret</h3>
            <p class="text-sm text-slate-500 mb-4">IoT cihazından gelen verileri simüle ederek blokzincire yeni bir yumurta paleti kaydedin.</p>
            <button class="w-full bg-emerald-600 text-white font-medium py-2 rounded-md hover:bg-emerald-700 transition-colors">
              Üretimi Başlat
            </button>
          </div>
        </div>
        
        <!-- Diğer roller için mesaj -->
        <div v-else class="bg-blue-50 border border-blue-200 text-blue-700 px-6 py-4 rounded-lg">
          <p>Şu an <strong>{{ userRole }}</strong> rolündesiniz. Sadece "PRODUCER" (Çiftlik) rolündeki hesaplar palet üretebilir.</p>
        </div>

      </main>
    </div>

    <!-- EĞER GİRİŞ YAPILMADIYSA: (AZ ÖNCE YAZDIĞIMIZ) LOGIN EKRANINI GÖSTER -->
    <div v-else class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
       <!-- ... (Buraya az önce yazdığımız Login formunun <div class="sm:mx-auto..."> kısmından itibaren olan içeriği yapıştır) ... -->
        <div class="sm:mx-auto sm:w-full sm:max-w-md text-center">
            <div class="mx-auto h-12 w-12 bg-emerald-600 text-white rounded-xl flex items-center justify-center text-2xl font-bold shadow-md">📦</div>
            <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">Tedarik Zinciri Ağı</h2>
        </div>

        <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
            <div class="bg-white py-8 px-4 shadow-xl sm:rounded-2xl sm:px-10 border border-gray-100">
                <form class="space-y-6" @submit.prevent="handleLogin">
                    <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 p-4 mb-4 rounded-md">
                        <p class="text-sm text-red-700">{{ errorMessage }}</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Kurumsal E-Posta</label>
                        <input v-model="email" type="email" required class="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm" />
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Şifre</label>
                        <input v-model="password" type="password" required class="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm" />
                    </div>
                    <button type="submit" :disabled="isLoading" class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500">
                        <span v-if="isLoading">Giriş Yapılıyor...</span>
                        <span v-else>Sisteme Giriş Yap</span>
                    </button>
                </form>
            </div>
        </div>
    </div>

  </div>
</template>