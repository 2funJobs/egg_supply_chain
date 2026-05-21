from django.db import models
import uuid
import requests

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_code = models.CharField(max_length=100, unique=True, db_index=True, editable=False, verbose_name="Organization Code")
    name = models.CharField(max_length=200, verbose_name="Organization Name")
    organization_type = models.CharField(max_length=20, choices=ORGANIZATION_CHOICES, verbose_name="Organization Type")
    location = models.CharField(max_length=255, verbose_name="Address")
    created_at = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(verbose_name="enlem", null=True, blank=True)
    longitude = models.FloatField(verbose_name="boylam", null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # 1. Handle org_code generation
        if not self.org_code:
            self.org_code = f"ORG-{uuid.uuid4().hex[:8].upper()}"

        # 2. Determine if geocoding is needed
        needs_geocoding = False
        
        if self._state.adding:
            # This is a brand new record (not in DB yet)
            needs_geocoding = True
        else:
            # Record exists, check if location changed
            try:
                # We use _original_location logic or a simple refresh_from_db style check
                # To be safe and avoid the DoesNotExist error, we use filter().first()
                old_instance = Organization.objects.filter(pk=self.pk).first()
                if old_instance and old_instance.location != self.location:
                    needs_geocoding = True
            except Exception:
                pass

        # 3. Perform the Geocoding
        if needs_geocoding and self.location:
            headers = {'User-Agent': 'EggSupplyChainApp/v1'}
            base_url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': self.location,
                'format': 'json',
                'limit': 1
            }

            try:
                response = requests.get(base_url, params=params, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        self.latitude = float(data[0]['lat'])
                        self.longitude = float(data[0]['lon'])
            except Exception as e:
                print(f"Geocoding API error: {e}")

        # 4. Final Save
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
            return f"{self.name} ({self.get_organization_type_display()})"

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