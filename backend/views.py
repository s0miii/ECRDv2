from django.db.models import Q, Count, Avg, Sum, Prefetch
from django.db import transaction
from django.utils import timezone
from django.http import Http404, FileResponse
from django.core.files.storage import default_storage
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal
import uuid

from .models import (
    CustomUser, College, Department, Project, ProjectMember,
    Trainer, ProjectTrainer, DocumentaryRequirement, File,
    AccomplishmentReport, AttendanceTemplate, AttendanceRecord,
    Evaluation, EvaluationLink, ProjectPerformance, Communication,
    ProjectStatusChoices, UserTypeChoices, RequirementStatusChoices
)

from .serializers import (
    CustomUserSerializer, UserBasicInfoSerializer, UserProfileSerializer,
    RegisterSerializer, LoginSerializer, CollegeSerializer, DepartmentSerializer,
    ProjectSerializer, ProjectDetailSerializer, ProjectCreateSerializer,
    ProjectSummarySerializer, ProjectMemberSerializer, TrainerSerializer,
    ProjectTrainerSerializer, DocumentaryRequirementSerializer, FileSerializer,
    AccomplishmentReportSerializer, AttendanceTemplateSerializer,
    AttendanceRecordSerializer, EvaluationSerializer, EvaluationLinkSerializer,
    ProjectPerformanceSerializer, CommunicationSerializer, ProjectExportSerializer,
    ProjectSearchSerializer, ProjectStatisticsSerializer, BulkOperationSerializer,
    ErrorResponseSerializer
)



# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================


# Pagination Configuration
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

# Bulk Operation Limits
MAX_BULK_OPERATIONS = 100

# File Upload Limits (MB)
MAX_FILE_SIZE_MB = 50
ALLOWED_FILE_TYPES = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt',
    'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov'
]

# Search Configuration
DEFAULT_SEARCH_FIELDS = ['title', 'description']
USER_SEARCH_FIELDS = ['first_name', 'last_name', 'email', 'employee_id']

# Performance Thresholds
EXCELLENT_PERFORMANCE_THRESHOLD = 4.0
GOOD_PERFORMANCE_THRESHOLD = 3.0



# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_file_upload(uploaded_file):
    """
    Validate uploaded file size and type.
    Single responsibility: File validation logic
    """
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit.")
    
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        raise ValueError(f"File type '{file_extension}' is not allowed.")
    
    return True


def get_optimized_project_queryset():
    """ 
    Get optimized queryset for projects with related data.
    Single responsibility: Query optimization.
    """
    return Project.objects.select_related(
        'project_leader', 'college', 'department'
    ).prefetch_related(
        'members__user',
        'trainer_assignments__trainer',
        'files'
    )


def apply_user_filters(queryset, user, user_type=None):
    """ 
    Apply user-based filtering based on permissions.
    Single responsibility: User permission filtering.
    """
    if user.is_superuser:
        return queryset
    
    user_type = user_type or user.user_type

    if user_type == UserTypeChoices.SYSTEM_ADMIN:
        return queryset
    elif user_type == UserTypeChoices.EXTENSION_COORDINATOR:
        return queryset.filter(college=user.college)
    elif user_type == UserTypeChoices.DEPARTMENT_HEAD:
        return queryset.filter(department=user.department)
    elif user_type == UserTypeChoices.PROJECT_LEADER:
        return queryset.filter(
            Q(project_leader=user) | Q(memers__user=user)
        ).distinct()
    else:
        # Regular users see projects they're involved in
        return queryset.filter(members__user=user).distinct()
    


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
    filter_backends = [DjangoFilterBackend. filters.SearchFilter, filters.OrderingFilter]
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




# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

class AuthenticationViewSet(APIView):
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
    
    @action(detail=False, method=['get'])
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



# ============================================================================
# INSTITUTIONAL STRUCTURE VIEWS
# ============================================================================

