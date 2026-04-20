from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, Pallet, Package, BlockchainTransaction, InspectionCertificate

class CustomUserAdmin(UserAdmin):
    # Kullanici guncelleme
    fieldsets = UserAdmin.fieldsets + (
        ("Organization and Role", { "fields": ("role", "organization")}),
        ("Blockchain Info", {"fields": ("wallet_address",)}),
    )

    # Kullanici ekleme
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Organization, Role and Wallet', {
            'classes': ('wide',),
            'fields': ('role', 'organization', 'wallet_address'),
        }),
    )

    # Kullanıcılar tablosunda hangi kolonlar görünecegi
    list_display = ('username', 'email', 'role', 'organization', 'is_staff')
    list_filter = UserAdmin.list_filter + ('role', 'organization')

# Djangonun built in UserAdmin override edilerek yeni bir custom user admin tanimlaniyor.
admin.site.register(User, CustomUserAdmin)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
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
    search_fields = ('package_qr_id', 'pallet_master_qr_id')

@admin.register(BlockchainTransaction)
class BlockchainTransactionAdmin(admin.ModelAdmin):
    list_display = ('tx_hash', 'action_type', 'pallet', 'status', 'timestamp')
    list_filter = ('action_type', 'status')
    search_fields = ('tx_hash', 'pallet_master_qr_id')

@admin.register(InspectionCertificate)
class InspectionCertificateAdmin(admin.ModelAdmin):
    list_display = ('inspector', 'producer')