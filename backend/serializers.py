from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import (
    CustomUser, College, Department, Project, ProjectMember,
    Trainer, ProjectTrainer, DocumentaryRequirement, File,
    AccomplishmentReport, AttendanceTemplate, AttendanceRecord,
    Evaluation, EvaluationLink, ProjectPerformance, Communication,
    UserTypeChoices, ProjectStatusChoices, RequirementStatusChoices
)


# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================


# Error Messages - Centralized for consistency
ERROR_MESSAGES = {
    'invalid_credentials': 'Invalid email or password.',
    'user_inactive': 'User account is inactive.',
    'weak_password': 'Password does not meet security requirements.',
    'email_required': 'Email address is required.',
    'duplicate_email': 'A user with this email already exists.',
    'invalid_date_range': 'End date must be after start date.',
    'invalid_budget': 'Budget must be a positive amount.',
    'file_too_large': 'File size exceeds maximum allowed limit.',
    'invalid_rating': 'Rating must be between 1 and 5.',
    'link_expired': 'This link has already expired.',
    'usage_exceeded': 'Usage limit for this link has been exceeded.'
}

# Validation Constants
MAX_FILE_SIZE_MB = 50
MIN_PROJECT_DURATION_DAYS = 1
MAX_PROJECT_DURATION_DAYS = 1825 # 5 years
MIN_RATING = 1
MAX_RATING = 5
BYTES_TO_MB = 1024 * 1024



# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def validate_date_range(start_date, end_date):
    """ 
    Validate that end date is after start date.
    Single responsibility: Date range validation.
    """
    if end_date < start_date:
        raise serializers.ValidationError(ERROR_MESSAGES['invalid_date_range'])
    


def validate_positive_amount(amount, field_name='amount'):
    """ 
    Validate that amount is positive.
    Single Responsibility: Positive number validation.
    """
    if amount < 0:
        raise serializers.ValidationError(
            f'{field_name.title()} must be a positive amount.'
        )
    


def calculate_file_size_mb(size_bytes):
    """ 
    Convert bytes to megabytes.
    Single responsibility: File size conversion
    """
    return round(size_bytes / BYTES_TO_MB, 2)



# ============================================================================
# BASE SERIALIZER CLASSES
# ============================================================================

class TimestampedModelSerializer(serializers.ModelSerializer):
    """ 
    Base serializer for models with timestamp fields.

    """
    class Meta:
        abstract = True
        read_only_fields = ('created_at', 'updated_at')



class BaseUserRelatedSerializer(serializers.ModelSerializer):
    """
    Base serializer for models with user relationships.
    Centralizes common user field handling.
    """
    
    def get_user_display_name(self, user):
        """Get formatted user display name."""
        if user:
            return f"{user.first_name} {user.last_name}"
        return None
    
    class Meta:
        abstract = True



# ============================================================================
# 1. USERS & AUTHENTICATION SERIALIZERS
# ============================================================================

class CustomUserSerializer(BaseUserRelatedSerializer):
    """
    Primary user serializer with full user information.
    Implements: Meaningful naming, SRP (user data serialization only).
    """

    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(
        source='department.department_name',
        read_only = True
    )
    college_name = serializers.CharField(
        source='college.college_name',
        read_only = True
    )
    user_type_display = serializers.CharField(
        source='get_user_type_display',
        read_only = True
    )

    class Meta:
        model = CustomUser
        fields = [
            'user_id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'user_type_display', 'department', 'department_name',
            'college', 'college_name', 'phone_number', 'employee_id', 
            'position', 'is_active'
        ]
        read_only_fields = ('user_id',)

    def get_full_name(self, obj):
        """Generate full name from first and last name."""
        return f"{obj.first_name} {obj.last_name}".strip()




