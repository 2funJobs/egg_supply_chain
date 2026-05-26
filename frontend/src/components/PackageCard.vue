<script setup>
import StatusBadge from './StatusBadge.vue'

defineProps({
  package: { type: Object, required: true },
})

// defineEmits() declares which custom events this component can fire.
// The parent listens with @click="handler". This keeps the child dumb
// (it doesn't know what the parent will do — it just announces "I was clicked").
defineEmits(['click'])
</script>

<template>
  <div
    @click="$emit('click', package)"
    class="bg-white rounded-2xl border border-stone-100 shadow-sm
           hover:shadow-md hover:border-amber-200 transition-all cursor-pointer"
  >
    <!-- Main row: icon + QR ID + status badge -->
    <div class="flex items-center gap-4 p-4">
      <div class="bg-amber-50 p-3 rounded-xl text-xl shrink-0">📦</div>
      <div class="min-w-0 flex-1">
        <p class="font-black text-stone-800 font-mono text-sm truncate">
          {{ package.package_qr_id }}
        </p>
        <!-- <p class="text-xs text-stone-500 mt-0.5 truncate">
          {{ package.pallet.producer }}
        </p> -->
      </div>
      <!-- <StatusBadge :status="package.pallet_detail.status" variant="package" class="shrink-0" /> -->
    </div>

    <!-- Named slot: the parent can inject a footer here.
         If no <template #footer> is provided, this renders nothing.
         <slot name="footer" /> is the placeholder that gets replaced. -->
    <slot name="footer" />
  </div>
</template>