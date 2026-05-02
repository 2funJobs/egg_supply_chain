from rest_framework import serializers
from .models import BlockchainTransaction

class BlockchainTransactionSerializer(serializers.ModelSerializer):
    # 1. Enum kodlarını (PROD, TRAN) açıklamalara dönüştürür
    action_type_display = serializers.CharField(source="get_action_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # 2. İlişkisel Veriler: ID yerine Public ID'leri (Slug) döndürür
    # source kullanarak ilişkili tablodaki spesifik alana ulaşır
    pallet_qr = serializers.CharField(source="pallet.master_qr_id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_code = serializers.CharField(source="organization.org_code", read_only=True)
    
    # İşlemi yapan kullanıcının cüzdan adresi (Blokzincir doğrulaması için kritik)
    user_wallet = serializers.CharField(source="user.wallet_address", read_only=True)

    class Meta:
        model = BlockchainTransaction
        # ViewSet'teki filterset_fields ve lookup_field ile uyumlu alanları seçiyoruz
        fields = [
            "tx_hash", 
            "block_number",
            "pallet_qr", 
            "organization_name", 
            "organization_code",
            "user_wallet",
            "action_type", 
            "action_type_display", 
            "status", 
            "status_display",
            "payload", 
            "timestamp"
        ]
        # Log kayıtları değiştirilemez olduğu için tüm alanları salt okunur yapmak güvenlidir
        read_only_fields = fields