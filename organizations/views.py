from django.shortcuts import render
from rest_framework import viewsets
from .serializers import OrganizationSerializer, CertificateSerializer
from .models import Organization, InspectionCertificate
from users.permissions import IsVet
from blockchain.services import log_to_blockchain

class OrganizationViewSet(viewsets.ModelViewSet):
    # Kurumlari listeleyen ve olusturan API endpoint
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class CertificateViewSet(viewsets.ModelViewSet):
    queryset = InspectionCertificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [IsVet] # Sadece INSPECTOR kurumundaki VET'ler
    lookup_field = 'certificate_no'

    def perform_create(self, serializer):
        # 1. Sertifikayı veren kurumu ata ve veritabanına kaydet
        certificate = serializer.save(inspector=self.request.user.organization)
        
        # 2. Blokzincir Logu (CERT)
        payload = {
            "certificate_no": certificate.certificate_no,
            "producer_org_code": certificate.producer.org_code,
            "valid_until": str(certificate.valid_to)
        }
        # Palet bazlı değil, genel bir işlem olduğu için pallet=None gönderiyoruz
        log_to_blockchain(pallet=None, user=self.request.user, action_type='CERT', payload=payload)