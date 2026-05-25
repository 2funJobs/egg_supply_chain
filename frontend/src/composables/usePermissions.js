// usePermissions.js
//
// IMPORTANT NOTE ON YOUR JWT STRUCTURE
// ─────────────────────────────────────
// Your backend puts the organization type ('PRODUCER', 'DISTRIBUTOR', etc.)
// into the JWT `role` claim — not a user-level role like STAFF/ADMIN.
//
// So auth.user.role might be:
//   'PRODUCER'    → user works at a producer farm
//   'DISTRIBUTOR' → user works at a distribution company
//   'MARKET'      → user works at a market
//   'INSPECTOR'   → user is a vet/inspector
//   'VET'         → specifically a veterinarian role (may also exist)
//   'ADMIN'       → platform administrator
//   'STAFF'       → generic staff (less common)
//
// We check BOTH the role claim AND the separately-fetched orgType so this
// works regardless of which one the backend actually populates.

import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

export function usePermissions() {
  const auth = useAuthStore()

  // storeToRefs() extracts reactive refs from a Pinia store while preserving
  // reactivity. We NO LONGER extract 'orgType' because we strictly rely on
  // the securely decoded JWT role.
  const { user } = storeToRefs(auth)

  const role = computed(() => user.value?.role ?? '')

  // Evaluate permissions strictly based on the JWT role claim.
  const isProducer = computed(() => role.value === 'PRODUCER')
  const isDistributor = computed(() => role.value === 'DISTRIBUTOR')
  const isMarket = computed(() => role.value === 'MARKET')
  const isInspector = computed(() => role.value === 'INSPECTOR')
  const isVet = computed(() => role.value === 'VET' || role.value === 'INSPECTOR')
  const isAdmin = computed(() => ['ADMIN', 'ORG_ADMIN'].includes(role.value))

  // ── Write permissions ────────────────────────────────────────────────────────

  // Producers create pallets (start of the supply chain)
  const canCreatePallet = computed(() => isProducer.value)

  // Distributors and markets can transfer pallets between themselves
  const canTransferPallet = computed(() =>
    isDistributor.value || isMarket.value
  )

  // Inspectors/vets issue health certificates for producer farms
  const canCreateCertificate = computed(() =>
    isInspector.value || isVet.value
  )

  return {
    // Boolean permission gates — use these directly in v-if
    canCreatePallet,
    canTransferPallet,
    canCreateCertificate,
    isAdmin,
    // Org-type shortcuts
    isProducer,
    isDistributor,
    isMarket,
    isInspector,
    isVet,
    // Raw values (useful for debugging or complex conditions)
    role,
  }
}