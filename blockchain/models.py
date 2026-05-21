from django.db import models

class BlockchainTransaction(models.Model):

    ACTION_CHOICES = [
        ('PROD', 'Production Record'),
        ('TRAN', 'Transfer/Logistics'),
        ('QUAL', 'Quality Control'),
        ('RECV', 'Market Received'),
        ('CERT', 'Certification/Approval')
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    pallet = models.ForeignKey("orders.Pallet", on_delete=models.CASCADE, null=True, blank=True, related_name='transactions', verbose_name="Pallet")
    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, verbose_name="User")
    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, related_name='blockchain_logs', verbose_name="Organization")
    action_type = models.CharField(max_length=4, choices=ACTION_CHOICES, verbose_name="Action Type")
    
    # Ethereum/EVM tabanlı ağlarda hash genelde 66 karakterdir (0x + 64 karakter)
    # Uzunluk 100 yapıldı. null ve blank True yapıldı ki PENDING işlemler hata vermesin.
    tx_hash = models.CharField(max_length=100, unique=True, db_index=True, null=True, blank=True, verbose_name="Transaction Hash (TxID)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="Status")
    
    # Blokzincir ağındaki bloğun numarası (Ağdan Success yanıtı gelince doldurulur)
    block_number = models.PositiveIntegerField(null=True, blank=True, verbose_name="Block Number")

    # Blokzincire giden verinin bir kopyası (PostgreSQL JSONField bu iş için mükemmeldir)
    payload = models.JSONField(help_text="Data brief that sended to blockchain", null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Time Stamp")

    class Meta:
        ordering = ['-timestamp'] # En yeni işlemler en üstte görünsün
        verbose_name = "Blockchain Transaction"
        verbose_name_plural = "Blockchain Transactions"

    def __str__(self):
        # Admin panelinde çok uzun görünmemesi için hash'in ilk 10 karakterini gösteriyoruz
        hash_display = self.tx_hash[:10] + "..." if self.tx_hash else "PENDING..."
        return f"{self.get_action_type_display()} - {hash_display}"