class CollegeViewSet(BaseModelViewSet):
    """ 
    College management with department relationships.
    Handle college CRUD and nested department data.
    """
    queryset = College.objects.all()
    serializer_class = CollegeSerializer
    search_fields = ['college_name', 'college_code']
    filterset_fields = ['created_at']
    ordering = ['college_code']

    def get_queryset(self):
        """ 
        Optimize with related data and annotations.
        """
        return College.objects.select_related(
            'dean', 'extension_coordinator'
        ).annotate(
            department_count=Count('departments'),
            project_count=Count('projects'),
            user_count=Count('users')
        )
        
    @action(detail=True, methods=['get'])
    def departments(self, request, pk=None):
        """ 
        Get all departments within a college.
        """
        college = self.get_object()
        departments = college.departments.all()
        serializer = DepartmentSerializer(departments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def projects(self, request, pk=None):
        """ 
        Get all projects within a college
        """

        college = self.get_object()
        projects = college.projects.all()
        serializer = ProjectSummarySerializer(projects, many=True)
        return Response(serializer.data)



class DepartmentViewSet(BaseModelViewSet):
    """ 
    Department management within college structure.
    Handles department CRUD with college relationships.
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    search_fields = ['department_name', 'department_code']
    filterset_fields = ['college', 'created_at']
    ordering = ['college__college_code', 'department_code']

    def get_queryset(self):
        """ 
        Optmize with college data and user count.
        """
        return Department.objects.select_related(
            'college', 'department_head'
        ).annotate(
            user_count=Count('users')
        )
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """ 
        Get all users within a department.
        """
        department = self.get_object()
        users = department.users.filter(is_active=True)
        serializer = UserBasicInfoSerializer(users, many=True)
        return Response(serializer.data)

    

# ============================================================================
# PROJECT MANAGEMENT VIEWS
# ============================================================================

class ProjectViewSet(BaseModelViewSet):
    """ 
    Comprehensive project management with nested relationships.
    Implements full project lifecycle management.
    """
    serializer_class = ProjectSerializer
    search_fields = ['title', 'description', 'location']
    filterset_fields = [
        'project_type', 'status', 'college', 'department',
        'project_leader', 'start_date', 'end_date'
    ]
    ordering_fields = ['title', 'start_date', 'end_date', 'budget', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """ 
        Get optimized queryset with user filtering.
        """
        queryset = get_optimized_project_queryset()
        return apply_user_filters(queryset, self.request.user)
    
    def get_serializer_class(self):
        """ 
        Return appropriate serializer based on action
        """
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        elif self.action == 'create':
            return ProjectCreateSerializer
        elif self.action == 'export':
            return ProjectExportSerializer
        return ProjectSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """ 
        Get project summary stats
        """
        queryset = self.get_queryset()

        statistics = {
            'total_projects': queryset.count(),
            'active_projects': queryset.filter(
                status__in=[ProjectStatusChoices.APPROVED, ProjectStatusChoices.ONGOING]
            ).count(),
            'completed_projects': queryset.filter(status=ProjectStatusChoices.COMPLETED).count(),
            'total_budget': queryset.aggregate(Sum('budget'))['budget__sum'] or 0,
            'average_budget': queryset.aggregate(Avg('budget'))['budget__avg'] or 0,
            'projects_by_type': dict(
                queryset.values('project_type').annotate(count=Count('project_id'))
                .values_list('project_type', 'count')
            ),
            'projects_by_status': dict(
                queryset.values('status').annotate(count=Count('project_id'))
                .values_list('status', 'count')
            )
        }


        serializer = ProjectStatisticsSerializer(statistics)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """ 
        Advanced project search with filters.
        """
        serializer = ProjectSearchSerializer(data=request.data)
        if serializer.is_valid():
            queryset = self.get_queryset()

            # Apply search filters
            filters = Q()
            if serializer.validated_data.get('query'):
                query = serializer.validated_data['query']
                filters |= (
                    Q(title__icontains=query) |
                    Q(description__icontains=query) |
                    Q(location__icontains=query)
                )
            
            # Apply additional filters
            for field in ['project_type', 'status', 'college', 'department']:
                value = serializer.validated_data.get(field)
                if value:
                    filters &= Q(**{field: value})
            
            # Apply date range filters
            if serializer.validated_data.get('start_date_from'):
                filters &= Q(start_date__gte=serializer.validated_data['start_date_from'])
            if serializer.validated_data.get('start_date_to'):
                filters &= Q(start_date__lte=serializer.validated_data['start_date_to'])
            
            # Apply budget range filters
            if serializer.validated_data.get('budget_min'):
                filter &= Q(budget__gte=serializer.validated_data['budget_min'])
            if serializer.validated_data.get('budget_max'):
                filters &= Q(budget__lte=serializer.validated_data['budget_max'])
            
            queryset = queryset.filter(filters)

            # Apply ordering
            ordering = serializer.validated_data.get('ordering', '-created_at')
            queryset = queryset.order_by(ordering)

            # Paginate results
            page = self.paginate_queryset(queryset)
            if page is not None:
                project_serializer = ProjectSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(project_serializer.data)

            project_serializer = ProjectSerializer(queryset, many=True, context={'request': request})
            return Response(project_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """ 
        Export projects to various formats.
        """

        