class UserBasicInfoSerializer(serializers.ModelSerializer):
    """
    Lightweight user serializer for nested relationships.
    Single responsibility: Provide essential user info for references.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['user_id', 'email', 'full_name', 'user_type']
    
    def get_full_name(self, obj):
        """Generate full name from first and last name"""
        return f"{obj.first_name} {obj.last_name}".strip()
    


class RegisterSerializer(serializers.ModelSerializer):
    """
    User registration serializer with password validation.
    Single responsibility: Handle new user registration.
    """
    
    password = serializers.CharField(
        write_only = True,
        style = {'input_type': 'password'},
        help_text = 'Password must meet security requirements'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'username', 'first_name', 'last_name', 
            'user_type', 'department', 'college', 'phone_number',
            'employee_id', 'position', 'password', 'password_confirm'
        ]

    def validate_email(self, value):
        """Ensure email is unique"""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(ERROR_MESSAGES['duplicate_email'])
        return value
    
    def validate_password(self, value):
        """Validate password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, data):
        """Cross-field validation for password confirmation"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return data
    
    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )
        return user
    


class LoginSerializer(serializers.Serializer):
    """
    Authentication serializer.
    Single responsibility: Handle user authentication.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        """Authenticate user credentials."""
        email = data.get('email')
        password = data.get('password')
        
        if not email:
            raise serializers.ValidationError(ERROR_MESSAGES['email_required'])
        
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError(ERROR_MESSAGES['invalid_credentials'])
        
        if not user.is_active:
            raise serializers.ValidationError(ERROR_MESSAGES['user_inactive'])
        
        data['user'] = user
        return data


# ============================================================================
# 2. COLLEGES & DEPARTMENTS SERIALIZERS
# ============================================================================

