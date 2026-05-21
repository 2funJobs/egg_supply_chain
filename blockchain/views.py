from django.shortcuts import render
from rest_framework import viewsets
from .models import BlockchainTransaction
from .serializers import BlockchainTransactionSerializer
from django_filters.rest_framework import DjangoFilterBackend

class BlockchainTransactionsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BlockchainTransaction.objects.all()
    serializer_class = BlockchainTransactionSerializer
    
    # 1. WEB3 STANDARDI: Detay aramalarında ID yerine Hash kullanılır
    lookup_field = 'tx_hash'

    # 2. FRONTEND'İN HAYAT KURTARICISI: Filtreleme Mekanizması
    filter_backends = [DjangoFilterBackend]
    
    # Frontend'in URL sonuna soru işareti (?) ile parametre ekleyebileceği alanlar
    filterset_fields = [
        'pallet__master_qr_id',  # Örn: ?pallet__master_qr_id=PAL-123
        'organization__org_code',# Örn: ?organization__org_code=ORG-A101
        'status',                # Örn: ?status=PENDING
        'action_type'            # Örn: ?action_type=TRAN
    ]
