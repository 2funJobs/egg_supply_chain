from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, Pallet, Package, BlockchainTransaction

admin.site.register(User, UserAdmin)

@admin.register(Organization)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization_type', 'location')
    list_filter = ('organization_type',)
    search_fields = ('name',)

@admin.register(Pallet)
class PalletAdmin(admin.ModelAdmin):
    list_display = ('master_qr_id', 'producer', 'current_holder', 'status', 'vet_approval')
    list_filter = ('status', 'vet_approval', 'is_quality_maintained')
    search_fields = ('master_qr_id',)

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('package_qr_id', 'pallet', 'laying_date', 'expiry_date')
    search_fields = ('package_qr_id', 'pallet__master_qr_id')

@admin.register(BlockchainTransaction)
class BlockchainTransactionAdmin(admin.ModelAdmin):
    list_display = ('tx_hash', 'action_type', 'pallet', 'status', 'timestamp')
    list_filter = ('action_type', 'status')
    search_fields = ('tx_hash', 'pallet__master_qr_id')