class CollegeSerializer(TimestampedModelSerializer):
    """
    College serializer with nested relationships.
    Single responsibility: Serialize college data with related users.
    """
    
    dean_info = UserBasicInfoSerializer(source='dean', read_only=True)
    extension_coordinator_info = UserBasicInfoSerializer(
        source='extension_coordinator', 
        read_only=True
    )
    department_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    
    class Meta:
        model = College
        fields = [
            'college_id', 'college_name', 'college_code',
            'dean', 'dean_info', 'extension_coordinator', 
            'extension_coordinator_info', 'department_count',
            'project_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ('college_id',)
    
    def get_department_count(self, obj):
        """Get number of departments in this college."""
        return obj.departments.count()
    
    def get_project_count(self, obj):
        """Get number of projects in this college."""
        return obj.projects.count()


class DepartmentSerializer(TimestampedModelSerializer):
    """
    Department serializer with college information.
    Single responsibility: Serialize department data with related info.
    """
    
    college_info = CollegeSerializer(source='college', read_only=True)
    department_head_info = UserBasicInfoSerializer(
        source='department_head', 
        read_only=True
    )
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'department_id', 'department_name', 'department_code',
            'college', 'college_info', 'department_head', 
            'department_head_info', 'user_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ('department_id',)
    
    def get_user_count(self, obj):
        """Get number of users in this department."""
        return obj.users.count()


# ============================================================================
# 3. PROJECT SERIALIZERS
# ============================================================================

class ProjectSerializer(TimestampedModelSerializer):
    """
    Base project serializer with essential information.
    Single responsibility: Serialize core project data.
    """
    
    project_leader_info = UserBasicInfoSerializer(
        source='project_leader', 
        read_only=True
    )
    college_info = CollegeSerializer(source='college', read_only=True)
    department_info = DepartmentSerializer(source='department', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    project_type_display = serializers.CharField(
        source='get_project_type_display', 
        read_only=True
    )
    duration_days = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Project
        fields = [
            'project_id', 'title', 'description', 'project_type', 
            'project_type_display', 'status', 'status_display',
            'start_date', 'end_date', 'duration_days', 'budget', 
            'location', 'project_leader', 'project_leader_info',
            'college', 'college_info', 'department', 'department_info',
            'expected_beneficiaries', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ('project_id',)
    
    def validate(self, data):
        """Cross-field validation for project data."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        budget = data.get('budget')
        
        if start_date and end_date:
            validate_date_range(start_date, end_date)
            
            # Validate project duration
            duration = (end_date - start_date).days
            if duration < MIN_PROJECT_DURATION_DAYS:
                raise serializers.ValidationError(
                    f'Project must be at least {MIN_PROJECT_DURATION_DAYS} day(s) long.'
                )
            if duration > MAX_PROJECT_DURATION_DAYS:
                raise serializers.ValidationError(
                    f'Project duration cannot exceed {MAX_PROJECT_DURATION_DAYS} days.'
                )
        
        if budget is not None:
            validate_positive_amount(budget, 'budget')
        
        return data


class ProjectDetailSerializer(ProjectSerializer):
    """
    Detailed project serializer with all relationships.
    Single responsibility: Provide comprehensive project view.
    """
    
    members = serializers.SerializerMethodField()
    trainers = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    
    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + [
            'members', 'trainers', 'requirements', 'files', 
            'reports', 'member_count'
        ]
    
    def get_members(self, obj):
        """Get active project members."""
        from .serializers import ProjectMemberSerializer  # Avoid circular import
        members = obj.members.filter(is_active=True)
        return ProjectMemberSerializer(members, many=True).data
    
    def get_trainers(self, obj):
        """Get project trainer assignments."""
        from .serializers import ProjectTrainerSerializer  # Avoid circular import
        trainers = obj.trainer_assignments.all()
        return ProjectTrainerSerializer(trainers, many=True).data
    
    def get_requirements(self, obj):
        """Get project requirements."""
        from .serializers import DocumentaryRequirementSerializer  # Avoid circular import
        requirements = obj.requirements.all()
        return DocumentaryRequirementSerializer(requirements, many=True).data
    
    def get_files(self, obj):
        """Get project files."""
        from .serializers import FileSerializer  # Avoid circular import
        files = obj.files.all()
        return FileSerializer(files, many=True).data
    
    def get_reports(self, obj):
        """Get accomplishment reports."""
        from .serializers import AccomplishmentReportSerializer  # Avoid circular import
        reports = obj.accomplishment_reports.all()
        return AccomplishmentReportSerializer(reports, many=True).data
    
    def get_member_count(self, obj):
        """Get active member count."""
        return obj.members.filter(is_active=True).count()


class ProjectCreateSerializer(serializers.ModelSerializer):
    """
    Write-only project serializer for creation.
    Single responsibility: Handle project creation with minimal data.
    """
    
    class Meta:
        model = Project
        fields = [
            'title', 'description', 'project_type', 'status',
            'start_date', 'end_date', 'budget', 'location',
            'project_leader', 'college', 'department', 'expected_beneficiaries'
        ]
    
    def validate(self, data):
        """Apply same validation as ProjectSerializer."""
        return ProjectSerializer().validate(data)


# ============================================================================
# 4. PROJECT MEMBERSHIP SERIALIZERS
# ============================================================================

class ProjectMemberSerializer(serializers.ModelSerializer):
    """
    Project member serializer with user and project info.
    Single responsibility: Serialize team membership data.
    """
    
    user_info = UserBasicInfoSerializer(source='user', read_only=True)
    project_info = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = ProjectMember
        fields = [
            'member_id', 'project', 'project_info', 'user', 'user_info',
            'role', 'role_display', 'assigned_date', 'is_active'
        ]
        read_only_fields = ('member_id', 'assigned_date')
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title,
            'status': obj.project.status
        }
    
    def validate(self, data):
        """Prevent duplicate memberships."""
        project = data.get('project')
        user = data.get('user')
        
        if project and user:
            existing = ProjectMember.objects.filter(
                project=project, 
                user=user
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError(
                    'User is already a member of this project.'
                )
        
        return data


# ============================================================================
# 5. TRAINER SERIALIZERS
# ============================================================================

class TrainerSerializer(TimestampedModelSerializer):
    """
    Trainer serializer with assignment count.
    Single responsibility: Serialize trainer information.
    """
    
    trainer_type_display = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    cv_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Trainer
        fields = [
            'trainer_id', 'trainer_name', 'email', 'phone_number',
            'expertise', 'bio', 'is_internal', 'trainer_type_display',
            'cv_file', 'cv_file_url', 'assignment_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ('trainer_id',)
    
    def get_trainer_type_display(self, obj):
        """Get trainer type as human-readable string."""
        return 'Internal' if obj.is_internal else 'External'
    
    def get_assignment_count(self, obj):
        """Get number of project assignments."""
        return obj.project_assignments.count()
    
    def get_cv_file_url(self, obj):
        """Get CV file URL if exists."""
        if obj.cv_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cv_file.url)
        return None


class ProjectTrainerSerializer(serializers.ModelSerializer):
    """
    Project trainer assignment serializer.
    Single responsibility: Serialize trainer-project relationships.
    """
    
    trainer_info = TrainerSerializer(source='trainer', read_only=True)
    project_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProjectTrainer
        fields = [
            'assignment_id', 'project', 'project_info', 'trainer', 'trainer_info',
            'training_date', 'training_topic', 'duration_hours', 'location',
            'status', 'status_display', 'notes', 'honorarium'
        ]
        read_only_fields = ('assignment_id',)
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def validate_duration_hours(self, value):
        """Validate training duration."""
        if value <= 0:
            raise serializers.ValidationError('Duration must be positive.')
        return value
    
    def validate_honorarium(self, value):
        """Validate honorarium amount."""
        if value is not None and value < 0:
            raise serializers.ValidationError('Honorarium cannot be negative.')
        return value


# ============================================================================
# 6. REQUIREMENTS & FILE MANAGEMENT SERIALIZERS
# ============================================================================

class DocumentaryRequirementSerializer(TimestampedModelSerializer):
    """
    Documentary requirement serializer with user relationships.
    Single responsibility: Serialize requirement data with assignments.
    """
    
    project_info = serializers.SerializerMethodField()
    assigned_by_info = UserBasicInfoSerializer(source='assigned_by', read_only=True)
    assigned_to_info = UserBasicInfoSerializer(source='assigned_to', read_only=True)
    approved_by_info = UserBasicInfoSerializer(source='approved_by', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentaryRequirement
        fields = [
            'requirement_id', 'project', 'project_info', 'requirement_name',
            'description', 'due_date', 'status', 'status_display',
            'assigned_by', 'assigned_by_info', 'assigned_to', 'assigned_to_info',
            'submitted_date', 'approved_by', 'approved_by_info', 'approval_date',
            'rejection_reason', 'is_overdue', 'file_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ('requirement_id', 'submitted_date', 'approval_date')
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def get_file_count(self, obj):
        """Get number of files submitted for this requirement."""
        return obj.files.count()
    
    def validate_due_date(self, value):
        """Ensure due date is not in the past for new requirements."""
        if not self.instance and value < timezone.now().date():
            raise serializers.ValidationError(
                'Due date cannot be in the past.'
            )
        return value


class FileSerializer(serializers.ModelSerializer):
    """
    File serializer with upload handling and approval workflow.
    Single responsibility: Serialize file data with metadata.
    """
    
    project_info = serializers.SerializerMethodField()
    requirement_info = serializers.SerializerMethodField()
    uploaded_by_info = UserBasicInfoSerializer(source='uploaded_by', read_only=True)
    approved_by_info = UserBasicInfoSerializer(source='approved_by', read_only=True)
    approval_status_display = serializers.CharField(
        source='get_approval_status_display', 
        read_only=True
    )
    file_type_display = serializers.CharField(
        source='get_file_type_display', 
        read_only=True
    )
    file_size_mb = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = File
        fields = [
            'file_id', 'project', 'project_info', 'requirement', 'requirement_info',
            'file_name', 'file_type', 'file_type_display', 'file_path', 'file_url',
            'file_size', 'file_size_mb', 'uploaded_by', 'uploaded_by_info',
            'uploaded_date', 'approval_status', 'approval_status_display',
            'approved_by', 'approved_by_info', 'approval_date'
        ]
        read_only_fields = (
            'file_id', 'file_size', 'uploaded_by', 'uploaded_date', 'approval_date'
        )
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def get_requirement_info(self, obj):
        """Get requirement information if associated."""
        if obj.requirement:
            return {
                'requirement_id': obj.requirement.requirement_id,
                'requirement_name': obj.requirement.requirement_name
            }
        return None
    
    def get_file_url(self, obj):
        """Get file URL if exists."""
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
        return None
    
    def validate_file_path(self, value):
        """Validate file size."""
        if value.size > MAX_FILE_SIZE_MB * BYTES_TO_MB:
            raise serializers.ValidationError(
                f'File size exceeds {MAX_FILE_SIZE_MB}MB limit.'
            )
        return value
    
    def create(self, validated_data):
        """Set file metadata on creation."""
        file_obj = validated_data['file_path']
        validated_data['file_size'] = file_obj.size
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# 7. REPORTS & MONITORING SERIALIZERS
# ============================================================================

class AccomplishmentReportSerializer(serializers.ModelSerializer):
    """
    Accomplishment report serializer with review workflow.
    Single responsibility: Serialize report data with review status.
    """
    
    project_info = serializers.SerializerMethodField()
    submitted_by_info = UserBasicInfoSerializer(source='submitted_by', read_only=True)
    reviewed_by_info = UserBasicInfoSerializer(source='reviewed_by', read_only=True)
    report_type_display = serializers.CharField(
        source='get_report_type_display', 
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AccomplishmentReport
        fields = [
            'report_id', 'project', 'project_info', 'report_type', 
            'report_type_display', 'reporting_period', 'achievements',
            'challenges', 'recommendations', 'submitted_by', 'submitted_by_info',
            'submission_date', 'status', 'status_display', 'reviewed_by',
            'reviewed_by_info', 'review_date', 'review_comments'
        ]
        read_only_fields = ('report_id', 'submission_date', 'review_date')
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def create(self, validated_data):
        """Set submitter on creation."""
        validated_data['submitted_by'] = self.context['request'].user
        return super().create(validated_data)


class ProjectPerformanceSerializer(serializers.ModelSerializer):
    """
    Project performance metrics serializer.
    Single responsibility: Serialize performance data with calculations.
    """
    
    project_info = serializers.SerializerMethodField()
    updated_by_info = UserBasicInfoSerializer(source='updated_by', read_only=True)
    overall_performance_score = serializers.ReadOnlyField()
    
    class Meta:
        model = ProjectPerformance
        fields = [
            'performance_id', 'project', 'project_info', 'total_beneficiaries',
            'completion_percentage', 'budget_utilization', 'impact_score',
            'sustainability_rating', 'overall_performance_score',
            'last_updated', 'updated_by', 'updated_by_info'
        ]
        read_only_fields = ('performance_id', 'last_updated')
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def update(self, instance, validated_data):
        """Set updated_by on update."""
        validated_data['updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)


# ============================================================================
# 8. ATTENDANCE & EVALUATION SERIALIZERS
# ============================================================================

class AttendanceTemplateSerializer(TimestampedModelSerializer):
    """
    Attendance template serializer.
    Single responsibility: Serialize attendance session templates.
    """
    
    project_info = serializers.SerializerMethodField()
    created_by_info = UserBasicInfoSerializer(source='created_by', read_only=True)
    attendance_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AttendanceTemplate
        fields = [
            'template_id', 'project', 'project_info', 'template_name',
            'session_date', 'session_time', 'venue', 'expected_participants',
            'created_by', 'created_by_info', 'is_active', 'attendance_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('template_id',)
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def get_attendance_count(self, obj):
        """Get number of attendance records."""
        return obj.attendance_records.count()
    
    def create(self, validated_data):
        """Set creator on creation."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """
    Attendance record serializer.
    Single responsibility: Serialize individual attendance records.
    """
    
    template_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'attendance_id', 'template', 'template_info', 'participant_name',
            'participant_email', 'organization', 'contact_number',
            'check_in_time', 'check_out_time', 'status', 'status_display', 'notes'
        ]
        read_only_fields = ('attendance_id',)
    
    def get_template_info(self, obj):
        """Get basic template information."""
        return {
            'template_id': obj.template.template_id,
            'template_name': obj.template.template_name,
            'session_date': obj.template.session_date
        }


class EvaluationSerializer(serializers.ModelSerializer):
    """
    Evaluation serializer with rating validation.
    Single responsibility: Serialize evaluation data with validation.
    """
    
    project_info = serializers.SerializerMethodField()
    evaluator_info = UserBasicInfoSerializer(source='evaluator', read_only=True)
    trainer_info = TrainerSerializer(source='trainer', read_only=True)
    evaluation_type_display = serializers.CharField(
        source='get_evaluation_type_display', 
        read_only=True
    )
    evaluator_display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Evaluation
        fields = [
            'evaluation_id', 'project', 'project_info', 'evaluator', 'evaluator_info',
            'trainer', 'trainer_info', 'evaluation_type', 'evaluation_type_display',
            'rating', 'feedback', 'evaluation_date', 'is_anonymous',
            'evaluator_name', 'evaluator_email', 'evaluator_display_name'
        ]
        read_only_fields = ('evaluation_id', 'evaluation_date')
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def get_evaluator_display_name(self, obj):
        """Get evaluator name (anonymous if applicable)."""
        if obj.is_anonymous:
            return obj.evaluator_name or 'Anonymous'
        return obj.evaluator.full_name if obj.evaluator else 'Unknown'
    
    def validate_rating(self, value):
        """Validate rating is within acceptable range."""
        if value < MIN_RATING or value > MAX_RATING:
            raise serializers.ValidationError(
                f'Rating must be between {MIN_RATING} and {MAX_RATING}.'
            )
        return value
    
    def validate(self, data):
        """Cross-field validation for anonymous evaluations."""
        is_anonymous = data.get('is_anonymous', False)
        evaluator = data.get('evaluator')
        evaluator_name = data.get('evaluator_name')
        evaluator_email = data.get('evaluator_email')
        
        if is_anonymous:
            # For anonymous evaluations, clear evaluator and require name/email
            data['evaluator'] = None
            if not evaluator_name:
                raise serializers.ValidationError({
                    'evaluator_name': 'Name is required for anonymous evaluations.'
                })
            if not evaluator_email:
                raise serializers.ValidationError({
                    'evaluator_email': 'Email is required for anonymous evaluations.'
                })
        else:
            # For non-anonymous evaluations, require evaluator
            if not evaluator:
                raise serializers.ValidationError({
                    'evaluator': 'Evaluator is required for non-anonymous evaluations.'
                })
            # Clear anonymous fields
            data['evaluator_name'] = None
            data['evaluator_email'] = None
        
        return data


# ============================================================================
# 9. LINKS & COMMUNICATION SERIALIZERS
# ============================================================================

class EvaluationLinkSerializer(TimestampedModelSerializer):
    """
    Evaluation link serializer with validation and expiration tracking.
    Single responsibility: Serialize shareable link data.
    """
    
    project_info = serializers.SerializerMethodField()
    created_by_info = UserBasicInfoSerializer(source='created_by', read_only=True)
    link_type_display = serializers.CharField(
        source='get_link_type_display', 
        read_only=True
    )
    is_expired = serializers.ReadOnlyField()
    is_usage_exceeded = serializers.ReadOnlyField()
    is_valid = serializers.ReadOnlyField()
    absolute_url = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluationLink
        fields = [
            'link_id', 'project', 'project_info', 'link_type', 'link_type_display',
            'unique_token', 'expiration_date', 'created_by', 'created_by_info',
            'is_active', 'usage_count', 'max_usage', 'is_expired',
            'is_usage_exceeded', 'is_valid', 'absolute_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ('link_id', 'unique_token', 'usage_count')
    
    def get_project_info(self, obj):
        """Get basic project information."""
        return {
            'project_id': obj.project.project_id,
            'title': obj.project.title
        }
    
    def get_absolute_url(self, obj):
        """Generate absolute URL for the link."""
        request = self.context.get('request')
        if request:
            # Construct URL based on link type
            link_path = f"/{obj.link_type.lower()}/{obj.unique_token}/"
            return request.build_absolute_uri(link_path)
        return None
    
    def validate_expiration_date(self, value):
        """Ensure expiration date is in the future."""
        if value <= timezone.now():
            raise serializers.ValidationError(
                'Expiration date must be in the future.'
            )
        return value
    
    def validate_max_usage(self, value):
        """Validate max usage limit."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                'Max usage must be a positive number or null for unlimited.'
            )
        return value
    
    def create(self, validated_data):
        """Set creator on creation."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CommunicationSerializer(serializers.ModelSerializer):
    """
    Communication serializer for email tracking.
    Single responsibility: Serialize communication data with status tracking.
    """
    
    project_info = serializers.SerializerMethodField()
    sender_info = UserBasicInfoSerializer(source='sender', read_only=True)
    email_type_display = serializers.CharField(
        source='get_email_type_display', 
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_delivered = serializers.ReadOnlyField()
    is_read = serializers.ReadOnlyField()
    
    class Meta:
        model = Communication
        fields = [
            'communication_id', 'project', 'project_info', 'sender', 'sender_info',
            'recipient_email', 'recipient_name', 'email_type', 'email_type_display',
            'subject', 'message', 'sent_date', 'is_automated', 'status',
            'status_display', 'error_message', 'read_at', 'is_delivered', 'is_read'
        ]
        read_only_fields = (
            'communication_id', 'sent_date', 'status', 'error_message', 'read_at'
        )
    
    def get_project_info(self, obj):
        """Get basic project information if associated."""
        if obj.project:
            return {
                'project_id': obj.project.project_id,
                'title': obj.project.title
            }
        return None
    
    def validate_subject(self, value):
        """Ensure subject is not empty."""
        if not value.strip():
            raise serializers.ValidationError('Subject cannot be empty.')
        return value
    
    def validate_message(self, value):
        """Ensure message is not empty."""
        if not value.strip():
            raise serializers.ValidationError('Message cannot be empty.')
        return value
    
    def create(self, validated_data):
        """Set sender on creation."""
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


# ============================================================================
# SPECIALIZED SERIALIZERS FOR SPECIFIC USE CASES
# ============================================================================

class ProjectSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight project serializer for lists and dropdowns.
    Single responsibility: Provide minimal project info for UI components.
    """
    
    project_leader_name = serializers.CharField(
        source='project_leader.full_name', 
        read_only=True
    )
    college_code = serializers.CharField(source='college.college_code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'project_id', 'title', 'project_type', 'status', 'status_display',
            'project_leader_name', 'college_code', 'start_date', 'end_date'
        ]


class UserProfileSerializer(CustomUserSerializer):
    """
    Extended user serializer for profile management.
    Single responsibility: Provide comprehensive user profile data.
    """
    
    led_projects_count = serializers.SerializerMethodField()
    project_memberships_count = serializers.SerializerMethodField()
    recent_activities = serializers.SerializerMethodField()
    
    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + [
            'led_projects_count', 'project_memberships_count', 'recent_activities'
        ]
    
    def get_led_projects_count(self, obj):
        """Get number of projects this user leads."""
        return obj.led_projects.count()
    
    def get_project_memberships_count(self, obj):
        """Get number of project memberships."""
        return obj.project_memberships.filter(is_active=True).count()
    
    def get_recent_activities(self, obj):
        """Get recent user activities (simplified)."""
        # This could be expanded to include recent files, reports, etc.
        recent_projects = obj.led_projects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        )[:5]
        
        return ProjectSummarySerializer(recent_projects, many=True).data


class ProjectStatisticsSerializer(serializers.Serializer):
    """
    Serializer for project statistics and dashboard data.
    Single responsibility: Serialize aggregated project statistics.
    """
    
    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    completed_projects = serializers.IntegerField()
    total_beneficiaries = serializers.IntegerField()
    average_budget = serializers.DecimalField(max_digits=12, decimal_places=2)
    projects_by_type = serializers.DictField()
    projects_by_status = serializers.DictField()
    monthly_completions = serializers.ListField()
    
    class Meta:
        # No model as this is a pure data serializer
        fields = [
            'total_projects', 'active_projects', 'completed_projects',
            'total_beneficiaries', 'average_budget', 'projects_by_type',
            'projects_by_status', 'monthly_completions'
        ]


class BulkOperationSerializer(serializers.Serializer):
    """
    Serializer for bulk operations on projects or other entities.
    Single responsibility: Handle bulk update/delete operations.
    """
    
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text='List of IDs to perform bulk operation on'
    )
    action = serializers.ChoiceField(
        choices=['activate', 'deactivate', 'delete', 'approve', 'reject'],
        help_text='Action to perform on selected items'
    )
    reason = serializers.CharField(
        required=False,
        max_length=500,
        help_text='Optional reason for the bulk operation'
    )
    
    def validate_ids(self, value):
        """Ensure IDs list is not empty and contains valid integers."""
        if not value:
            raise serializers.ValidationError('At least one ID must be provided.')
        
        # Remove duplicates while preserving order
        unique_ids = list(dict.fromkeys(value))
        
        if len(unique_ids) != len(value):
            # Log that duplicates were removed
            pass
        
        return unique_ids


