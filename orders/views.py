from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
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
        if self.action == 'get_history':
            permission_classes = [AllowAny]
    # Varsayılan olarak paletlere sadece giriş yapmış kullanıcılar erişsin
    # Ancak yeni Palet YARATMA (POST) işlemini SADECE ÜRETİCİ yapabilsin
        elif self.action == 'create':
            permission_classes = [IsProducer]
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
    
    @action(detail=True, methods=["get"], url_path="history", permission_classes=[AllowAny])
    # Allow any ile herkes authenticaion yani token ihtiycai olmdadan blockchain bilgisine erisebilir.
    def get_history(self, request, master_qr_id=None):
        # Paletin tum yasam dongusunun sunulacagi metod tanimidir.
        pallet = self.get_object()

        pallet_data = self.get_serializer(pallet).data

        transactions = pallet.transactions.all()
        transaction_data = BlockchainTransactionSerializer(transactions, many=True).data

        return Response({
            "product_info": pallet_data,
            "timeline": transaction_data
        })

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
        if self.action in ['list', 'retrieve']:
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
        
        # 4. Her şey yolundaysa paketi kaydet (Package modelinde ekstra alan olmadığı için içi boş save yeterli)
        serializer.save()

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