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
    ReportStatusChoices, LinkTypeChoices, AttendanceStatusChoices,
    EvaluationTypeChoices, EmailTypeChoices, CommunicationStatusChoices,
    ApprovalStatusChoices,

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
    ErrorResponseSerializer, calculate_file_size_mb
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
                filters &= Q(budget__gte=serializer.validated_data['budget_min'])
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

class AttendanceTemplateViewSet(BaseModelViewSet):
    """ 
    Attendance template management for sessions and events.
    Handles creation and management of attendance sheets.
    """
    queryset = AttendanceTemplate.objects.all()
    serializer_class = AttendanceTemplateSerializer
    filterset_fields = ['project', 'session_date', 'is_active', 'created_by']
    ordering = ['-session_date', '-session_time']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters.
        """
        queryset = AttendanceTemplate.objects.select_related(
            'project', 'created_by'
        ).annotate(
            attendance_count=Count('attendance_records')
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """ 
        Set creator on template creation
        """
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def attendance_records(self, request, pk=None):
        """ 
        Get all attendance records for a template
        """
        template = self.get_object()
        records = template.attendance_records.all()

        page = self.paginate_queryset(records)
        if page is not None:
            serializer = AttendanceRecordSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = AttendanceRecordSerializer(
            records, many=True, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def generate_attendance_link(self, request, pk=None):
        """ 
        Generate public link for attendance marking
        """
        template = self.get_object()

        # create evaluation link for attendance
        link = EvaluationLink.objects.create(
            project=template.project,
            link_type=LinkTypeChoices.ATTENDANCE,
            expiration_date=timezone.now() + timezone.timedelta(days=7), # 7 days validity
            created_by=request.user,
            max_usage=template.expected_participants * 2 # allow some buffer
        )

        serializer = EvaluationLinkSerializer(link, context={'request': request})
        return Response({
            'message': 'Attendance link generated successfully!',
            'link': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def deactivate_template(self, request, pk=None):
        """ 
        Deactivate attendance template
        """
        template = self.get_object()
        template.is_active = False
        template.save()

        return Response({'message': 'Attendance template deactivated'})
    

class AttendanceRecordViewSet(BaseModelViewSet):
    """ 
    Individual attendance record management.
    Handles participant check-in/check-out operations.
    """
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ['template', 'status', 'participant_email']
    ordering = ['participant_name']

    def get_queryset(self):
        """ 
        Optimize with template and project data.
        """
        return AttendanceRecord.objects.select_related(
            'template', 'template__project'
        )
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """ 
        Mark participate as checked in.
        """
        record = self.get_object()

        if record.check_in_time:
            return Response(
                {'error': 'Participant already checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record.check_in_time = timezone.now()
        record.status = AttendanceStatusChoices.PRESENT
        record.save()

        return Response({
            'message': 'Check-in successful',
            'check_in_time': record.check_in_time
        })
    
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """ 
        Mark participant as checked out
        """
        record = self.get_object()

        if not record.check_in_time:
            return Response(
                {'error': 'Participant must check in first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if record.check_out_time:
            return Response(
                {'error': 'Participant already checked out'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record.check_out_time = timezone.now()
        record.save()

        return Response({
            'message': 'Check-out successful',
            'check_out_time': record.check_out_time
        })
    
    @action(detail=False, methods=['post'])
    def bulk_mark_attendance(self, request):
        """ 
        Mark attendance for multiple participants at once
        """
        template_id = request.data.get('template_id')
        participants = request.data.get('participants', []) # list of participant emails
        attendance_status = request.data.get('status', AttendanceStatusChoices.PRESENT)

        if not template_id or not participants:
            return Response(
                {'error': 'template_id and participants list are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            template = AttendanceTemplate.objects.get(template_id=template_id)
            updated_count = 0

            with transaction.atomic():
                for participante_email in participants:
                    record, created = AttendanceRecord.objects.get_or_create(
                        template=template,
                        participante_email=participante_email,
                        defaults={
                            'participant_name': participante_email.split('@')[0],
                            'status': attendance_status
                        }
                    )

                    if not created and record.status != attendance_status:
                        record.status = attendance_status
                        if attendance_status == AttendanceStatusChoices.PRESENT:
                            record.check_in_time = timezone.now()
                        record.save()

                    updated_count += 1

            return Response({
                'message': f'Attendance marked for {updated_count} participants',
                'updated_count': updated_count
            })
        except AttendanceTemplate.DoesNotExist:
            return Response(
                {'error': 'Attendance template not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        

class EvaluationViewSet(BaseModelViewSet):
    """ 
    Evaluation management for projects and trainers.
    handles feedback collection and rating systems.
    """
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    filterset_fields = ['project', 'evaluator', 'trainer', 'evaluation_type', 'rating']
    ordering = ['-evaluation_date']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters
        """
        queryset = Evaluation.objects.select_related(
            'project', 'evaluator', 'trainer'
        )
        return apply_user_filters(queryset, self.request.user)
    
    @action(detail=False, methods=['post'])
    def anonymous_evaluation(self, request):
        """ 
        submit anonymous evaluation without authentication
        """
        # allow anonymous access for this specific endpoint
        data = request.data.copy()
        data['is_anonymous'] = True

        serializer = EvaluationSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Anonymous evaluation submitted successfully',
                'evaluation_id': serializer.instance.evaluation_id
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def project_statistics(self, request):
        """ 
        Get evaluation statistics for projects.
        """
        project_id = request.query_params.get('project_id')

        if project_id:
            evaluations = self.get_queryset().filter(project_id=project_id)
        else:
            evaluations = self.get_queryset()

        statistics = {
            'total_evaluations': evaluations.count(),
            'average_rating': evaluations.aggregate(Avg('rating'))['rating__avg'] or 0,
            'rating_distribution': dict(
                evaluations.values('rating').annotate(count=Count('rating'))
                .values_list('rating', 'count')
            ),
            'evaluation_types': dict(
                evaluations.values('evaluation_type').annotate(count=Count('evaluation_type'))
                .values_list('evaluation_type', 'count')
            ),
            'anonymous_count': evaluations.filter(is_anonymous=True).count(),
            'identified_count': evaluations.filter(is_anonymous=False).count()
        }

        return Response(statistics)
    
    @action(detail=False, methods=['get'])
    def trainer_ratings(self, request):
        """ 
        Get trainer evaluation statistics
        """
        trainer_id = request.query_params.get('trainer_id')

        trainer_evaluations = self.get_queryset().filter(
            evaluation_type=EvaluationTypeChoices.TRAINER
        )

        if trainer_id:
            trainer_evaluations = trainer_evaluations.filter(trainer_id=trainer_id)

        trainer_stats = trainer_evaluations.values('trainer__trainer_name').annotate(
            average_rating=Avg('rating'),
            total_evaluation=Count('evaluation_id'),
            excellent_ratings=Count('rating', filter=Q(rating__gte=4)),
            poor_ratings=Count('rating', filter=Q(rating__lte=2))
        ).order_by('-average_rating')

        return Response(list(trainer_stats))
    