# ============================================================================
# SEARCH AND FILTER SERIALIZERS
# ============================================================================

class ProjectSearchSerializer(serializers.Serializer):
    """
    Serializer for project search parameters.
    Single responsibility: Validate and serialize search criteria.
    """
    
    query = serializers.CharField(
        required=False,
        max_length=200,
        help_text='Search query for title, description, or location'
    )
    project_type = serializers.ChoiceField(
        choices=[('', 'All')] + list(Project._meta.get_field('project_type').choices),
        required=False,
        help_text='Filter by project type'
    )
    status = serializers.ChoiceField(
        choices=[('', 'All')] + list(ProjectStatusChoices.choices),
        required=False,
        help_text='Filter by project status'
    )
    college = serializers.IntegerField(
        required=False,
        help_text='Filter by college ID'
    )
    department = serializers.IntegerField(
        required=False,
        help_text='Filter by department ID'
    )
    start_date_from = serializers.DateField(
        required=False,
        help_text='Filter projects starting from this date'
    )
    start_date_to = serializers.DateField(
        required=False,
        help_text='Filter projects starting before this date'
    )
    budget_min = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text='Minimum budget filter'
    )
    budget_max = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text='Maximum budget filter'
    )
    ordering = serializers.ChoiceField(
        choices=[
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
            ('start_date', 'Start Date (Oldest)'),
            ('-start_date', 'Start Date (Newest)'),
            ('budget', 'Budget (Low to High)'),
            ('-budget', 'Budget (High to Low)'),
            ('-created_at', 'Recently Created'),
            ('created_at', 'Oldest Created')
        ],
        required=False,
        default='-created_at',
        help_text='Sort order for results'
    )
    
    def validate(self, data):
        """Cross-field validation for search parameters."""
        start_date_from = data.get('start_date_from')
        start_date_to = data.get('start_date_to')
        budget_min = data.get('budget_min')
        budget_max = data.get('budget_max')
        
        if start_date_from and start_date_to:
            if start_date_from > start_date_to:
                raise serializers.ValidationError(
                    'start_date_from must be before start_date_to'
                )
        
        if budget_min and budget_max:
            if budget_min > budget_max:
                raise serializers.ValidationError(
                    'budget_min must be less than budget_max'
                )
        
        return data


