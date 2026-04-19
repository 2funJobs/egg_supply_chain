from rest_framework import serializers
from .models import Organization, Pallet, Package, BlockchainTransaction

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "organization_type", "location"]

class PalletSerializer(serializers.ModelSerializer):
    producer_detail = OrganizationSerializer(source="producer", read_only=True)
    current_holder_detail = OrganizationSerializer(source="current_holder", read_only=True)

    class Meta:
        model = Pallet
        fields = [
            'master_qr_id', 'producer', 'producer_detail', 
            'current_holder', 'current_holder_detail', 
            'status', 'vet_approval', 'is_quality_maintained', 
            'departure_date', 'created_at'
        ]

# Blockchain loglarini gostermek icin kullanilan serializer tanimidir.
class BlockchainTransactionSerializer(serializers.ModelSerializer):
    action_type_display = serializers.CharField(source="get_action_type_display", read_only=True)

    class Meta:
        model = BlockchainTransaction
        fields = ["action_type", "action_type_display", "tx_hash", "status", "payload", "timestamp"]

class PackageSerializer(serializers.ModelSerializer):
    pallet_detail = PalletSerializer(source="pallet", read_only=True)
    class Meta:
        model = Package
        fields = ["package_qr_id", "pallet_detail", "feeding_type", "laying_date", "expiry_date"]
    