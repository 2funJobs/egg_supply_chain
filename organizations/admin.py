from django.contrib import admin
from .models import InspectionCertificate, Organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('org_code', 'name', 'organization_type', 'location')
    list_filter = ('organization_type',)
    search_fields = ('name',)

@admin.register(InspectionCertificate)
class InspectionCertificateAdmin(admin.ModelAdmin):
    list_display = ('inspector', 'producer')
