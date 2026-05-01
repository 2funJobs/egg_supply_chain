from rest_framework import serializers
from .models import Organization, Pallet, Package, BlockchainTransaction, InspectionCertificate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # JWT Payload'una ekstra verilerimizi (Kurum/Rol) ekliyoruz
        if hasattr(user, 'organization') and user.organization:
            token['org_code'] = user.organization.org_code
            token['org_name'] = user.organization.name
            token['role'] = user.organization.organization_type

        return token

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["org_code", "name", "organization_type", "location"]

class PalletSerializer(serializers.ModelSerializer):
    producer_detail = OrganizationSerializer(source="producer", read_only=True)
    current_holder_detail = OrganizationSerializer(source="current_holder", read_only=True)

    producer = serializers.SlugRelatedField(slug_field='org_code', read_only=True)
    current_holder = serializers.SlugRelatedField(slug_field='org_code', read_only=True)

    class Meta:
        model = Pallet
        fields = [
            'master_qr_id', 'producer', 'producer_detail', 
            'current_holder', 'current_holder_detail', 
            'status', 'vet_approval', 'is_quality_maintained', 
            'departure_date', 'created_at'
        ]
        
        # Bu alanları read_only yaparsak, DRF artık POST isteğinde bu verileri kullanıcıdan beklemez.
        read_only_fields = ['producer', 'current_holder', 'status', 'vet_approval', 'is_quality_maintained']

# Blockchain loglarini gostermek icin kullanilan serializer tanimidir.

class BlockchainTransactionSerializer(serializers.ModelSerializer):
    # 1. Okunabilirlik: Enum kodlarını (PROD, TRAN) açıklamalara dönüştürür
    action_type_display = serializers.CharField(source="get_action_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # 2. İlişkisel Veriler: ID yerine Public ID'leri (Slug) döndürür
    # source kullanarak ilişkili tablodaki spesifik alana ulaşıyoruz
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

class PackageSerializer(serializers.ModelSerializer):

    pallet = serializers.SlugRelatedField(
        slug_field='master_qr_id',
        queryset=Pallet.objects.all()
    )

    pallet_detail = PalletSerializer(source="pallet", read_only=True)
    class Meta:
        model = Package
        fields = ["package_qr_id", "pallet", "pallet_detail", "feeding_type", "laying_date", "expiry_date", "capacity"]
    

class CertificateSerializer(serializers.ModelSerializer):
    # Okuma (GET) işlemleri için detaylı veriler
    inspector_detail = OrganizationSerializer(source="inspector", read_only=True)
    producer_detail = OrganizationSerializer(source="producer", read_only=True)
    inspector = serializers.SlugRelatedField(slug_field='org_code', read_only=True)

    # POST işleminde, Veterinerin çiftliği 'org_code' üzerinden bulmasını sağlıyoruz.
    # Güvenlik: Sadece 'PRODUCER' tipindeki kurumlara sertifika verilebilsin!
    producer = serializers.SlugRelatedField(
        slug_field='org_code',
        queryset=Organization.objects.filter(organization_type='PRODUCER')
    )

    class Meta:
        model = InspectionCertificate
        fields = [
            'certificate_no', 
            'inspector', 
            'inspector_detail', 
            'producer', 
            'producer_detail', 
            'valid_from', 
            'valid_to', 
            'is_active'
        ]
        
        # GÜVENLİK DUVARI:
        # 'inspector' -> views.py içindeki perform_create metodunda otomatik atanacak.
        # 'is_active' -> Varsayılan olarak True gelir, dışarıdan manipüle edilmesini engelliyoruz.
        read_only_fields = ['inspector', 'is_active']

