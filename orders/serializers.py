from rest_framework import serializers
from .models import Organization, Pallet, Package

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