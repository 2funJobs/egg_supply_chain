from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# 1_Organization Table

class Organization(models.Model):
    # Uretici, Dagitici ve Martketi ayri tablolar yerine ayri niteliklere ayrilmasi
    ORGANIZATION_CHOICES = [
        ('PRODUCER', 'Producer Farm'),
        ('DISTRIBUTOR', 'Distributor Firm'),
        ('MARKET', 'Retail Market'),
    ]

    name = models.CharField(max_length=200, verbose_name="Organization Name")
    organization_type = models.CharField(max_length=20, choices=ORGANIZATION_CHOICES, verbose_name="Organization Type")
    location = models.CharField(max_length=255, verbose_name="Address")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_organization_type_display()})"
    
    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

# 2_User Table

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'System Manager'),
        ('STAFF', 'Organization Employee'),
        ('VET', 'Veterinary')
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF', verbose_name="User Role")
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name="Related Organization")
    wallet_address = models.CharField(max_length=42, blank=True, null=True, verbose_name="Crypto Wallet Address")

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"
    
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
    producer = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='produced_pallets', verbose_name="Producer")
    current_holder = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='held_pallets', verbose_name="Current Holder")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PRODUCTION', verbose_name="Status")

# Güvenlik ve Kalite Metrikleri
    vet_approval = models.BooleanField(default=False, verbose_name="Vet Approval")
    is_quality_maintained = models.BooleanField(default=True, verbose_name="Quality/Temperature Ensured?")

    departure_date = models.DateTimeField(null=True, blank=True, verbose_name="Departure Date")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pallet: {self.master_qr_id}"

# 4. Paket Varlığı (Unit QR / Tüketici Birimi)
class Package(models.Model):
    FEEDING_TYPE= [
        ('0', "Organik"),
        ('1', 'Gezen Tavuk'),
        ('2', 'Kümes'),
        ('3', 'Kafes')
    ]
    package_qr_id = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="Paket QR")
    pallet = models.ForeignKey(Pallet, on_delete=models.CASCADE, related_name="packages", verbose_name="Related Pallet")
    feeding_type = models.CharField(max_length=20, choices=FEEDING_TYPE, default="Kümes", verbose_name="Beslenme Türü")
    laying_date = models.DateField(verbose_name="Yumurtlama Tarihi")
    expiry_date = models.DateField(verbose_name="TETT")

    def __str__(self):
        return f"Package: {self.package_qr_id}"
    

class BlockchainTransaction(models.Model):

    ACTION_CHOICES = [
        ('PROD', 'Production Record'),
        ('TRAN', 'Transfer/Logistics'),
        ('QUAL', 'Quality Control'),
        ('RECV', 'Market Received'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    pallet = models.ForeignKey(Pallet, on_delete=models.CASCADE, related_name='transactions', verbose_name="Pallet")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="User")
    
    action_type = models.CharField(max_length=4, choices=ACTION_CHOICES, verbose_name="Action Type")
    
    # Ethereum/EVM tabanlı ağlarda hash genelde 66 karakterdir (0x + 64 karakter)
    tx_hash = models.CharField(max_length=66, unique=True, db_index=True, verbose_name="Transaction Hash (TxID)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="Status")
    
    # Blokzincire giden verinin bir kopyası (PostgreSQL JSONField bu iş için mükemmeldir)
    payload = models.JSONField(help_text="Data brief that sended to blockchain", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Time Stamp")

    class Meta:
        ordering = ['-timestamp'] # En yeni işlemler en üstte görünsün
        verbose_name = "Blockchain Transaction"
        verbose_name_plural = "Blockchain Transactions"

    def __str__(self):
        # Admin panelinde çok uzun görünmemesi için hash'in ilk 10 karakterini gösteriyoruz
        return f"{self.get_action_type_display()} - {self.tx_hash[:10]}..."