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
    ProjectStatusChoices, UserTypeChoices, RequirementStatusChoices,
    ReportStatusChoices,
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
        queryset = self.get_queryset()
        serializer = ProjectExportSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """ 
        Change project status with validation
        """
        project = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')

        if not new_status:
            return Response({'error': 'Status is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in dict(ProjectStatusChoices.choices):
            return Response({'error': 'Invalid status.'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Validate status transition (add business logic as neeeded)
        old_status = project.status
        project.status = new_status
        project.save()

        # Log status change (implement audit trail as needed)

        return Response({
            'message': f'Project status changed from {old_status} to {new_status}',
            'project': ProjectSerializer(project, context={'request': request}).data
        })
    
    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """ 
        Perform bulk operations on multiple projects
        """
        serializer = BulkOperationSerializer(data=request.data)
        if serializer.is_valid():
            ids = serializer.validated_data['ids']
            action = serializer.validated_data['action']
            reason = serializer.validated_data.get('reason', '')

            if len(ids) > MAX_BULK_OPERATIONS:
                return Response({
                    'error': f'Cannot perform bulk operations on more than {MAX_BULK_OPERATIONS} items'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            projects = self.get_queryset().filter(project_id__in=ids)
            updated_count = 0

            with transaction.atomic():
                if action == 'activate':
                    updated_count = projects.update(status=ProjectStatusChoices.APPROVED)
                elif action == 'deactivate':
                    updated_count = projects.update(status=ProjectStatusChoices.SUSPENDED)
                elif action == 'delete':
                    updated_count = projects.count()
                    projects.delete()
            
            return Response({
                'message': f'Bulk {action} completed on {updated_count} projects',
                'updated_count': updated_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ProjectMemberViewSet(BaseModelViewSet):
    """ 
    Project team member management.
    Handles project membership assignments and roles.
    """
    queryset = ProjectMember.objects.all()
    serializer_class = ProjectMemberSerializer
    filterset_fields = ['project', 'user', 'role', 'is_active']
    ordering = ['project', 'role', 'assigned_date']

    def get_queryset(self):
        """ 
        Optimize with related user and project data
        """
        return ProjectMember.objects.select_related(
            'user', 'project'
        )
    
    @action(detail=False, methods=['post'])
    def assign_member(self, request):
        """ 
        Assign user to project with role validation.
        """
        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'MEMBER')

        try:
            project = Project.objects.get(project_id=project_id)
            user = CustomUser.objects.get(user_id=user_id)

            # Check if membership already exists
            if ProjectMember.objects.filter(project=project, user=user).exists():
                return Response({'error': 'User is already a member of this project.'},
                                status=status.HTTP_400_BAD_REQUEST)
            
            member = ProjectMember.objects.create(
                project=project,
                user=user,
                role=role
            )

            serializer = ProjectMemberSerializer(member, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Project.DoesNotExist:
            return Response({'error': 'Project not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """ 
        Remove member from project.
        """
        member = self.get_object()
        member.is_active = False
        member.save()

        return Response({'message': 'Member removed from the project successfully!'})



# ============================================================================
# TRAINER MANAGEMENT VIEWS
# ============================================================================

class TrainerViewSet(BaseModelViewSet):
    """
    Trainer management for internal and external trainers.
    Handles trainer profiles and assignment tracking.
    """
    queryset = Trainer.objects.all()
    serializer_class = TrainerSerializer
    search_fields = ['trainer_name', 'email', 'expertise']
    filterset_fields = ['is_internal', 'created_at']
    ordering = ['trainer_name']
    
    def get_queryset(self):
        """
        Annotate with assignment count.
        """
        return Trainer.objects.annotate(
            assignment_count=Count('project_assignments')
        )
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get trainers available for assignment.
        """
        trainers = self.get_queryset().filter(is_internal=True)  # or other availability logic
        serializer = TrainerSerializer(trainers, many=True, context={'request': request})
        return Response(serializer.data)


class ProjectTrainerViewSet(BaseModelViewSet):
    """
    Project trainer assignment management.
    Handles trainer scheduling and tracking.
    """
    queryset = ProjectTrainer.objects.all()
    serializer_class = ProjectTrainerSerializer
    filterset_fields = ['project', 'trainer', 'status', 'training_date']
    ordering = ['-training_date']
    
    def get_queryset(self):
        """
        Optimize with trainer and project data.
        """
        return ProjectTrainer.objects.select_related(
            'trainer', 'project'
        )



# ============================================================================
# REQUIREMENTS AND FILE MANAGEMENT VIEWS
# ============================================================================

class DocumentaryRequirementViewSet(BaseModelViewSet):
    """ 
    Documentary requirement management with approval workflow.
    Handles requirement assignments and tracking.
    """
    queryset = DocumentaryRequirement.objects.all()
    serializer_class = DocumentaryRequirementSerializer
    filterset_fields = ['project', 'status', 'assigned_to', 'due_date']
    ordering = ['due_date', 'requirement_name']

    def get_queryset(self):
        """
        Optimize with related user and project data.
        """
        return DocumentaryRequirement.objects.select_related(
            'project', 'assigned_by', 'assigned_to', 'approved_by'
        )
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """ 
        Submit requirements for approval.
        """
        requirement = self.get_object()
        requirement.status = RequirementStatusChoices.SUBMITTED
        requirement.submitted_date = timezone.now()
        requirement.save()

        return Response({'message': 'Requirement submitted for approval'})
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """ 
        Approve submitted requirement.
        """
        requirement = self.get_object()
        requirement.status = RequirementStatusChoices.APPROVED
        requirement.approved_by = request.user
        requirement.approval_date = timezone.now()
        requirement.save()

        return Response({'message': 'Requirement approved.'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """ 
        Reject submitted requirement with reason
        """
        requirement = self.get_object()
        reason = request.data.get('reason')

        requirement.status = RequirementStatusChoices.REJECTED
        requirement.rejection_reason = reason
        requirement.save()

        return Response({'message': 'Requirement rejected'})



class FileViewSet(BaseModelViewSet):
    """ 
    File management with upload handling and approval workflow.
    Implements secure file upload and management.
    """
    queryset = File.objects.all()
    serializer_class = FileSerializer
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ['project', 'requirement', 'file_type', 'approval_status']
    ordering = ['-uploaded_date']

    def get_queryset(self):
        """ 
        Optimize with related data.
        """
        return File.objects.select_related(
            'project', 'requirement', 'uploaded_by', 'approved_by'
        )
    
    def create(self, request, *args, **kwargs):
        """ 
        Handle file upload with validation
        """
        try:
            uploaded_file = request.FILES.get('file_path')
            if not uploaded_file:
                return Response({'error': 'No file provided'},
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file
            validate_file_upload(uploaded_file)

            # set file metadata
            request.data['file_name'] = uploaded_file.name
            request.data['file_size'] = uploaded_file.size
            request.data['uploaded_by'] = request.user.user_id

            # Determine file type based on extension
            file_extension = uploaded_file.name.split('.')[-1].lower()
            file_type_map = {
                'pdf': 'DOCUMENT',
                'doc': 'DOCUMENT', 'docx': 'DOCUMENT',
                'xls': 'SPREADSHEET', 'xlsx': 'SPREADSHEET',
                'ppt': 'PRESENTATION', 'pptx': 'PRESENTATION',
                'jpg': 'IMAGE', 'jpeg': 'IMAGE', 'png': 'IMAGE', 'gif': 'IMAGE',
                'mp4': 'VIDEO', 'avi': 'VIDEO', 'mov': 'VIDEO'
            }
            request.data['file_type'] = file_type_map.get(file_extension, 'OTHER')

            return super().create(request, *args, **kwargs)
        
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """ 
        Download file with permission check.
        """
        file_obj = self.get_object()

        # Check permissions (implement as needed)
        if not file_obj.file_path:
            return Response({'error': 'File not found'},
                            status=status.HTTP_404_NOT_FOUND)
        
        return FileResponse(
            file_obj.file_path.open('rb'),
            as_attachment=True,
            filename=file_obj.file_name
        )



# ============================================================================
# REPORTING AND MONITORING VIEWS
# ============================================================================
        

class AccomplishmentReportViewSet(BaseModelViewSet):
    """ 
    Accomplishment report management with review workflow.
    Handles report, submission, review, and approval processes.
    """
    queryset = AccomplishmentReport.objects.all()
    serializer_class = AccomplishmentReportSerializer
    filterset_fields = ['project', 'report_type', 'status', 'submitted_by']
    ordering = ['-submission_date']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters.
        """
        queryset = AccomplishmentReport.objects.select_related(
            'project', 'submitted_by', 'reviewed_by'
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """ 
        Set submitter and submission date on creation
        """
        serializer.save(submitted_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        """ 
        Submit report for review by changing status.
        """
        report = self.get_object()

        if report.status != ReportStatusChoices.DRAFT:
            return Response(
                {'error': 'Only draft reports can be submitted for review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = ReportStatusChoices.SUBMITTED
        report.save()

        return Response({
            'message': 'Report submitted for review successfully',
            'report': AccomplishmentReportSerializer(report, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def approve_report(self, request, pk=None):
        """ 
        Approve submitted report.
        """
        report = self.get_object()
        comments = request.data.get('review_comments', '')

        if report.status != ReportStatusChoices.SUBMITTED:
            return Response(
                {'error': 'Only submitted reports can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = ReportStatusChoices.APPROVED
        report.reviewed_by = request.user
        report.review_date = timezone.now()
        report.review_comments = comments
        report.save()

        return Response({
            'message': 'Report approved successfully',
            'report': AccomplishmentReportSerializer(report, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        """ 
        Request revision on submitted report.
        """
        report = self.get_object()
        comments = request.data.get('review_comments')

        if not comments:
            return Response(
                {'error': 'Review comments are required when requesting revision'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if report.status != ReportStatusChoices.SUBMITTED:
            return Response(
                {'error': 'Only submitted reports can be sent for revision'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = ReportStatusChoices.REVISION_NEEDED
        report.reviewed_by = request.user
        report.review_date = timezone.now()
        report.review_comments = comments
        report.save()

        return Response({
            'message': 'Revision requested successfully',
            'report': AccomplishmentReportSerializer(report, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def pending_reviews(self, request):
        """ 
        Get reports pending review for current user.
        """
        if request.user.user_type not in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.COLLEGE_HEAD,
            UserTypeChoices.SYSTEM_ADMIN
        ]:
            return Response(
                {'error': 'Insufficient permissions to review reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_reports = self.get_queryset().filter(
            status=ReportStatusChoices.SUBMITTED
        )

        page = self.paginate_queryset(pending_reports)
        if page is not None:
            serializer = AccomplishmentReportSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = AccomplishmentReportSerializer(
            pending_reports, many=True, context={'request': request}
        )
        return Response(serializer.data)
    

class ProjectPerformanceViewSet(BaseModelViewSet):
    """ 
    Project performance metrics management.
    Handles performance tracking and scoring
    """
    queryset = ProjectPerformance.objects.all()
    serializer_class = ProjectPerformanceSerializer
    filterset_fields = ['project', 'updated_by']
    ordering = ['-last_updated']

    def get_queryset(self):
        """ 
        Optimize with project data and apply user filters.
        """
        queryset = ProjectPerformance.objects.select_related(
            'project', 'updated_by'
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_update(self, serializer):
        """ 
        Set updated_by on performance updates
        """
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'])
    def dashboard_metrics(self, request):
        """ 
        Get aggregated performance metrics for dashboard.
        """
        performances = self.get_queryset()

        metrics = {
            'total_projects': performances.count(),
            'excellent_performance': performances.filter(
                impact_score__gte=EXCELLENT_PERFORMANCE_THRESHOLD,
                sustainability_rating__gte=EXCELLENT_PERFORMANCE_THRESHOLD
            ).count(),
            'good_performance': performances.filter(
                impact_score__gte=GOOD_PERFORMANCE_THRESHOLD,
                impact_score__lt=EXCELLENT_PERFORMANCE_THRESHOLD
            ).count(),
            'average_completion': performances.aggregate(
                Avg('completion_percentage')
            )['completion_percentage__avg'] or 0,
            'average_budget_utilization': performances.aggregate(
                Avg('budget_utilization')
            )['budget_utilization__avg'] or 0,
            'total_beneficiaries': performances.aggregate(
                Sum('total_beneficiaries')
            )['total_beneficiaries__sum'] or 0,
            'average_impact_score': performances.aggregate(
                Avg('impact_score')
            )['impact_score__avg'] or 0
        }

        return Response(metrics)

    @action(detail=True, methods=['post'])
    def update_metrics(self, request, pk=None):
        """ 
        Update specific performance metrics.
        """
        performance = self.get_object()

        allowed_fields = [
            'total_beneficiaries', 'completion_percentage',
            'budget_utilization', 'impact_score', 'sustainability_rating'
        ]

        updated_fields = []
        for field in allowed_fields:
            if field in request.data:
                setattr(performance, field, request.data[field])
                updated_fields.append(field)

        if updated_fields:
            performance.updated_by = request.user
            performance.save()

            return Response({
                'message': f'Updated metrics: {",".join(updated_fields)}',
                'performance': ProjectPerformanceSerializer(
                    performance, context={'request': request}
                ).data
            })
        
        return Response(
            {'error': 'No valid metrics provided for update'},
            status=status.HTTP_400_BAD_REQUEST
        )
    


# ============================================================================
# ATTENDANCE AND EVALUATION VIEWS
# ============================================================================










