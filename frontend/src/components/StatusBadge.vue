<!-- StatusBadge.vue — Reusable colored pill badge
     Props are the API of a component: they define what data it needs from the parent.
     The parent passes data DOWN via props; the child never modifies them (one-way flow).

     Usage:
       <StatusBadge status="IN_TRANSIT" variant="pallet" />
       <StatusBadge status="SUCCESS"    variant="tx" />
       <StatusBadge status="PROD"       variant="action" /> -->
<script setup>
// defineProps() declares which props this component accepts.
// You can add type, required, and default constraints.
const props = defineProps({
  status:  { type: String, required: true },
  variant: {
    type: String,
    default: 'pallet',
    // 'pallet' → IN_PRODUCTION | IN_TRANSIT | AT_MARKET | FAULTY
    // 'tx'     → SUCCESS | FAILED | PENDING
    // 'action' → PROD | TRAN | QUAL | RECV | CERT
  },
})

// Each map converts a raw backend value into a display label + Tailwind classes.
// Keeping this as a plain object (not computed) is fine — maps don't change at runtime.
const maps = {
  pallet: {
    IN_PRODUCTION: { label: 'In Production', cls: 'bg-blue-100 text-blue-700' },
    IN_TRANSIT:    { label: 'In Transit',    cls: 'bg-amber-100 text-amber-700' },
    AT_MARKET:     { label: 'At Market',     cls: 'bg-emerald-100 text-emerald-700' },
    FAULTY:        { label: 'Faulty',        cls: 'bg-red-100 text-red-700' },
  },
  tx: {
    SUCCESS: { label: 'Success', cls: 'bg-emerald-100 text-emerald-700' },
    FAILED:  { label: 'Failed',  cls: 'bg-red-100 text-red-700' },
    PENDING: { label: 'Pending', cls: 'bg-amber-100 text-amber-700' },
  },
  action: {
    PROD: { label: 'Production',   cls: 'bg-blue-100 text-blue-700' },
    TRAN: { label: 'Transfer',     cls: 'bg-amber-100 text-amber-700' },
    QUAL: { label: 'Quality',      cls: 'bg-emerald-100 text-emerald-700' },
    RECV: { label: 'Received',     cls: 'bg-purple-100 text-purple-700' },
    CERT: { label: 'Certificate',  cls: 'bg-pink-100 text-pink-700' },
  },
  package: {
    IN_PRODUCTION: { label: 'In Production', cls: 'bg-blue-100 text-blue-700' },
    IN_TRANSIT:    { label: 'In Transit',    cls: 'bg-amber-100 text-amber-700' },
    AT_MARKET:     { label: 'At Market',     cls: 'bg-emerald-100 text-emerald-700' },
    FAULTY:        { label: 'Faulty',        cls: 'bg-red-100 text-red-700' },
  }
}

// Optional chaining (?.) safely handles unknown variants or statuses.
const config = maps[props.variant]?.[props.status]
</script>

<template>
  <span
    class="inline-block text-xs font-bold px-2.5 py-1 rounded-full whitespace-nowrap"
    :class="config?.cls || 'bg-stone-100 text-stone-600'"
  >
    {{ config?.label || status }}
  </span>
</template>
