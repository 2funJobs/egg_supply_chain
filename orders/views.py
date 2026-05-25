import uuid
import datetime
from .utils import calculate_haversine_distance
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework import permissions
from rest_framework.views import APIView
from users.permissions import IsProducer, IsMarketOrLogisticsStaff
from .models import Pallet, Package, MarketOrder, MarketOrderItem
from organizations.models import Organization, InspectionCertificate
from .serializers import PalletSerializer, PackageSerializer
from blockchain.serializers import BlockchainTransactionSerializer
from blockchain.services import log_to_blockchain
from organizations.views import OrganizationViewSet
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import MarketOrderSerializer, MarketOrderItemSerializer

class PalletViewSet(viewsets.ModelViewSet):
    # Paletleri listeleyen, yeni palet olusturan API endpoint
    queryset = Pallet.objects.all().order_by("-created_at")
    serializer_class = PalletSerializer
    # Paletlere id(QR) degeri saglayacak atama
    lookup_field = "master_qr_id"
    filter_backends = [DjangoFilterBackend]
    
    # Frontend'in URL sonuna soru işareti (?) ile parametre ekleyebileceği alanlar
    filterset_fields = ['status']

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
            permission_classes = [IsAdminUser] # Sadece sistem admini (Django Admin)
            
        # 4. Görüntüleme (Listeleme/Detay): Tüm sistem paydaşları okuyabilir
        else:
            permission_classes = [IsMarketOrLogisticsStaff | IsProducer]
            
        return [permission() for permission in permission_classes]

