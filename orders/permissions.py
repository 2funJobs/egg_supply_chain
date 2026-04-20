from rest_framework import permissions

class IsProducer(permissions.BasePermission):
    """Sadece Üretici (PRODUCER) rolüne sahip olanlar işlem yapabilir."""
    def has_permission(self, request, view):
        # Kullanıcı giriş yapmış mı ve bir kurumu var mı?
        if not (request.user and request.user.is_authenticated and request.user.organization):
            return False
            
        user = request.user
        org_type = user.organization.organization_type
        
        # 1. Kurum yetkisi kontrolü (Bu şirket mal taşıyabilir/alabilir mi?)
        is_valid_org = org_type in ['PRODUCER']
        
        # 2. Rol kontrolü (Bu kişi bu şirkette işlem yapmaya yetkili mi?)
        is_valid_role = user.role in ['CLERK', 'STAFF', 'ADMIN'] 
        
        return is_valid_org and is_valid_role
    
class IsVet(permissions.BasePermission):
    """Sadece Denetçi kurumlara bağlı Veterinerler/Çalışanlar onay verebilir."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.organization):
            return False
            
        # Hem kurum tipi INSPECTOR olmalı, hem de kişinin rolü VET olmalı
        is_inspector_org = request.user.organization.organization_type == 'INSPECTOR'
        is_vet_role = request.user.role == 'VET'
        
        return is_inspector_org and is_vet_role
    
class IsMarketOrLogisticsStaff(permissions.BasePermission):
    """
    KURAL 1: Kullanıcının bağlı olduğu şirket Market veya Lojistik firması MIKURAL 2: İşlemi yapan kişi o şirketin saha çalışanı (CLERK/STAFF) mı?
    """
    def has_permission(self, request, view):
        # Kullanıcı giriş yapmış mı ve bir kurumu var mı?
        if not (request.user and request.user.is_authenticated and request.user.organization):
            return False
            
        user = request.user
        org_type = user.organization.organization_type
        
        # 1. Kurum yetkisi kontrolü (Bu şirket mal taşıyabilir/alabilir mi?)
        is_valid_org = org_type in ['DISTRIBUTOR', 'MARKET']
        
        # 2. Rol kontrolü (Bu kişi bu şirkette işlem yapmaya yetkili mi?)
        is_valid_role = user.role in ['CLERK', 'STAFF', 'ADMIN'] 
        
        return is_valid_org and is_valid_role