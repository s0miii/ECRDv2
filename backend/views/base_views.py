from rest_framework import viewsets, status, permissions, filters
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend


# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# Pagination Configuration
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


# ============================================================================
# BASE CLASSES
# ============================================================================

class StandardResultsSetPagination(PageNumberPagination):
    """ 
    Standard Pagination Configuration.
    Implements consistent pagination across all views.
    """
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = MAX_PAGE_SIZE


class BaseModelViewSet(viewsets.ModelViewSet):
    """ 
    Base viewset with common configurations.
    Implements DRY by centralizing common viewset behavior.
    """
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Override to apply user-based filtering.
        Ensures users only see data they have permission to access. 
        """
        queryset = super().get_queryset()
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """ 
        Set creator fields when creating objects.
        Automatically tracks who created each record.
        """
        if hasattr(serializer.instance, 'created_by'):
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    def handle_exception(self, exc):
        """ 
        Centralized exception handling.
        Provides consistent error response format.
        """
        if isinstance(exc, ValueError):
            return Response(
                {'error': 'Validation Error', 'message': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().handle_exception(exc)
