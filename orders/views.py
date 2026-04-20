from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from .permissions import IsProducer, IsVet, IsLogistics
from .models import Organization, Pallet, Package
from .serializers import OrganizationSerializer, PalletSerializer, BlockchainTransactionSerializer, PackageSerializer
from .services import log_to_blockchain

class OrganizationViewSet(viewsets.ModelViewSet):
    # Kurumlari listeleyen ve olusturan API endpoint
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class PalletViewSet(viewsets.ModelViewSet):
    # Paletleri listeleyen, yeni palet olusturan API endpoint
    queryset = Pallet.objects.all().order_by("-created_at")
    serializer_class = PalletSerializer
    # Paletlere id(QR) degeri saglayacak atama
    lookup_field = "master_qr_id"
    
    def get_permissions(self):
    # Varsayılan olarak paletlere sadece giriş yapmış kullanıcılar erişsin
        permission_classes = [IsAuthenticated]
    # Ancak yeni Palet YARATMA (POST) işlemini SADECE ÜRETİCİ yapabilsin
        if self.action == 'create':
            permission_classes = [IsProducer]
        return [permission() for permission in permission_classes]
    
    # Veteriner Onayi(sadece veteriner token ile islem yapabilir)
    @action(detail=True, methods=['post'], url_path="vet-approval", permission_classes="[IsVet]")
    def vet_approval(self, request, master_qr_id=None):
        pallet = self.get_object() #URL deki IDden ilgili palet
        # user = request.user
        pallet.vet_approval = True
        pallet.save()

        # simdi blockzincir logu olusturalim.
        payload_data = {
            "is_approved": True,
            "vet_notes": request.data.get("notes", "Sorunsuz") 
        }

        # Kalite Kontrolu
        log = log_to_blockchain(pallet, user, "QLTY", payload_data)
        return Response({"message": "Veteriner onayi basarili", "txid": log.tx_hash})
    
# Lojistik islemler icin gerekli action
    @action(detail=True, methods=["patch"], url_path="transfer", permission_classes=[IsLogistics])
    def transfer(self, request, master_qr_id=None):
        pallet = self.get_object()

        # Lojistik calisani yeni urunleri aliyor
        new_holder_id = request.data.get("new_holder_id")
        new_status = request.data.get("status")

        #eksik veri olmasi durumunda
        if not new_holder_id or not new_status:
            return Response({"error": "new_holder_id ve status alanlari eksik"}, status=400)
        # 3. Yeni sahibin (kurumun) veritabanında gerçekten var olup olmadığını kontrol et
        new_holder = get_object_or_404(Entity, id=new_holder_id)

        # Log için eski sahibin adını kenara not alalım
        old_holder_name = pallet.current_holder.name if pallet.current_holder else "Bilinmiyor"

    # --- ADIM A: POSTGRESQL GÜNCELLEMESİ ---
        pallet.current_holder = new_holder
        pallet.status = new_status
        pallet.save() # Veritabanına kalıcı olarak yazıldı!

    # --- ADIM B: BLOKZİNCİR GÜNCELLEMESİ (DUAL WRITE) ---
        payload_data = {
            "transfer_from": old_holder_name,
            "transfer_to": new_holder.name,
            "new_status": new_status,
            "notes": request.data.get("notes", "Transfer standart prosedürlere uygun gerçekleşti.")
        }

    # log_to_blockchain servisine verileri gönderiyoruz.
    # İşlem tipi olarak 'TRAN' (Transfer/Lojistik) kodunu kullanıyoruz.
        log = log_to_blockchain(
            pallet=pallet, 
            user=request.user, # İşlemi yapan şoför/market yetkilisi
            action_type='TRAN', 
            payload=payload_data
        )

        # 4. İstemciye (Mobil Uygulamaya) Başarı Yanıtı ve Makbuz (TxID) Dön
        return Response({
            "message": f"Palet mülkiyeti başarıyla {new_holder.name} kurumuna devredildi.",
            "txid": log.tx_hash,
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
            log_to_blockchain(pallet, request.user, "QLTY", payload)

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
        # İşlemi yapan kullanıcının bağlı olduğu kurumu bul
        organization = self.request.user.organization
        
        # Paleti oluştururken üreticiyi ve mevcut sahibini bu kurum olarak zorla kaydet
        serializer.save(producer=organization, current_holder=organization)

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