class EvaluationLinkViewSet(BaseModelViewSet):
    """ 
    Shareable link management for evaluations and attendance.
    Handles link generation, tracking, and validation.
    """
    queryset = EvaluationLink.objects.all()
    serializer_class = EvaluationLinkSerializer
    filterset_fields = ['project', 'link_type', 'is_active', 'created_by']
    ordering = ['-created_at']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters
        """
        queryset = EvaluationLink.objects.select_related(
            'project', 'created_by'
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """ 
        Set creator and generate unique token on creation
        """
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def validate_token(self, request):
        """
        Validate link token without authentication.
        """
        token = request.query_params.get('token')
        
        if not token:
            return Response(
                {'error': 'Token parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            link = EvaluationLink.objects.get(unique_token=token)
            
            if not link.is_valid:
                error_reasons = []
                if not link.is_active:
                    error_reasons.append('Link is inactive')
                if link.is_expired:
                    error_reasons.append('Link has expired')
                if link.is_usage_exceeded:
                    error_reasons.append('Usage limit exceeded')
                
                return Response({
                    'valid': False,
                    'errors': error_reasons
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'valid': True,
                'link': EvaluationLinkSerializer(link, context={'request': request}).data
            })
            
        except EvaluationLink.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Invalid token'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def increment_usage(self, request, pk=None):
        """
        Increment usage count for a link.
        """
        link = self.get_object()
        
        if not link.is_valid:
            return Response(
                {'error': 'Link is not valid for use'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        link.usage_count += 1
        link.save()
        
        return Response({
            'message': 'Usage count updated',
            'usage_count': link.usage_count,
            'remaining_uses': (link.max_usage - link.usage_count) if link.max_usage else None
        })
    
    @action(detail=True, methods=['post'])
    def extend_expiration(self, request, pk=None):
        """
        Extend link expiration date.
        """
        link = self.get_object()
        days = request.data.get('days', 7)
        
        link.expiration_date = timezone.now() + timezone.timedelta(days=days)
        link.save()
        
        return Response({
            'message': f'Link expiration extended by {days} days',
            'new_expiration': link.expiration_date
        })


# ============================================================================
# COMMUNICATION AND NOTIFICATIONS VIEWS
# ============================================================================

class CommunicationViewSet(BaseModelViewSet):
    """
    Communication management for email notifications and tracking.
    Handles automated and manual communications.
    """
    queryset = Communication.objects.all()
    serializer_class = CommunicationSerializer
    filterset_fields = ['project', 'sender', 'email_type', 'status', 'is_automated']
    ordering = ['-sent_date']
    
    def get_queryset(self):
        """
        Optimize with related data and apply user filters.
        """
        queryset = Communication.objects.select_related(
            'project', 'sender'
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """
        Set sender on communication creation.
        """
        serializer.save(sender=self.request.user)
    
    @action(detail=False, methods=['post'])
    def send_notification(self, request):
        """
        Send notification email to specific recipients.
        """
        project_id = request.data.get('project_id')
        recipients = request.data.get('recipients', [])
        email_type = request.data.get('email_type', EmailTypeChoices.NOTIFICATION)
        subject = request.data.get('subject')
        message = request.data.get('message')
        
        if not recipients or not subject or not message:
            return Response(
                {'error': 'recipients, subject, and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project = None
        if project_id:
            try:
                project = Project.objects.get(project_id=project_id)
            except Project.DoesNotExist:
                return Response(
                    {'error': 'Project not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        communications_created = []
        
        with transaction.atomic():
            for recipient in recipients:
                communication = Communication.objects.create(
                    project=project,
                    sender=request.user,
                    recipient_email=recipient.get('email'),
                    recipient_name=recipient.get('name'),
                    email_type=email_type,
                    subject=subject,
                    message=message,
                    is_automated=False
                )
                communications_created.append(communication)
        
        return Response({
            'message': f'Created {len(communications_created)} communication records',
            'communications': CommunicationSerializer(
                communications_created, many=True, context={'request': request}
            ).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def delivery_statistics(self, request):
        """
        Get email delivery statistics.
        """
        communications = self.get_queryset()
        
        project_id = request.query_params.get('project_id')
        if project_id:
            communications = communications.filter(project_id=project_id)
        
        statistics = {
            'total_sent': communications.count(),
            'delivered': communications.filter(
                status=CommunicationStatusChoices.DELIVERED
            ).count(),
            'failed': communications.filter(
                status=CommunicationStatusChoices.FAILED
            ).count(),
            'pending': communications.filter(
                status=CommunicationStatusChoices.PENDING
            ).count(),
            'read_count': communications.filter(read_at__isnull=False).count(),
            'by_type': dict(
                communications.values('email_type').annotate(count=Count('email_type'))
                .values_list('email_type', 'count')
            ),
            'automated_vs_manual': {
                'automated': communications.filter(is_automated=True).count(),
                'manual': communications.filter(is_automated=False).count()
            }
        }
        
        return Response(statistics)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark communication as read.
        """
        communication = self.get_object()
        communication.mark_as_read()
        
        return Response({
            'message': 'Communication marked as read',
            'read_at': communication.read_at
        })
    
    @action(detail=False, methods=['post'])
    def send_bulk_reminders(self, request):
        """
        Send bulk reminder emails for overdue requirements.
        """
        # Get overdue requirements
        overdue_requirements = DocumentaryRequirement.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=[RequirementStatusChoices.PENDING, RequirementStatusChoices.REVISION_NEEDED]
        ).select_related('assigned_to', 'project')
        
        reminder_count = 0
        
        with transaction.atomic():
            for requirement in overdue_requirements:
                # Check if reminder already sent today
                today_reminders = Communication.objects.filter(
                    recipient_email=requirement.assigned_to.email,
                    email_type=EmailTypeChoices.REMINDER,
                    sent_date__date=timezone.now().date()
                )
                
                if not today_reminders.exists():
                    Communication.objects.create(
                        project=requirement.project,
                        sender=request.user,
                        recipient_email=requirement.assigned_to.email,
                        recipient_name=requirement.assigned_to.get_full_name(),
                        email_type=EmailTypeChoices.REMINDER,
                        subject=f'Reminder: {requirement.requirement_name} is overdue',
                        message=f'The requirement "{requirement.requirement_name}" for project "{requirement.project.title}" was due on {requirement.due_date}. Please submit as soon as possible.',
                        is_automated=True
                    )
                    reminder_count += 1
        
        return Response({
            'message': f'Sent {reminder_count} reminder emails',
            'reminders_sent': reminder_count
        })


