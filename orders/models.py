from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
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
    master_qr_id = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="Pallet (Master)QR")
    producer = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name='produced_pallets', verbose_name="Producer")
    current_holder = models.ForeignKey("organizations.Organization", on_delete=models.SET_NULL, null=True, related_name='held_pallets', verbose_name="Current Holder")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PRODUCTION', verbose_name="Status")

# Güvenlik ve Kalite Metrikleri
    vet_approval = models.BooleanField(default=False, verbose_name="Vet Approval")
    is_quality_maintained = models.BooleanField(default=False, verbose_name="Quality/Temperature Ensured?")
    departure_date = models.DateTimeField(null=True, blank=True, verbose_name="Çıkış Tarihi")
    created_at = models.DateTimeField(auto_now_add=True)

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

    package_qr_id = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="Paket QR")
    pallet = models.ForeignKey(Pallet, on_delete=models.CASCADE, related_name="packages", verbose_name="Related Pallet")
    feeding_type = models.IntegerField(choices=FEEDING_TYPE, default=2, verbose_name="Beslenme Türü")
    laying_date = models.DateField(verbose_name="Yumurtlama Tarihi")
    expiry_date = models.DateField(verbose_name="TETT")
    capacity = models.IntegerField(choices=CAPACITY, default=30, verbose_name="Kapasite")

    def __str__(self):
        return f"Package: {self.package_qr_id}"