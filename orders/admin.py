from django.contrib import admin
from .models import Pallet, Package
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(Pallet)
class PalletAdmin(admin.ModelAdmin):
    list_display = ('master_qr_id', 'producer', 'current_holder', 'status', 'vet_approval')
    list_filter = ('status', 'vet_approval', 'is_quality_maintained')
    search_fields = ('master_qr_id',)

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('package_qr_id', 'pallet', 'laying_date', 'expiry_date')
    search_fields = ('package_qr_id', 'pallet_master_qr_id')
