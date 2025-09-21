from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from ..models import UserTypeChoices

from ..serializers import (
    UserBasicInfoSerializer, RegisterSerializer, LoginSerializer
    )


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

class AuthenticationViewSet(viewsets.ViewSet):
    """
    Handle user authentication operations.
    Single responsibility: User authentication workflow.
    """
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def login(self, request):
        """ 
        Authenticate user and return token.
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user': UserBasicInfoSerializer(user).data,
                'permissions': self._get_user_permissions(user)
            })
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """ 
        Register new user account
        """
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user': UserBasicInfoSerializer(user).data,
                'message': 'Registration successful!'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """ 
        Logout user by deleting token.
        """
        try:
            request.user.auth_token.delete()
            return Response({'message': 'Logged out successfully.'})
        except:
            return Response({'error': 'Error logging out!'},
                            status=status.HTTP_400_BAD_REQUEST)
        
    def _get_user_permissions(self, user):
        """ 
        Get user permissions based on user type.
        Private method for permissions mapping.
        """
        permission_map = {
            UserTypeChoices.SYSTEM_ADMIN: ['all'],
            UserTypeChoices.EXTENSION_ADMIN_STAFF: ['manage_projects', 'view_reports'],
            UserTypeChoices.PROJECT_LEADER: ['manage_own_projects', 'submit_reports'],
            UserTypeChoices.PROPONENT: ['create_projects', 'submit_requirements'],
            UserTypeChoices.EXTENSION_COORDINATOR: ['manage_college_projects'],
            UserTypeChoices.DEPARTMENT_HEAD: ['manage_department_projects'],
            UserTypeChoices.COLLEGE_HEAD: ['view_college_reports']
        }
        return permission_map.get(user.user_type, ['view_own_data'])