# ============================================================================
# EXPORT SERIALIZERS
# ============================================================================

class ProjectExportSerializer(serializers.ModelSerializer):
    """
    Comprehensive project serializer for data export.
    Single responsibility: Provide all project data for export formats.
    """
    
    project_leader_name = serializers.CharField(
        source='project_leader.full_name', 
        read_only=True
    )
    project_leader_email = serializers.CharField(
        source='project_leader.email', 
        read_only=True
    )
    college_name = serializers.CharField(source='college.college_name', read_only=True)
    college_code = serializers.CharField(source='college.college_code', read_only=True)
    department_name = serializers.CharField(
        source='department.department_name', 
        read_only=True
    )
    department_code = serializers.CharField(
        source='department.department_code', 
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    project_type_display = serializers.CharField(
        source='get_project_type_display', 
        read_only=True
    )
    duration_days = serializers.ReadOnlyField()
    member_count = serializers.SerializerMethodField()
    trainer_count = serializers.SerializerMethodField()
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'project_id', 'title', 'description', 'project_type', 
            'project_type_display', 'status', 'status_display',
            'start_date', 'end_date', 'duration_days', 'budget', 'location',
            'project_leader_name', 'project_leader_email', 'college_name',
            'college_code', 'department_name', 'department_code',
            'expected_beneficiaries', 'member_count', 'trainer_count',
            'file_count', 'created_at', 'updated_at'
        ]
    
    def get_member_count(self, obj):
        """Get active member count."""
        return obj.members.filter(is_active=True).count()
    
    def get_trainer_count(self, obj):
        """Get trainer assignment count."""
        return obj.trainer_assignments.count()
    
    def get_file_count(self, obj):
        """Get file count."""
        return obj.files.count()


# ============================================================================
# ERROR RESPONSE SERIALIZERS
# ============================================================================

class ErrorResponseSerializer(serializers.Serializer):
    """
    Standardized error response serializer.
    Single responsibility: Provide consistent error message format.
    """
    
    error = serializers.CharField(help_text='Error type or code')
    message = serializers.CharField(help_text='Human-readable error message')
    details = serializers.DictField(
        required=False,
        help_text='Additional error details or field-specific errors'
    )
    timestamp = serializers.DateTimeField(
        default=timezone.now,
        help_text='When the error occurred'
    )
    
    class Meta:
        fields = ['error', 'message', 'details', 'timestamp']


class ValidationErrorSerializer(ErrorResponseSerializer):
    """
    Validation error response serializer.
    Single responsibility: Handle validation error responses.
    """
    
    field_errors = serializers.DictField(
        required=False,
        help_text='Field-specific validation errors'
    )
    
    class Meta(ErrorResponseSerializer.Meta):
        fields = ErrorResponseSerializer.Meta.fields + ['field_errors']



