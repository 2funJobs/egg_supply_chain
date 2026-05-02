from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework import permissions
from users.permissions import IsProducer, IsMarketOrLogisticsStaff
from .models import Pallet, Package
from organizations.models import Organization, InspectionCertificate
from .serializers import PalletSerializer, PackageSerializer
from blockchain.serializers import BlockchainTransactionSerializer
from blockchain.services import log_to_blockchain
from organizations.views import OrganizationViewSet

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
        transfer_date = timezone.now().isoformat()
    # --- ADIM A: POSTGRESQL GÜNCELLEMESİ ---
        pallet.current_holder = new_holder
        pallet.status = new_status
        pallet.save() # Veritabanına kalıcı olarak yazıldı!

    # --- ADIM B: BLOKZİNCİR GÜNCELLEMESİ (DUAL WRITE) ---
        payload_data = {
            "transfer_from_org": old_holder_name,
            "transfer_to_org_code": new_holder.org_code,
            "new_status": new_status,
            "timestamp": transfer_date,
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
        
        if pallet.status != 'IN_TRANSIT':
            return Response({"error": "Sadece yoldaki paletler için sıcaklık işlenebilir."}, status=400)

        temp = request.data.get("temperature")
        humidity = request.data.get("humidity")
        if (temp is None) or (humidity is None):
            return Response({"error": "Taşıma kalite verisi eksik!"}, status=400)

        try:
            temp_val = float(temp)
            humidity_val = float(humidity)
        except ValueError:
            return Response({"error": "Sıcaklık ve nem değerleri sayısal olmalıdır!"}, status=400)

        # Kural Kontrolü
        if (15 <= temp_val <= 26) and (70 <= humidity_val <= 85):
           return Response({
                "status": "OK",
                "message": f"Veri alındı. (Sıcaklık: {temp_val}°C, Nem: {humidity_val}%) - Mevzuata Uygun."
            })
        else:
            pallet.is_quality_maintained = False
            pallet.status = "FAULTY"
            pallet.save()

            # 3. DÜZELTME: Fazladan parantez kaldırıldı
            alert_message = f"Uygunsuz taşıma koşulu! Sıcaklık: {temp_val}°C, Nem: {humidity_val}%"

            # 2. DÜZELTME: Nem (humidity) verisi blokzincir kanıtına eklendi
            payload = {"alert": alert_message, "temp": temp_val, "humidity": humidity_val}
            log_to_blockchain(pallet, request.user, "QUAL", payload)

            return Response({
                "status": "CRITICAL",
                "message": alert_message
            }, status=400)

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
        
        # Palet yola çıkmış mı?
        # Eğer paletin güncel sahibi çiftçi değilse VEYA durumu "Üretimde" değilse işlemi reddet!
        if target_pallet.current_holder != user_organization or target_pallet.status != 'IN_PRODUCTION':
            raise PermissionDenied(
                "Yola çıkmış veya teslim edilmiş bir palete yeni paket ekleyemezsiniz."
            )

        # Sertifikalı olduğunun kanıtı
        # certificate = target_pallet.transactions.filter(action_type='CERT'.first().payload.get("certificate_no"))

        # İşlem Bütünlüğü: Eğer bu bloğun içinde herhangi bir hata (Exception) çıkarsa,
        # Django veritabanına yapılan kayıtları (save) otomatik olarak geri alır (Rollback).
        with transaction.atomic():
            package = serializer.save()
            
            # 2. Paket bilgilerini blokzincire 'üretim kanıtı' olarak kazı
            payload = {
                "action": "PACKAGE_CREATED",
                "package_qr": package.package_qr_id,
                "pallet_qr": package.pallet.master_qr_id,
                "quality_class": "A Sınıfı",
                "feeding_type": package.get_feeding_type_display(),
                "laying_date": str(package.laying_date),
                "expiry_date": str(package.expiry_date),
                "capacity": package.capacity,
                # "certificate_ref": certificate
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
        # 2. Paletin TÜM geçmişini çek
        # timestamp değerinin geçmiçten geleceğe olması için "-" değeri konulmaz.
        all_transactions = target_pallet.transactions.all().order_by('timestamp')
        
        # 3. FİLTRELEME (Gürültüyü Temizle)
        filtered_transactions = []
        for tx in all_transactions:
            payload = tx.payload or {}
            
            # Eğer bu log bir "Paket Üretim" loguysa ve QR kodu BİZİM paketimizle EŞLEŞMİYORSA, bunu atla (continue).
            if tx.action_type == 'PROD' and payload.get('package_qr') and payload.get('package_qr') != package.package_qr_id:
                continue
                
            # Geriye kalan her şeyi (Genel palet hareketleri ve bizim paketimizin logu) listeye ekle
            filtered_transactions.append(tx)

        # 4. Temizlenmiş listeyi Serializer'a ver
        # pallet_data = PalletSerializer(target_pallet).data
        transaction_data = BlockchainTransactionSerializer(filtered_transactions, many=True).data

        return Response({
            # "package_details": PackageSerializer(package).data,
            # "traceability_summary": {
            #     "origin_pallet": target_pallet.master_qr_id,
            #     "status": target_pallet.status,
            #     "is_quality_maintained": target_pallet.is_quality_maintained
            # },
            "timeline": transaction_data
        })
