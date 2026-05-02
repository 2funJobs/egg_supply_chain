"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import CustomTokenObtainPairView
from orders.views import PalletViewSet, PackageViewSet
from organizations.views import OrganizationViewSet, CertificateViewSet
from blockchain.views import BlockchainTransactionsViewSet
# Uygulamadaki viewleri route etmek icin kullan
from orders.views import OrganizationViewSet, PalletViewSet

# Otomatik URL routing icin Router tanimlanir.
# Uç noktaları (endpoints) kaydediyoruz
router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'pallets', PalletViewSet, basename='pallet')
router.register(r'packages', PackageViewSet, basename='package')
router.register(r'blockchain-logs', BlockchainTransactionsViewSet, basename='blockchain-log')

urlpatterns = [
    # Admin endpoints
    path('admin/', admin.site.urls),
    
    # Authentication endpoints
    path("api/v1/auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Workflow endpoints
    path("api/v1/", include(router.urls)),
]
