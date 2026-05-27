from django.shortcuts import render
from rest_framework import viewsets
from .serializers import OrganizationSerializer, CertificateSerializer
from .models import Organization, InspectionCertificate
from users.permissions import IsVet, IsProducer, IsMarketOrLogisticsStaff
from blockchain.services import log_to_blockchain
from rest_framework.permissions import IsAdminUser

class OrganizationViewSet(viewsets.ModelViewSet):
    # Kurumlari listeleyen ve olusturan API endpoint
    serializer_class = OrganizationSerializer
    
    def get_permissions(self):
        """
        Organizasyonlar işletmelere kapalıdır. KAPALIDIR.
        """
        # 1. Yeni Organizasyon Tanımlama: Sadece Admin yapabilir
        if self.action == 'create':
            permission_classes = [IsAdminUser]
            
        # 2.Organizasyon güncellemesi admin veya denetleyici
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser | IsVet] # Sadece sistem admini (Django Admin)
            
        # 4. Görüntüleme (Listeleme/Detay) sadece admin ve denetleyici
        else:
            permission_classes = [IsAdminUser | IsVet | IsProducer]
            
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        # 1. Başlangıç: Tüm organizasyonları al
        queryset = Organization.objects.all()
        user = self.request.user
        token_payload = self.request.auth

        # --- AŞAMA 1: ROL BAZLI GÜVENLİK SINIRLANDIRMASI ---
        # Kimin hangi verileri görmeye hakkı var?
        
        # Eğer admin ise hiçbir sınırlandırma yapma (hepsini görebilir)
        if user.is_staff or user.is_superuser:
            pass 
            
        # Eğer Inspector ise sadece PRODUCER listesiyle sınırla
        elif token_payload and token_payload.get('role') == 'INSPECTOR':
            queryset = queryset.filter(organization_type='PRODUCER')

        elif token_payload and token_payload.get('role') == 'PRODUCER':
            queryset = queryset.filter(organization_type='MARKET')
            
        # Tanımsız bir rol ise veya yetkisizse hiçbir şey gösterme
        else:
            return queryset.none()


        # --- AŞAMA 2: FRONTEND FİLTRELEMESİ ---
        # Kullanıcı izin verilen veriler içinde özel bir arama/filtreleme yapmış mı?
        
        org_type = self.request.query_params.get('type', None)
        
        if org_type:
            # Örneğin; Inspector sadece PRODUCER görebildiği için ?type=INSPECTOR yollasa 
            # bile yukarıdaki sınırlandırma sayesinde veri sızmaz. Sadece boş döner.
            queryset = queryset.filter(organization_type=org_type)

        return queryset
    
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