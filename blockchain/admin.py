from django.contrib import admin
from .models import BlockchainTransaction

@admin.register(BlockchainTransaction)
class BlockchainTransactionAdmin(admin.ModelAdmin):
    list_display = ('tx_hash', 'action_type', 'pallet', 'status', 'timestamp')
    list_filter = ('action_type', 'status')
    search_fields = ('tx_hash', 'pallet_master_qr_id')