# ============================================================================
# DASHBOARD AND ANALYTICS VIEWS
# ============================================================================

class DashboardViewSet(APIView):
    """
    Dashboard analytics and summary data.
    Provides aggregated data for admin and user dashboards.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get dashboard data based on user role and permissions.
        """
        user = request.user
        dashboard_data = {}
        
        # Apply user-based filtering to all queries
        projects = apply_user_filters(Project.objects.all(), user)
        
        # Basic project statistics
        dashboard_data['project_statistics'] = {
            'total_projects': projects.count(),
            'active_projects': projects.filter(
                status__in=[ProjectStatusChoices.APPROVED, ProjectStatusChoices.ONGOING]
            ).count(),
            'completed_projects': projects.filter(
                status=ProjectStatusChoices.COMPLETED
            ).count(),
            'planning_projects': projects.filter(
                status=ProjectStatusChoices.PLANNING
            ).count(),
        }
        
        # Budget statistics
        budget_data = projects.aggregate(
            total_budget=Sum('budget'),
            average_budget=Avg('budget')
        )
        dashboard_data['budget_statistics'] = {
            'total_budget': budget_data['total_budget'] or 0,
            'average_budget': budget_data['average_budget'] or 0
        }
        
        # Recent activities based on user type
        if user.user_type == UserTypeChoices.PROJECT_LEADER:
            dashboard_data['my_projects'] = ProjectSummarySerializer(
                projects.filter(project_leader=user)[:5], many=True
            ).data
            
        elif user.user_type in [UserTypeChoices.EXTENSION_COORDINATOR, UserTypeChoices.DEPARTMENT_HEAD]:
            dashboard_data['department_projects'] = ProjectSummarySerializer(
                projects[:10], many=True
            ).data
        
        # Performance metrics (if user has access)
        if user.user_type in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF,
            UserTypeChoices.EXTENSION_COORDINATOR
        ]:
            performances = ProjectPerformance.objects.filter(
                project__in=projects
            ).aggregate(
                avg_completion=Avg('completion_percentage'),
                avg_impact=Avg('impact_score'),
                total_beneficiaries=Sum('total_beneficiaries')
            )
            
            dashboard_data['performance_metrics'] = {
                'average_completion': performances['avg_completion'] or 0,
                'average_impact_score': performances['avg_impact'] or 0,
                'total_beneficiaries': performances['total_beneficiaries'] or 0
            }
        
        # Pending items that need attention
        dashboard_data['pending_items'] = self._get_pending_items(user, projects)
        
        # Recent communications
        recent_communications = Communication.objects.filter(
            project__in=projects
        ).order_by('-sent_date')[:5]
        
        dashboard_data['recent_communications'] = CommunicationSerializer(
            recent_communications, many=True, context={'request': request}
        ).data
        
        return Response(dashboard_data)
    
    def _get_pending_items(self, user, projects):
        """
        Get items requiring user attention.
        Private method for pending items logic.
        """
        pending_items = {
            'overdue_requirements': 0,
            'pending_reports': 0,
            'pending_evaluations': 0,
            'expiring_links': 0,
            'failed_communications': 0,
            'items_needing_approval': 0
        }

        # Get current date for calculations
        today = timezone.now().date()

        # overdue requirements calculation
        overdue_requirements = DocumentaryRequirement.objects.filter(
            project__in=projects,
            due_date__lt=today,
            status__in=[
                RequirementStatusChoices.PENDING,
                RequirementStatusChoices.REVISION_NEEDED
            ]
        )
        pending_items['overdue_requirements'] = overdue_requirements.count()

        # Pending reports that need review (for coordinators, heads, admins)
        if user.user_type in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.COLLEGE_HEAD,
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            pending_reports = AccomplishmentReport.objects.filter(
                project__in=projects,
                status=ReportStatusChoices.SUBMITTED
            )
            pending_items['pending_reports'] = pending_reports.count()
        
        # Items needing approval (files, requirements) baseed on user role
        if user.user_type in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            #Files pending approval
            pending_files = File.objects.filter(
                project__in=projects,
                approval_status=ApprovalStatusChoices.PENDING
            ).count()

            # Requirements submitted for approval
            pending_req_approvals = DocumentaryRequirement.objects.filter(
                project__in=projects,
                status=RequirementStatusChoices.SUBMITTED
            ).count()

            pending_items['items_needing_approval'] = pending_files + pending_req_approvals

        # Expiring evaluation/attendance links (within next 7 days)
        expiration_threshold = timezone.now() + timezone.timedelta(days=7)
        expiring_links = EvaluationLink.objects.filter(
            project__in=projects,
            is_active=True,
            expiration_date__lte=expiration_threshold,
            expiration_date__gt=timezone.now()
        )
        pending_items['expiring_links'] = expiring_links.count()
        
        # Failed communications that need attention
        failed_communications = Communication.objects.filter(
            project__in=projects,
            status=CommunicationStatusChoices.FAILED,
            sent_date__gte=timezone.now() - timezone.timedelta(days=30)  # Last 30 days
        )
        pending_items['failed_communications'] = failed_communications.count()
        
        # Pending evaluations (for project leaders - check if project ended without evaluations)
        if user.user_type == UserTypeChoices.PROJECT_LEADER:
            completed_projects = projects.filter(
                status=ProjectStatusChoices.COMPLETED,
                project_leader=user
            )
            
            projects_without_evaluations = 0
            for project in completed_projects:
                if not project.evaluations.filter(
                    evaluation_type=EvaluationTypeChoices.PROJECT
                ).exists():
                    projects_without_evaluations += 1
            
            pending_items['pending_evaluations'] = projects_without_evaluations
        
        return pending_items


