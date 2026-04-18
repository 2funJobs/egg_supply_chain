from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from .models import Organization, Pallet
from .serializers import OrganizationSerializer, PalletSerializer, BlockchainTransactionSerializer
from .services import log_to_blockchain

class OrganizationViewSet(viewsets.ModelViewSet):
    # Kurumlari listeleyen ve olusturan API endpoint
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class PalletViewSet(viewsets.ModelViewSet):
    # Paletleri listeleyen, yeni palet olusturan API endpoint
    queryset = Pallet.objects.all().order_by("-created_at")
    serializer_class = PalletSerializer

    # Authorization condition
    permission_classes = [IsAuthenticated]

    # Paletlere id(QR) degeri saglayacak atama
    lookup_field = "master_qr_id"

    @action(detail=True, methods=['post'], url_path="vet-approval")
    def vet_approval(self, request, master_qr_id=None):
        pallet = self.get_object() #URL deki IDden ilgili palet
        user = request.user

        if user.role != 'VET':
            return Response({"error": "Sadece Veteriner yetkisine sahip kullanıcılar bu işlemi yapabilir."}, status=403)
        # Veritabani palet tablosunu guncelle
        pallet.vet_approval = True
        pallet.save()

        # simdi blockzincir logu olusturalim.
        payload_data = {
            "is_approved": True,
            "vet_notes": request.data.get("notes", "Sorunsuz") 
        }

        # Kalite Kontrolu
        log = log_to_blockchain(pallet, user, "QLTY", payload_data)

        return Response({
            "message": "Veteriner onayi basarili ve aga islendi",
            "pallet_id": pallet.master_qr_id,
            "blockchain_txid": log.tx_hash, # Kaniti geri donuyor
            "timestamp": log.timestamp
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
