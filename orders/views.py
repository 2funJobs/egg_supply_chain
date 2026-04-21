from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework import permissions
from .permissions import IsProducer, IsVet, IsMarketOrLogisticsStaff
from .models import Organization, Pallet, Package, InspectionCertificate, BlockchainTransaction
from .serializers import OrganizationSerializer, PalletSerializer, BlockchainTransactionSerializer, PackageSerializer, CertificateSerializer
from .services import log_to_blockchain

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

class PalletViewSet(viewsets.ModelViewSet):
    # Paletleri listeleyen, yeni palet olusturan API endpoint
    queryset = Pallet.objects.all().order_by("-created_at")
    serializer_class = PalletSerializer
    # Paletlere id(QR) degeri saglayacak atama
    lookup_field = "master_qr_id"
    
    def get_permissions(self):
        """
        PALETLER B2B (İŞLETMELER ARASI) BİRİMLERDİR. TÜKETİCİYE KAPALIDIR.
        """
        # 1. Yeni Palet Üretimi: Sadece Çiftçi (Üretici) yapabilir
        if self.action == 'create':
            permission_classes = [IsProducer]
            
        # 2. Transfer ve IoT Verisi: Sadece Lojistik ve Market personeli yapabilir
        elif self.action in ['transfer', 'receive_iot_data']:
            permission_classes = [IsMarketOrLogisticsStaff]
            
        # 3. Güvenlik: Paletler manuel güncellenemez veya silinemez (Blokzincir bütünlüğü)
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser] # Sadece sistem admini (Django Admin)
            
        # 4. Görüntüleme (Listeleme/Detay): Tüm sistem paydaşları okuyabilir
        else:
            permission_classes = [IsAuthenticated]
            
        return [permission() for permission in permission_classes]

# Lojistik islemler icin gerekli action
    @action(detail=True, methods=["patch"], url_path="transfer", permission_classes=[IsMarketOrLogisticsStaff])
    def transfer(self, request, master_qr_id=None):
        pallet = self.get_object()

        # Lojistik calisani yeni urunleri aliyor
        new_holder_code = request.data.get("new_holder_code")
        new_status = request.data.get("status")

        #eksik veri olmasi durumunda
        if not new_holder_code or not new_status:
            return Response({"error": "new_holder_code ve status alanlari eksik"}, status=400)
        # 3. Yeni sahibin (kurumun) veritabanında gerçekten var olup olmadığını kontrol et
        new_holder = get_object_or_404(Organization, org_code=new_holder_code)
        courier_wallet = request.user.wallet_address

        # Log için eski sahibin adını kenara not alalım
        old_holder_name = pallet.current_holder.name if pallet.current_holder else "Bilinmiyor"

    # --- ADIM A: POSTGRESQL GÜNCELLEMESİ ---
        pallet.current_holder = new_holder
        pallet.status = new_status
        pallet.save() # Veritabanına kalıcı olarak yazıldı!

    # --- ADIM B: BLOKZİNCİR GÜNCELLEMESİ (DUAL WRITE) ---
        payload_data = {
            "transfer_from_org": old_holder_name,
            "transfer_to_org_code": new_holder.org_code,
            "new_status": new_status,
            "timestamp": "otomatik eklenecek",
            "notes": request.data.get("notes", "Transfer standart prosedürlere uygun gerçekleşti.")
        }

    # log_to_blockchain servisine verileri gönderiyoruz.
        dynamic_action_type = 'RECV' if new_holder.organization_type == 'MARKET' else 'TRAN'
    # İşlem tipi olarak market ya da lojistik olma durumuna göre 
    # 'TRAN' (Transfer/Lojistik) yada RECV kodunu kullanıyoruz.
        log = log_to_blockchain(
            pallet=pallet, 
            user=request.user, # İşlemi yapan şoför/market yetkilisi
            action_type=dynamic_action_type, 
            payload=payload_data
        )

        # 4. İstemciye (Mobil Uygulamaya) Başarı Yanıtı ve Makbuz (TxID) Dön
       # 4. İstemciye (Mobil Uygulamaya) Başarı Yanıtı ve Takip Numarası Dön
        return Response({
            "message": f"Palet mülkiyeti başarıyla {new_holder.name} kurumuna devredildi.",
            "tracking_id": log.id, # txid yerine yerel veritabanı ID'sini dönüyoruz
            "status_info": "İşlem blokzincir kuyruğuna alındı.",
            "courier_verified": bool(courier_wallet),
            "new_status": pallet.status
        }, status=200)

