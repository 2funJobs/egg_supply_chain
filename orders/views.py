from django.shortcuts import render
from rest_framework import viewsets
from .models import Organization, Pallet
from .serializers import OrganizationSerializer, PalletSerializer

class OrganizationViewSet(viewsets.ModelViewSet):
    # Kurumlari listeleyen ve olusturan API endpoint
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class PalletViewSet(viewsets.ModelViewSet):
    # Paletleri listeleyen, yeni palet olusturan API endpoint
    queryset = Pallet.objects.all().order_by("-created_at")
    serializer_class = PalletSerializer