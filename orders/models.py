from django.db import models
import uuid

# 3.Pallet Table
class Pallet(models.Model):
    STATUS_CHOICES= [
        ('IN_PRODUCTION', "Preparing"),
        ('IN_TRANSIT', 'On Delivery'),
        ('AT_MARKET', 'On Retail'),
        ('FAULTY', 'Fault/Cancelled')
    ]

    # UUID, db_index=True arama hızını artırır.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    master_qr_id = models.CharField(max_length=100, unique=True, editable=False, db_index=True, verbose_name="Pallet (Master)QR")
    producer = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name='produced_pallets', verbose_name="Producer")
    current_holder = models.ForeignKey("organizations.Organization", on_delete=models.SET_NULL, null=True, related_name='held_pallets', verbose_name="Current Holder")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PRODUCTION', verbose_name="Status")

# Güvenlik ve Kalite Metrikleri
    vet_approval = models.BooleanField(default=False, verbose_name="Vet Approval")
    is_quality_maintained = models.BooleanField(default=False, verbose_name="Quality/Temperature Ensured?")
    departure_date = models.DateTimeField(null=True, blank=True, verbose_name="Çıkış Tarihi")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Eğer bu palet ilk defa oluşturuluyorsa (henüz QR kodu yoksa) otomatik üret!
        if not self.master_qr_id:
            # Örn: PAL-A7B29F4C (Kısa, estetik ve benzersiz bir QR barkod numarası)
            self.master_qr_id = f"PAL-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pallet: {self.master_qr_id}"

# 4. Paket Varlığı (Unit QR / Tüketici Birimi)
class Package(models.Model):
    FEEDING_TYPE= [
        (0, "Organik"),
        (1, 'Gezen Tavuk'),
        (2, 'Kümes'),
        (3, 'Kafes')
    ]

    CAPACITY = [
        (6, "6'lı"),
        (15, "15'li"),
        (30, "30'lu")
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_qr_id = models.CharField(max_length=100, unique=True, editable=False, db_index=True, verbose_name="Paket QR")
    pallet = models.ForeignKey(Pallet, on_delete=models.CASCADE, related_name="packages", verbose_name="Related Pallet")
    feeding_type = models.IntegerField(choices=FEEDING_TYPE, default=2, verbose_name="Beslenme Türü")
    laying_date = models.DateField(verbose_name="Yumurtlama Tarihi")
    expiry_date = models.DateField(verbose_name="TETT")
    capacity = models.IntegerField(choices=CAPACITY, default=30, verbose_name="Kapasite")

    def save(self, *args, **kwargs):
        # Koliler için otomatik QR üretimi
        if not self.package_qr_id:
            # Örn: PKG-E91D3F (Kutu barkodu)
            self.package_qr_id = f"PKG-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Package: {self.package_qr_id}"