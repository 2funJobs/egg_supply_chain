from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    """
    E-posta ile giriş yapmak için gereken özel yönetici (Manager).
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Kullanıcıların bir e-posta adresi olmalıdır.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser is_staff=True olmalıdır.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser is_superuser=True olmalıdır.')

        return self.create_user(email, password, **extra_fields)\
        
class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'System Manager'),
        ('ORG_ADMIN', 'Organization Manager'),
        ('STAFF', 'Staff'),
        ('VET', 'Veterinary'),
    ]

    username = None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('e-posta adresi', unique=True)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='STAFF', verbose_name="User Role")
    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name="Related Organization")
    wallet_address = models.CharField(max_length=42, unique=True, blank=True, null=True, verbose_name="Crypto Wallet Address")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # 4. ÖZEL MANAGER'I BAĞLIYORUZ
    objects = CustomUserManager()

    def __str__(self):
        # self.username yerine self.email kullandık
        org_name = self.organization.name if self.organization else "Bağımsız / Kurumsuz"
        return f"{self.email} ({self.get_role_display()}) - {org_name}"
    