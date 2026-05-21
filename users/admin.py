from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
User = get_user_model()

# 1. ÖZEL KULLANICI EKLEME FORMU
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        # Yeni kullanıcı eklerken admin panelde zorunlu sorulacak alanlar
        fields = ('email', 'role', 'organization', 'wallet_address')

# 2. ÖZEL KULLANICI DÜZENLEME FORMU
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'role', 'organization', 'wallet_address')

# 3. YENİ ADMIN SINIFIMIZ
class CustomUserAdmin(UserAdmin):
    # Formları admin panelimize bağlıyoruz
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    list_display = ('email', 'role', 'organization', 'is_staff', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('email',)

    # Şifreyi form üzerinden güvenli hashleyeceği için artık sadece yetkileri gösteriyoruz
    fieldsets = (
        ('Kişisel Bilgiler', {'fields': ('email', 'password')}),
        ('Kurumsal Yetkiler', {'fields': ('role', 'organization', 'wallet_address')}),
        ('Sistem İzinleri', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Önemli Tarihler', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            # Şifre alanları (password1 ve password2) CustomUserCreationForm tarafından otomatik eklenecek
            'fields': ('email', 'role', 'password1', 'password2', 'organization', 'wallet_address')
        }),
    )

admin.site.register(User, CustomUserAdmin)