# ============================================================================
# SYSTEM HEALTH AND MONITORING VIEWS
# ============================================================================

class SystemHealthViewSet(APIView):
    """
    System health monitoring and diagnostics.
    Single responsibility: Provide system status and health metrics.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get comprehensive system health metrics.
        Only accessible to system administrators.
        """
        if request.user.user_type != UserTypeChoices.SYSTEM_ADMIN:
            return Response(
                {'error': 'Insufficient permissions to view system health'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Database connectivity check
        try:
            total_users = CustomUser.objects.count()
            total_projects = Project.objects.count()
            db_status = 'healthy'
        except Exception as e:
            db_status = f'error: {str(e)}'
            total_users = 0
            total_projects = 0
        
        # File storage health check
        storage_status = 'healthy'
        try:
            # Check if we can access file storage
            total_files = File.objects.count()
            total_file_size = File.objects.aggregate(
                total_size=Sum('file_size')
            )['total_size'] or 0
            storage_size_mb = calculate_file_size_mb(total_file_size)
        except Exception as e:
            storage_status = f'error: {str(e)}'
            total_files = 0
            storage_size_mb = 0
        
        # Communication system health
        comm_status = 'healthy'
        failed_communications_count = Communication.objects.filter(
            status=CommunicationStatusChoices.FAILED,
            sent_date__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        if failed_communications_count > 50:  # Threshold for concern
            comm_status = 'warning'
        
        # System performance metrics
        overdue_requirements = DocumentaryRequirement.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=[
                RequirementStatusChoices.PENDING,
                RequirementStatusChoices.REVISION_NEEDED
            ]
        ).count()
        
        pending_approvals = File.objects.filter(
            approval_status=ApprovalStatusChoices.PENDING
        ).count() + DocumentaryRequirement.objects.filter(
            status=RequirementStatusChoices.SUBMITTED
        ).count()
        
        active_links = EvaluationLink.objects.filter(
            is_active=True,
            expiration_date__gt=timezone.now()
        ).count()
        
        health_data = {
            'timestamp': timezone.now(),
            'overall_status': 'healthy' if all([
                db_status == 'healthy',
                storage_status == 'healthy',
                comm_status in ['healthy', 'warning']
            ]) else 'unhealthy',
            'database': {
                'status': db_status,
                'total_users': total_users,
                'total_projects': total_projects,
                'active_users': CustomUser.objects.filter(is_active=True).count()
            },
            'file_storage': {
                'status': storage_status,
                'total_files': total_files,
                'storage_size_mb': storage_size_mb
            },
            'communications': {
                'status': comm_status,
                'failed_last_week': failed_communications_count,
                'total_sent_today': Communication.objects.filter(
                    sent_date__date=timezone.now().date()
                ).count()
            },
            'system_metrics': {
                'overdue_requirements': overdue_requirements,
                'pending_approvals': pending_approvals,
                'active_links': active_links,
                'projects_by_status': dict(
                    Project.objects.values('status').annotate(
                        count=Count('project_id')
                    ).values_list('status', 'count')
                )
            }
        }
        
        return Response(health_data)
    
    @action(detail=False, methods=['post'])
    def cleanup_expired_tokens(self, request):
        """
        Clean up expired evaluation links and tokens.
        System maintenance operation.
        """
        if request.user.user_type != UserTypeChoices.SYSTEM_ADMIN:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Deactivate expired links
        expired_links = EvaluationLink.objects.filter(
            expiration_date__lte=timezone.now(),
            is_active=True
        )
        
        updated_count = expired_links.update(is_active=False)
        
        return Response({
            'message': f'Cleaned up {updated_count} expired links',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def performance_metrics(self, request):
        """
        Get detailed performance and usage metrics.
        """
        if request.user.user_type not in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Date range for metrics (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        
        metrics = {
            'user_activity': {
                'total_users': CustomUser.objects.count(),
                'active_users': CustomUser.objects.filter(
                    last_login__gte=thirty_days_ago
                ).count(),
                'new_users_this_month': CustomUser.objects.filter(
                    date_joined__gte=thirty_days_ago
                ).count()
            },
            'project_activity': {
                'projects_created_this_month': Project.objects.filter(
                    created_at__gte=thirty_days_ago
                ).count(),
                'projects_completed_this_month': Project.objects.filter(
                    status=ProjectStatusChoices.COMPLETED,
                    updated_at__gte=thirty_days_ago
                ).count(),
                'average_project_duration': Project.objects.filter(
                    status=ProjectStatusChoices.COMPLETED
                ).aggregate(
                    avg_duration=Avg('end_date') - Avg('start_date')
                )['avg_duration'] or 0
            },
            'file_activity': {
                'files_uploaded_this_month': File.objects.filter(
                    uploaded_date__gte=thirty_days_ago
                ).count(),
                'total_storage_mb': calculate_file_size_mb(
                    File.objects.aggregate(
                        total_size=Sum('file_size')
                    )['total_size'] or 0
                ),
                'files_by_type': dict(
                    File.objects.values('file_type').annotate(
                        count=Count('file_id')
                    ).values_list('file_type', 'count')
                )
            },
            'communication_metrics': {
                'emails_sent_this_month': Communication.objects.filter(
                    sent_date__gte=thirty_days_ago
                ).count(),
                'delivery_success_rate': self._calculate_delivery_success_rate(
                    thirty_days_ago
                ),
                'communications_by_type': dict(
                    Communication.objects.filter(
                        sent_date__gte=thirty_days_ago
                    ).values('email_type').annotate(
                        count=Count('communication_id')
                    ).values_list('email_type', 'count')
                )
            }
        }
        
        return Response(metrics)
    
    def _calculate_delivery_success_rate(self, since_date):
        """
        Calculate email delivery success rate.
        Private method for performance calculation.
        """
        total_communications = Communication.objects.filter(
            sent_date__gte=since_date
        ).count()
        
        if total_communications == 0:
            return 0
        
        successful_communications = Communication.objects.filter(
            sent_date__gte=since_date,
            status=CommunicationStatusChoices.DELIVERED
        ).count()
        
        return round((successful_communications / total_communications) * 100, 2)


# ============================================================================
# BACKUP AND DATA EXPORT VIEWS  
# ============================================================================

class DataExportViewSet(APIView):
    """
    Data export functionality for backup and reporting.
    Single responsibility: Handle various data export formats.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def export_projects(self, request):
        """
        Export project data in various formats (CSV, Excel, JSON).
        """
        export_format = request.data.get('format', 'csv').lower()
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')
        college_ids = request.data.get('college_ids', [])
        status_filters = request.data.get('status_filters', [])
        
        # Apply user-based filtering
        projects = apply_user_filters(Project.objects.all(), request.user)
        
        # Apply additional filters
        if date_from:
            projects = projects.filter(start_date__gte=date_from)
        if date_to:
            projects = projects.filter(start_date__lte=date_to)
        if college_ids:
            projects = projects.filter(college_id__in=college_ids)
        if status_filters:
            projects = projects.filter(status__in=status_filters)
        
        # Optimize query with related data
        projects = projects.select_related(
            'project_leader', 'college', 'department'
        ).prefetch_related('members__user')
        
        # Serialize data for export
        serializer = ProjectExportSerializer(
            projects, many=True, context={'request': request}
        )
        
        export_data = {
            'export_date': timezone.now(),
            'total_records': projects.count(),
            'filters_applied': {
                'date_from': date_from,
                'date_to': date_to,
                'colleges': college_ids,
                'statuses': status_filters
            },
            'data': serializer.data
        }
        
        return Response(export_data)
    
    @action(detail=False, methods=['post'])
    def export_users(self, request):
        """
        Export user data for administrative purposes.
        """
        # Restrict to admin users only
        if request.user.user_type not in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            return Response(
                {'error': 'Insufficient permissions to export user data'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        export_format = request.data.get('format', 'csv').lower()
        user_types = request.data.get('user_types', [])
        colleges = request.data.get('colleges', [])
        active_only = request.data.get('active_only', True)
        
        users = CustomUser.objects.all()
        
        # Apply filters
        if user_types:
            users = users.filter(user_type__in=user_types)
        if colleges:
            users = users.filter(college_id__in=colleges)
        if active_only:
            users = users.filter(is_active=True)
        
        # Optimize query
        users = users.select_related('college', 'department')
        
        # Serialize data (excluding sensitive information)
        serializer = CustomUserSerializer(
            users, many=True, context={'request': request}
        )
        
        # Remove sensitive fields from export
        safe_data = []
        for user_data in serializer.data:
            safe_user = user_data.copy()
            # Remove any sensitive fields if needed
            safe_data.append(safe_user)
        
        export_data = {
            'export_date': timezone.now(),
            'total_records': users.count(),
            'data': safe_data
        }
        
        return Response(export_data)
    
    @action(detail=False, methods=['get'])
    def export_reports(self, request):
        """
        Export accomplishment reports with filters.
        """
        project_id = request.query_params.get('project_id')
        report_type = request.query_params.get('report_type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Apply user-based filtering to projects first
        user_projects = apply_user_filters(
            Project.objects.all(), request.user
        )
        
        reports = AccomplishmentReport.objects.filter(
            project__in=user_projects
        )
        
        # Apply additional filters
        if project_id:
            reports = reports.filter(project_id=project_id)
        if report_type:
            reports = reports.filter(report_type=report_type)
        if date_from:
            reports = reports.filter(submission_date__gte=date_from)
        if date_to:
            reports = reports.filter(submission_date__lte=date_to)
        
        # Optimize query
        reports = reports.select_related(
            'project', 'submitted_by', 'reviewed_by'
        ).order_by('-submission_date')
        
        serializer = AccomplishmentReportSerializer(
            reports, many=True, context={'request': request}
        )
        
        export_data = {
            'export_date': timezone.now(),
            'total_records': reports.count(),
            'data': serializer.data
        }
        
        return Response(export_data)


# ============================================================================
# NOTIFICATION MANAGEMENT VIEWS
# ============================================================================

class NotificationViewSet(APIView):
    """
    Notification management and delivery system.
    Single responsibility: Handle system notifications and alerts.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get notifications for the current user.
        """
        # Get user's notifications (communications sent to them)
        user_notifications = Communication.objects.filter(
            recipient_email=request.user.email
        ).order_by('-sent_date')[:50]  # Limit to recent 50
        
        # Get system-wide notifications based on user role
        system_notifications = self._get_system_notifications(request.user)
        
        serializer = CommunicationSerializer(
            user_notifications, many=True, context={'request': request}
        )
        
        notification_data = {
            'user_notifications': serializer.data,
            'system_notifications': system_notifications,
            'unread_count': user_notifications.filter(read_at__isnull=True).count()
        }
        
        return Response(notification_data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all user notifications as read.
        """
        updated_count = Communication.objects.filter(
            recipient_email=request.user.email,
            read_at__isnull=True
        ).update(read_at=timezone.now())
        
        return Response({
            'message': f'Marked {updated_count} notifications as read',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def send_system_alert(self, request):
        """
        Send system-wide alert (admin only).
        """
        if request.user.user_type not in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message = request.data.get('message')
        subject = request.data.get('subject', 'System Alert')
        recipient_types = request.data.get('recipient_types', [])
        
        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get recipients based on user types
        recipients = CustomUser.objects.filter(is_active=True)
        if recipient_types:
            recipients = recipients.filter(user_type__in=recipient_types)
        
        # Create communications for all recipients
        communications_created = []
        with transaction.atomic():
            for recipient in recipients:
                communication = Communication.objects.create(
                    sender=request.user,
                    recipient_email=recipient.email,
                    recipient_name=recipient.get_full_name(),
                    email_type=EmailTypeChoices.NOTIFICATION,
                    subject=subject,
                    message=message,
                    is_automated=False
                )
                communications_created.append(communication)
        
        return Response({
            'message': f'System alert sent to {len(communications_created)} users',
            'recipients_count': len(communications_created)
        }, status=status.HTTP_201_CREATED)
    
    def _get_system_notifications(self, user):
        """
        Get system notifications based on user role.
        Private method for role-based system notifications.
        """
        notifications = []
        
        # Apply user filtering to get relevant projects
        user_projects = apply_user_filters(Project.objects.all(), user)
        
        # Overdue requirements notification
        overdue_count = DocumentaryRequirement.objects.filter(
            project__in=user_projects,
            due_date__lt=timezone.now().date(),
            status__in=[
                RequirementStatusChoices.PENDING,
                RequirementStatusChoices.REVISION_NEEDED
            ]
        ).count()
        
        if overdue_count > 0:
            notifications.append({
                'type': 'warning',
                'title': 'Overdue Requirements',
                'message': f'You have {overdue_count} overdue requirements',
                'action_url': '/requirements?filter=overdue'
            })
        
        # Pending approvals (for coordinators and heads)
        if user.user_type in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.SYSTEM_ADMIN
        ]:
            pending_reports = AccomplishmentReport.objects.filter(
                project__in=user_projects,
                status=ReportStatusChoices.SUBMITTED
            ).count()
            
            if pending_reports > 0:
                notifications.append({
                    'type': 'info',
                    'title': 'Pending Report Reviews',
                    'message': f'{pending_reports} reports awaiting your review',
                    'action_url': '/reports?filter=pending'
                })
        
        # Project deadlines approaching (next 7 days)
        upcoming_deadlines = user_projects.filter(
            end_date__lte=timezone.now().date() + timezone.timedelta(days=7),
            end_date__gt=timezone.now().date(),
            status__in=[ProjectStatusChoices.APPROVED, ProjectStatusChoices.ONGOING]
        ).count()
        
        if upcoming_deadlines > 0:
            notifications.append({
                'type': 'warning',
                'title': 'Upcoming Project Deadlines',
                'message': f'{upcoming_deadlines} projects ending within 7 days',
                'action_url': '/projects?filter=ending_soon'
            })
        
        return notifications