# Lojistik islemler icin gerekli action
    @action(detail=True, methods=["patch"], url_path="transfer", permission_classes=[IsMarketOrLogisticsStaff])
    def transfer(self, request, master_qr_id=None): # master_qr_id yerine pk kullanımı Django standartıdır
        pallet = self.get_object()
        old_status= pallet.status

        user_organization = request.user.organization # Kullanıcının bağlı olduğu kurum
        
        # 2. Request ile gelen holder_code'u sadece KONTROL için al (isteğe bağlı)
        claimed_holder_code = request.data.get("new_holder_code")

        # 3. GÜVENLİK KONTROLÜ: 
        # Giriş yapmış kullanıcının kurum kodu ile gönderilen kod eşleşiyor mu?
        if str(user_organization.org_code) != str(claimed_holder_code):
            raise PermissionDenied("Başka bir kurum adına işlem yapamazsınız!")

        # 1. Verileri Al
        new_organization_type = request.data.get("current_holder.organization_type")
        new_holder_code = request.data.get("new_holder_code")
        new_status = request.data.get("status")
        is_quality_maintained = request.data.get("is_quality_maintained")
        
        # 2. Eksik Veri Kontrolü
        if not new_holder_code or not new_status:
            return Response({"error": "new_holder_code ve status alanlari eksik"}, status=400)

        # 3. İş Mantığı Doğrulaması (Business Logic)
        print(f"DEBUG: Eski Durum: '{old_status}', Yeni Durum: '{new_status}'")
        
        if old_status == "IN_PRODUCTION" and new_status == "AT_MARKET":
            raise PermissionDenied("Üreticiden doğrudan markete transfer yapılamaz!")

        # 4. Not Belirleme (Düzeltilen Kısım)
        # request.data immutable (değiştirilemez) olabileceği için yerel değişken kullanıyoruz
        note_text = request.data.get("notes")
        if not note_text:
            if new_status == "AT_MARKET" and is_quality_maintained is False:
                note_text = "Sıcaklık ve Nem birimi eksik yada uygunsuz."
            else:
                note_text = "Transfer standart prosedürlere uygun gerçekleşti."

        # 5. İlişkili Objeyi Bul
        new_holder = get_object_or_404(Organization, org_code=new_holder_code)
        
        # 6. Güncelleme İşlemleri
        old_holder_name = pallet.current_holder.name if pallet.current_holder else "Bilinmiyor"
        transfer_date = timezone.now().isoformat()
        courier_wallet = getattr(request.user, 'wallet_address', None) # Güvenli erişim

        # PostgreSQL Güncelleme
        pallet.current_holder = new_holder
        pallet.status = new_status
        pallet.save()

        # 7. Blokzincir Loglama
        payload_data = {
            "transfer_from_org": old_holder_name,
            "transfer_to_org_code": new_holder.org_code,
            "new_status": new_status,
            "timestamp": transfer_date,
            "notes": note_text # Düzeltilen yerel değişken
        }

        dynamic_action_type = 'RECV' if new_holder.organization_type == 'MARKET' else 'TRAN'
        
        log = log_to_blockchain(
            pallet=pallet, 
            user=request.user, 
            action_type=dynamic_action_type, 
            payload=payload_data
        )

        return Response({
            "message": f"Palet mülkiyeti başarıyla {new_holder.name} kurumuna devredildi.",
            "tracking_id": log.id,
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
           pallet.is_quality_maintained = True
           return Response({
                "status": "OK",
                "message": f"Veri alındı. (Sıcaklık: {temp_val}°C, Nem: {humidity_val}%) - Mevzuata Uygun."
            })
        else:
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
        today = datetime.date.today()
        departure_date = today + datetime.timedelta(days=2)
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
            vet_approval=True, # Veteriner tek tek onaylamaz, sertifika olduğu için otomatik True olur!
            departure_date=departure_date
        )

        # 3. BLOKZİNCİR LOGU (Opsiyonel ama mükemmel olur)
        # Paletin hangi sertifika numarasına dayanarak üretildiğini blokzincire kazıyoruz.
        payload_data = {
            "action": "PALLET_CREATED",
            "auto_vet_approval": True,
            "departure_date": str(departure_date),
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
        THE HYBRID TRACEABILITY MODEL:
        - /packages/ (list): Sadece Üretici (B2B Gizliliği)
        - /packages/ID/ (retrieve): Sadece Üretici (B2B Gizliliği)
        - /packages/ID/history/ (get_history): HERKES (Tüketici Şeffaflığı)
        """
        
        if self.action == 'get_history':
            # Consumers scanning the QR code ONLY hit this endpoint. 
            # They get to see the blockchain timeline and that's it.
            permission_classes = [AllowAny]
            
        elif self.action in ['list', 'retrieve', 'create']:
            # The actual raw package data and the full list are locked down
            # to internal supply chain staff only.
            permission_classes = [IsProducer] 
            
        else:
            # PUT, PATCH, DELETE 
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
            "package_details": PackageSerializer(package).data,
            # "traceability_summary": {
            #     "origin_pallet": target_pallet.master_qr_id,
            #     "status": target_pallet.status,
            #     "is_quality_maintained": target_pallet.is_quality_maintained
            # },
            "timeline": transaction_data
        })

class MarketOrderViewSet(viewsets.ModelViewSet):
    serializer_class = MarketOrderSerializer
    
    def get_queryset(self):
        user_org = self.request.user.organization
        
        if user_org.organization_type == 'MARKET':
            return MarketOrder.objects.filter(market=user_org).order_by('-created_at')
        elif user_org.organization_type == 'PRODUCER':
            return MarketOrder.objects.filter(assigned_producer=user_org).order_by('-created_at')
        
        if self.request.user.is_staff:
            return MarketOrder.objects.all().order_by('-created_at')
            
        return MarketOrder.objects.none()
    
    # YENİ: Tek bir POST isteğiyle Karma Sipariş (Order + Items) oluşturmak için
    def perform_create(self, serializer):
        user_org = self.request.user.organization
        if user_org.organization_type != 'MARKET':
            raise PermissionDenied("Only markets can create orders.")
        
        # Güvenlik: Siparişi oluşturan marketi otomatik ata ve durumu DRAFT yap
        serializer.save(market=user_org, status='DRAFT')

    @action(detail=False, methods=['get', 'post'], url_path='my-cart')
    def my_cart(self, request):
        user_org = request.user.organization
        if user_org.organization_type != 'MARKET':
            raise PermissionDenied("Only markets can have a shopping cart.")

        order, created = MarketOrder.objects.get_or_create(
            market=user_org, 
            status='DRAFT'
        )
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    # NEW: Checkout logic moved inside the ViewSet
    @action(detail=True, methods=['post'], url_path='checkout')
    def checkout(self, request, pk=None):
        order = self.get_object() # Automatically handles 404 safely
        
        if order.status != 'DRAFT':
            return Response({"error": "Cart is already submitted."}, status=status.HTTP_400_BAD_REQUEST)
            
        if not order.items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        producers = Organization.objects.filter(
            organization_type='PRODUCER', 
            latitude__isnull=False, 
            longitude__isnull=False
        )

        if not producers.exists():
            return Response({"error": "No producers available in the system."}, status=status.HTTP_400_BAD_REQUEST)

        closest_producer = None
        shortest_distance = float('inf')

        for producer in producers:
            distance = calculate_haversine_distance(
                order.market.latitude, order.market.longitude,
                producer.latitude, producer.longitude
            )
            if distance < shortest_distance:
                shortest_distance = distance
                closest_producer = producer

        order.status = 'ASSIGNED'
        order.assigned_producer = closest_producer
        order.save()

        return Response({
            "message": "Order placed and routed to nearest producer!",
            "producer": closest_producer.name,
            "distance_km": round(shortest_distance, 2)
        })

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='accept')
    def accept_order(self, request, pk=None):
        order = self.get_object()
        
        if order.status != 'ASSIGNED':
            return Response({"error": "Order not found or already processed."}, status=status.HTTP_400_BAD_REQUEST)

        producer_org = request.user.organization
        
        # 0. GÜVENLİK DUVARI 1: Is this producer actually the assigned one?
        if order.assigned_producer != producer_org:
            raise PermissionDenied("You can only accept orders assigned to your organization.")

        # 1. GÜVENLİK DUVARI 2: Çiftliğin aktif bir sertifikası var mı?
        now = timezone.now()
        active_certificate = InspectionCertificate.objects.filter(
            producer=producer_org,
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).first()

        if not active_certificate:
            raise PermissionDenied(
                "Üretim durduruldu: Çiftliğinize ait geçerli bir veteriner denetim sertifikası bulunamadı."
            )
        
        today = datetime.date.today()
        departure_date = today + datetime.timedelta(days=2)
        # 2. Paleti Oluştur (Otomatik onaylı olarak)
        new_pallet = Pallet.objects.create(
            producer=producer_org,
            current_holder=producer_org,
            departure_date=departure_date,
            status='IN_PRODUCTION',
            vet_approval=True  # Sertifika olduğu için otomatik True!
        )
        
        # 3. BLOKZİNCİR LOGU: Palet Üretimi
        payload_data = {
            "action": "PALLET_CREATED",
            "departure_date": str(departure_date),
            "auto_vet_approval": True,
            "certificate_no": active_certificate.certificate_no,
            "inspector_org": active_certificate.inspector.name,
            "fulfillment_for_order": order.id
        }
        log_to_blockchain(new_pallet, request.user, "PROD", payload_data)

        # 4. Paketleri Oluştur
        packages_to_create = []
        expiry = today + datetime.timedelta(days=28) 

        for item in order.items.all():
            for _ in range(item.package_quantity):
                generated_qr = f"PKG-{uuid.uuid4().hex[:6].upper()}"
                package = Package(
                    package_qr_id=generated_qr,
                    pallet=new_pallet,
                    feeding_type=item.feeding_type,
                    capacity=item.capacity,
                    laying_date=today,
                    expiry_date=expiry
                )
                packages_to_create.append(package)

        Package.objects.bulk_create(packages_to_create)
        total_packages = sum(item.package_quantity for item in order.items.all())

        # 5. Siparişi Güncelle
        order.fulfilled_pallet = new_pallet
        order.status = 'IN_PRODUCTION'
        order.save()

        # We extract all the generated QR codes from the memory list
        generated_qr_list = [pkg.package_qr_id for pkg in packages_to_create]

        # 6. Siparişin Kabul Edildiğine Dair Log (Opsiyonel ama takip için iyi)
        bulk_package_payload = {
            "action": "BULK_PACKAGES_CREATED",
            "pallet_qr": new_pallet.master_qr_id,
            "total_packages_minted": total_packages,
             # List of all QRs inside the pallet
            # "quality_class": "A Sınıfı",
            # "laying_date": str(today),
            # "expiry_date": str(expiry),
            # "certificate_used": active_certificate.certificate_no
        }
        
        log_to_blockchain(new_pallet, request.user, "PROD", bulk_package_payload)

        return Response({
            "message": "Order accepted! Pallet and packages generated under active certificate.",
            "pallet_qr": new_pallet.master_qr_id,
            "total_packages": total_packages,
            "certificate_used": active_certificate.certificate_no
        }, status=status.HTTP_201_CREATED)

class MarketOrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = MarketOrderItemSerializer
    queryset = MarketOrderItem.objects.all()

    # YENİ: Dizi (Array) şeklindeki JSON'ları kabul etmek için many=True ayarı
    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        user_org = self.request.user.organization
        validated_data = serializer.validated_data

        # YENİ: Veri liste (çoklu) olarak gelmişse
        if isinstance(validated_data, list):
            for item in validated_data:
                order = item.get('order')
                if order.market != user_org:
                    raise PermissionDenied("You cannot add items to another market's cart.")
                if order.status != 'DRAFT':
                    raise PermissionDenied("You can only edit orders that are in DRAFT status.")
        # Veri tekil obje olarak gelmişse
        else:
            order = validated_data.get('order')
            if order.market != user_org:
                raise PermissionDenied("You cannot add items to another market's cart.")
            if order.status != 'DRAFT':
                raise PermissionDenied("You can only edit orders that are in DRAFT status.")

        serializer.save()

    def perform_update(self, serializer):
        # SECURITY: Prevent editing items if the order is already submitted
        item = self.get_object()
        if item.order.status != 'DRAFT':
            raise PermissionDenied("Cannot edit items in an order that has already been submitted.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.order.status != 'DRAFT':
            raise PermissionDenied("Cannot remove items from an order that has already been submitted.")
        instance.delete()