# IoT simulasyonu gerceklestirilcek action tanimi yapilmaktadir.
    @action(detail=True, methods=["post"], url_path="iot-data")
    def receive_iot_data(self, request, master_qr_id=None):
        pallet = self.get_object()
        temp = request.data.get("temperature")
        humidity = request.data.get("humidity")

        #Dagitim araci sicaklik kontrolu
        # 8 derecenin ustu risklidir.
        if temp and float(temp) > 8.0:
            pallet.is_quality_maintained = False
            pallet.status = "SPOILED" # Durum sorunlu olarak guncellendi
            pallet.save()

            payload = {"alert": "Sıcaklık sınırı aşıldı!", "temp": temp, "humidity":humidity}
            log_to_blockchain(pallet, request.user, "QUAL", payload)

            return Response({
                "status": "CRITICAL",
                "message": "Sıcaklık ihlali tespit edildi! Palet durumu güncellendi ve loglandı."
            }, status=400)
        
        # Eger her sey yolundaysa sadece veri alindi bilgisi verilir. Cunku surekli gelen sicaklik verisini
        # Blockzinciri kaydetmek verimsiz olacaktir. yani sadece ihlaller bildiriliyor.
        return Response({"status": "OK", "message": "Veri alindi, degerler normal."})

    # POST işlemi sırasında araya girip üreticiyi ve ilk sahibini otomatik atıyoruz
    def perform_create(self, serializer):
        organization = self.request.user.organization
        now = timezone.now()

        # 1. GÜVENLİK DUVARI: Çiftliğin aktif bir sertifikası var mı?
        # valid_from bugünden küçük/eşit olmalı, valid_to bugünden büyük/eşit olmalı
        active_certificate = InspectionCertificate.objects.filter(
            producer=organization,
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).first()

        # Eğer aktif sertifika yoksa, hacker postman'den istek atsa bile reddet!
        if not active_certificate:
            raise PermissionDenied(
                "Üretim durduruldu: Çiftliğinize ait geçerli bir veteriner denetim sertifikası bulunamadı."
            )

        # 2. HER ŞEY YOLUNDA: Paleti otomatik 'Onaylı' olarak kaydet
        pallet = serializer.save(
            producer=organization, 
            current_holder=organization,
            vet_approval=True # Veteriner tek tek onaylamaz, sertifika olduğu için otomatik True olur!
        )

        # 3. BLOKZİNCİR LOGU (Opsiyonel ama mükemmel olur)
        # Paletin hangi sertifika numarasına dayanarak üretildiğini blokzincire kazıyoruz.
        payload_data = {
            "action": "PALLET_CREATED",
            "auto_vet_approval": True,
            "certificate_no": active_certificate.certificate_no,
            "inspector_org": active_certificate.inspector.name
        }
        log_to_blockchain(pallet, self.request.user, "PROD", payload_data)

class PackageViewSet(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    lookup_field = "package_qr_id"

    def get_permissions(self):
        """
        DİNAMİK YETKİ:
        - Tüketici okur (AllowAny)
        - Üretici yaratır (IsProducer)
        - Kimse güncelleyemez (Güvenlik)
        """
        if self.action in ['list', 'retrieve', 'get_history']:
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsProducer] # YALNIZCA ÜRETİCİ YENİ PAKET GİREBİLİR
        else:
            # PUT, PATCH, DELETE işlemlerine kimsenin yetkisi yok
            permission_classes = [permissions.IsAdminUser] 
            
        return [permission() for permission in permission_classes]
    
    # POST işlemi sırasında araya girip üreticiyi ve ilk sahibini otomatik atıyoruz
    def perform_create(self, serializer):
        # 1. Kullanıcının paketi eklemeye çalıştığı paleti tespit et
        target_pallet = serializer.validated_data.get('pallet')
        
        # 2. İşlemi yapan kullanıcının kurumunu bul
        user_organization = self.request.user.organization
        
        # 3. GÜVENLİK KONTROLÜ: Bu palet gerçekten işlemi yapan çiftliğe mi ait?
        if target_pallet.producer != user_organization:
            # Eğer başkasının paletine paket koymaya çalışıyorsa işlemi reddet!
            raise PermissionDenied("Güvenlik ihlali: Sadece kendi kurumunuza ait paletlere paket ekleyebilirsiniz.")
        
        # İşlem Bütünlüğü: Eğer bu bloğun içinde herhangi bir hata (Exception) çıkarsa,
        # Django veritabanına yapılan kayıtları (save) otomatik olarak geri alır (Rollback).
        with transaction.atomic():
            package = serializer.save()
            
            # 2. Paket bilgilerini blokzincire 'üretim kanıtı' olarak kazı
            payload = {
                "action": "PACKAGE_CREATED",
                "package_qr": package.package_qr_id,
                "pallet_qr": package.pallet.master_qr_id,
                "feeding_type": package.get_feeding_type_display(),
                "laying_date": str(package.laying_date),
                "expiry_date": str(package.expiry_date)
            }
            
            # Bu log, paketin bireysel kimlik kartı olur
            log_to_blockchain(
                pallet=package.pallet, 
                user=self.request.user, 
                action_type='PROD', 
                payload=payload
            )

    @action(detail=True, methods=["get"], url_path="history", permission_classes=[AllowAny])
    def get_history(self, request, package_qr_id=None):
        # 1. Paketi bul
        package = self.get_object()
        
        # 2. Paketin bağlı olduğu palete ulaş
        target_pallet = package.pallet
        
        # 3. Paletin geçmişini (BlockchainTransaction) çek
        # PalletViewSet'teki mantığın aynısını buraya kuruyoruz
        pallet_data = PalletSerializer(target_pallet).data
        transactions = target_pallet.transactions.all()
        transaction_data = BlockchainTransactionSerializer(transactions, many=True).data

        return Response({
            "package_details": PackageSerializer(package).data,
            "traceability_summary": {
            "origin_pallet": target_pallet.master_qr_id,
            "status": target_pallet.status,
            "is_quality_maintained": target_pallet.is_quality_maintained
        },
        "timeline": transaction_data
        })

class BlockchainTransactionsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BlockchainTransaction.objects.all()
    serializer_class = BlockchainTransactionSerializer
    
    # 1. WEB3 STANDARDI: Detay aramalarında ID yerine Hash kullanılır
    lookup_field = 'tx_hash'

    # 2. FRONTEND'İN HAYAT KURTARICISI: Filtreleme Mekanizması
    filter_backends = [DjangoFilterBackend]
    
    # Frontend'in URL sonuna soru işareti (?) ile parametre ekleyebileceği alanlar
    filterset_fields = [
        'pallet__master_qr_id',  # Örn: ?pallet__master_qr_id=PAL-123
        'organization__org_code',# Örn: ?organization__org_code=ORG-A101
        'status',                # Örn: ?status=PENDING
        'action_type'            # Örn: ?action_type=TRAN
    ]