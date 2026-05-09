import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// Pinia must be installed before the router, because the router's
// navigation guards call useAuthStore() which needs Pinia to be ready.
app.use(createPinia())
app.use(router)
app.mount('#app')
