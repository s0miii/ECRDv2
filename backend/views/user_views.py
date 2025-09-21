from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import CustomUser

from ..serializers import (
    CustomUserSerializer, UserBasicInfoSerializer, UserProfileSerializer,
)

from .base_views import BaseModelViewSet



# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# Search Configuration
DEFAULT_SEARCH_FIELDS = ['title', 'description']
USER_SEARCH_FIELDS = ['first_name', 'last_name', 'email', 'employee_id']


# ============================================================================
# USER MANAGEMENT VIEWS
# ============================================================================

class CustomUserViewSet(BaseModelViewSet):
    """ 
    Comprehensive user management with role-based access.
    Implements user CRUD with proper permission controls.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    search_fields = USER_SEARCH_FIELDS
    filterset_fields = ['user_type', 'is_active', 'college', 'department']
    ordering_fields = ['first_name', 'last_name', 'date_joined']
    ordering = ['first_name', 'last_name']

    def get_serializer_class(self):
        """ 
        Return appropriate serializer based on action.
        Implements action-specific serializer selection.
        """
        if self.action == 'profile':
            return UserProfileSerializer
        elif self.action in ['list', 'retrieve']:
            return CustomUserSerializer
        return CustomUserSerializer
    
    def get_queryset(self):
        """ 
        Optimize queryset with related data.
        """
        return CustomUser.objects.select_related(
            'college', 'department'
        ).prefetch_related(
            'led_projects', 'project_memberships'
        )

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """ 
        Get current user's profile with detailed information.
        """
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """ 
        Activate user account.
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'message': 'User activated successfully!'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """ 
        Deactivate user account
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'message': 'User deactivated successfully!'})
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """ 
        Get users filtered by role type
        """
        user_type = request.query_params.get('user_type')
        if not user_type:
            return Response({'error': 'user_type parameter required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        users = self.get_queryset().filter(user_type=user_type, is_active=True)
        serializer = UserBasicInfoSerializer(users, many=True)
        return Response(serializer.data)