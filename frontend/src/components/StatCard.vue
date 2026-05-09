<!-- StatCard.vue — Glass stat counter for inside gradient headers
     A minimal example of props with defaults.

     Usage:
       <StatCard label="Total Pallets" :value="stats.pallets" :loading="loading" />
       <StatCard label="Chain Active"  emoji="🔗" /> -->
<script setup>
defineProps({
  label:   { type: String, required: true },
  value:   { type: [String, Number], default: null },
  emoji:   { type: String, default: null },
  loading: { type: Boolean, default: false },
})
</script>

<template>
  <div class="bg-white/15 rounded-xl p-4 border border-white/20 text-center">
    <!-- Show emoji OR the numeric value (never both) -->
    <div class="text-white text-2xl font-black">
      <template v-if="emoji">{{ emoji }}</template>
      <template v-else>{{ loading ? '—' : value }}</template>
    </div>
    <div class="text-white/60 text-xs mt-1">{{ label }}</div>
  </div>
</template>
