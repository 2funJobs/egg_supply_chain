from django.db import models

# Organization tablosu
class Organization(models.Model):
    # Uretici, Dagitici ve Martketi ayri tablolar yerine ayri niteliklere ayrilmasi
    ORGANIZATION_CHOICES = [
        ('PRODUCER', 'Producer Farm'),
        ('DISTRIBUTOR', 'Distributor Firm'),
        ('MARKET', 'Retail Market'),
        ('INSPECTOR', 'Inspection & Veterinary Agency')
    ]

    # Her siparişin ayrı ayrı veteriner kontrolünden geçmesi tedarik süreci için pek uygun değil.
    # Bunun yerine işletmeye belirli süre boyunca geçerli kontrol sertifikası verilmesi daha makul görüldü.
    # Bu sebeple INSPECTOR adında denetim organizasyonu oluşturuldu.

    org_code = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Organization Code")
    name = models.CharField(max_length=200, verbose_name="Organization Name")
    organization_type = models.CharField(max_length=20, choices=ORGANIZATION_CHOICES, verbose_name="Organization Type")
    location = models.CharField(max_length=255, verbose_name="Address")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_organization_type_display()})"
    
    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

class InspectionCertificate(models.Model):
    inspector = models.ForeignKey(
        Organization, 
        limit_choices_to={'organization_type': 'INSPECTOR'}, 
        on_delete=models.CASCADE,
        related_name='given_certificates'  # Verdiği sertifikalar
    )
    
    producer = models.ForeignKey(
        Organization, 
        limit_choices_to={'organization_type': 'PRODUCER'}, 
        on_delete=models.CASCADE,
        related_name='received_certificates' # Aldığı sertifikalar
    )

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    certificate_no = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Sertifika: {self.certificate_no} - {self.producer.name}"