from rest_framework import serializers
from .models import Organization, InspectionCertificate

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["org_code", "name", "organization_type", "location"]

class CertificateSerializer(serializers.ModelSerializer):
    # Okuma (GET) işlemleri için detaylı veriler
    inspector_detail = OrganizationSerializer(source="inspector", read_only=True)
    producer_detail = OrganizationSerializer(source="producer", read_only=True)
    inspector = serializers.SlugRelatedField(slug_field='org_code', read_only=True)

    # POST işleminde, Veterinerin çiftliği 'org_code' üzerinden bulmasını sağlanır.
    # Sadece 'PRODUCER' tipindeki kurumlara sertifika verilebilsin
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
