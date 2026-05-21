<!-- src/views/LoginView.vue -->
<script setup>
import axios from 'axios'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref(null)

const handleLogin = async () => {
  errorMessage.value = null
  isLoading.value = true

  try {
    // Call the login action from Pinia
    await authStore.login(email.value, password.value)
    
    // Success! Redirect to the dashboard
    router.push('/')
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || "Invalid email or password."
  } finally {
    isLoading.value = false
  }
}

</script>

<template>
  <!-- Background is split: Top gradient, Bottom white/gray -->
  <div class="min-h-screen bg-gray-50 flex flex-col relative overflow-hidden">
    
    <!-- 
      2. TOP BRANDING SECTION 
      Matches the gradient and logo style from HomeView.vue and image_0.png
    -->
    <div class="bg-gradient-to-br from-[#2D60C7] to-[#1FB7E6] pt-20 pb-20 px-6 rounded-b-[40px] text-white flex flex-col items-center">
      <div class="flex items-center gap-3 mb-4">
        <!-- Reusable Egg Icon -->
        <svg class="w-12 h-12" fill="white" viewBox="0 0 20 20"><path d="M10 2a6 6 0 00-6 6c0 4 3 8 6 10 3-2 6-6 6-10a6 6 0 00-6-6z" /></svg>
        <h1 class="text-4xl font-bold tracking-tight">EggChain<span class="text-[#89D8F1]">♥</span></h1>
      </div>
      <p class="text-white/80 text-lg">Blockchain Egg Traceability System</p>
    </div>

    <!-- 
      3. FORM SECTION (The white card)
      This card is positioned to slightly overlap the gradient, like image_0.png
    -->
    <div class="flex-grow px-6 relative -top-12">
      <div class="bg-white p-8 rounded-3xl shadow-xl border border-gray-100 flex flex-col gap-6">
        
        <div class="text-center">
          <h2 class="text-3xl font-black text-gray-800 tracking-tight">Sign In</h2>
          <p class="text-gray-500 mt-2">Enter your credentials to access the ledger.</p>
        </div>

        <!-- Error message display -->
        <div v-if="errorMessage" class="bg-red-100 text-red-700 p-4 rounded-lg text-sm font-medium">
          {{ errorMessage }}
        </div>

        <!-- The Login Form -->
        <form @submit.prevent="handleLogin" class="space-y-5">
          
          <!-- Username Input -->
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-1.5 ml-1">Email Address</label>
            <div class="relative">
              <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
              <input
                v-model="email"
                type="email"
                placeholder="e.g., worker@greenfarm.com"
                required
                class="w-full pl-11 pr-4 py-3.5 bg-gray-100 border border-gray-200 rounded-xl focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors"
              />
            </div>
          </div>

          <!-- Password Input -->
          <div>
            <div class="flex justify-between items-center mb-1.5 ml-1">
              <label class="block text-sm font-bold text-gray-700">Password</label>
              <a href="#" class="text-xs font-semibold text-[#2D60C7] hover:text-blue-700">Forgot Password?</a>
            </div>
            <div class="relative">
              <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
              <input 
                v-model="password"
                type="password" 
                placeholder="••••••••" 
                required
                class="w-full pl-11 pr-4 py-3.5 bg-gray-100 border border-gray-200 rounded-xl focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors"
              />
            </div>
          </div>

          <!-- LOGIN BUTTON -->
          <button 
            type="submit"
            :disabled="isLoading"
            class="w-full py-4 px-6 mt-4 rounded-2xl font-bold transition-all duration-200 flex items-center justify-center gap-3 text-lg"
            :class="isLoading 
              ? 'bg-gray-400 text-gray-200 cursor-not-allowed' 
              : 'bg-[#3A3F58] text-white hover:bg-[#2A2E42] shadow-lg shadow-[#3A3F58]/30'"
          >
            <!-- Loading Spinner (v-if) -->
            <svg v-if="isLoading" class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            
            {{ isLoading ? 'Authenticating...' : 'Sign In' }}
          </button>

        </form>
      </div>

      <!-- Bottom footer helper -->
      <p class="text-center text-sm text-gray-500 mt-8 mb-4">
        Need assistance? <a href="#" class="font-bold text-[#2D60C7] hover:text-blue-700">Contact Network Admin</a>
      </p>
    </div>
  </div>
</template>