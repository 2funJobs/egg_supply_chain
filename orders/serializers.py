from rest_framework import serializers
from .models import Pallet, Package
from organizations.serializers import OrganizationSerializer

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

class PackageSerializer(serializers.ModelSerializer):

    pallet = serializers.SlugRelatedField(
        slug_field='master_qr_id',
        queryset=Pallet.objects.all()
    )

    pallet_detail = PalletSerializer(source="pallet", read_only=True)
    class Meta:
        model = Package
        fields = ["package_qr_id", "pallet", "pallet_detail", "feeding_type", "laying_date", "expiry_date", "capacity"]
