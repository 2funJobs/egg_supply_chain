from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # JWT Payload'una ekstra verilerimizi (Kurum/Rol) ekliyoruz
        if hasattr(user, 'organization') and user.organization:
            token['org_code'] = user.organization.org_code
            token['org_name'] = user.organization.name
            token['role'] = user.organization.organization_type

        return token