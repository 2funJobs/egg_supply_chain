from rest_framework import permissions

class IsProducer(permissions.BasePermission):
    """Sadece Üretici (PRODUCER) rolüne sahip olanlar işlem yapabilir."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'FARMER')
    
class IsVet(permissions.BasePermission):
    """Sadece Veteriner (VET) rolüne sahip olanlar işlem yapabilir."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'VET')
    
class IsLogistics(permissions.BasePermission):
    """Sadece Dağıtıcı (DISTRIBUTOR) veya Market (MARKET) rolündekiler işlem yapabilir."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['DISTRIBUTOR', 'CLERK'])