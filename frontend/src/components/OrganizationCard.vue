<script setup>
defineProps({
  organization: { type: Object, required: true },
})

defineEmits(['click'])
</script>

<template>
  <div
    @click="$emit('click', organization)"
    class="bg-white rounded-2xl border border-stone-100 shadow-sm
           hover:shadow-md hover:border-amber-200 transition-all cursor-pointer"
  >
    <div class="flex items-center gap-4 p-4">
      <div class="bg-amber-50 p-3 rounded-xl text-xl shrink-0">🏢</div> 
      <div class="min-w-0 flex-1">
        <!-- Organization Name -->
        <p class="font-black text-stone-800 text-sm truncate">
          {{ organization.name }}
        </p>
        <!-- Organization Code -->
        <p class="font-mono text-xs text-stone-500 mt-0.5 truncate">
          {{ organization.org_code }}
        </p>
        <!-- Type and Location -->
        <p class="text-[10px] text-stone-400 mt-1.5 uppercase tracking-wider truncate">
          {{ organization.organization_type }} <span class="px-1">•</span> {{ organization.location }}
        </p>
      </div>
    </div>

    <slot name="footer" />
  </div>
</template>