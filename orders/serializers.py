from rest_framework import serializers
from .models import Pallet, Package, MarketOrder, MarketOrderItem
from organizations.serializers import OrganizationSerializer
from organizations.models import Organization
class PalletSerializer(serializers.ModelSerializer):
    producer_detail = OrganizationSerializer(source="producer", read_only=True)
    current_holder_detail = OrganizationSerializer(source="current_holder", read_only=True)

    producer = serializers.SlugRelatedField(slug_field='org_code', read_only=True)
    current_holder = serializers.SlugRelatedField(slug_field='org_code', read_only=True)
    destination_market = serializers.SlugRelatedField(
        slug_field='org_code',
        queryset=Organization.objects.filter(organization_type='MARKET'),
        required=False,
        allow_null=True
    )
    destination_market_detail = OrganizationSerializer(
        source='destination_market',
        read_only=True
    )

    class Meta:
        model = Pallet
        fields = [
            'master_qr_id', 'producer', 'producer_detail', 
            'current_holder', 'current_holder_detail', 
            'status', 'vet_approval', 'is_quality_maintained', 
            'departure_date', 'created_at','destination_market',
            'destination_market_detail',
        ]
        
        # Bu alanları read_only yaparsak, DRF artık POST isteğinde bu verileri kullanıcıdan beklemez.
        read_only_fields = ['producer', 'current_holder', 'departure_date', 'status', 'vet_approval', 'is_quality_maintained']

# Blockchain loglarini gostermek icin kullanilan serializer tanimidir.

class PackageSerializer(serializers.ModelSerializer):

    pallet = serializers.SlugRelatedField(
        slug_field='master_qr_id',
        queryset=Pallet.objects.all()
    )

    # pallet_detail = PalletSerializer(source="pallet", read_only=True)
    class Meta:
        model = Package
        fields = ["package_qr_id", "pallet", "feeding_type", "laying_date", "expiry_date", "capacity"]


class MarketOrderItemSerializer(serializers.ModelSerializer):
    # 'get_FOO_display' is a built-in Django trick for fields with 'choices'.
    # This automatically translates the database integer (e.g., 0) into 
    # the human-readable string (e.g., "Organik") for your frontend UI.
    feeding_type_display = serializers.CharField(source='get_feeding_type_display', read_only=True)
    capacity_display = serializers.CharField(source='get_capacity_display', read_only=True)

    class Meta:
        model = MarketOrderItem
        fields = [
            'id', 
            'order', 
            'feeding_type', 
            'feeding_type_display', 
            'capacity', 
            'capacity_display', 
            'package_quantity'
        ]

class MarketOrderSerializer(serializers.ModelSerializer):
    # NESTED RELATIONSHIP: This is the magic line. 
    # Because you set related_name="items" in the MarketOrderItem model,
    # DRF will automatically fetch all linked items and serialize them into a list here.
    items = MarketOrderItemSerializer(many=True, read_only=True)

    # Read-only details for the frontend UI (names instead of just UUIDs/IDs)
    market_detail = OrganizationSerializer(source="market", read_only=True)
    assigned_producer_detail = OrganizationSerializer(source="assigned_producer", read_only=True)
    fulfilled_pallet_detail = PalletSerializer(source="fulfilled_pallet", read_only=True)

    class Meta:
        model = MarketOrder
        fields = [
            'id', 
            'market', 
            'market_detail', 
            'assigned_producer', 
            'assigned_producer_detail',
            'fulfilled_pallet', 
            'fulfilled_pallet_detail', 
            'status', 
            'created_at',
            'items' # The nested cart items array
        ]
        
        # We lock these fields down because the frontend should NEVER send them.
        # They are strictly controlled by your routing (CheckoutCartView) 
        # and fulfillment (AcceptMarketOrderView) backend logic.
        read_only_fields = ['assigned_producer', 'fulfilled_pallet', 'status']