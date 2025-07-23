from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg
from django.utils import timezone
from .models import (
    CustomUser, College, Department, Project, ProjectMember, 
    Trainer, ProjectTrainer, DocumentaryRequirement, File, 
    AccomplishmentReport, AttendanceTemplate, AttendanceRecord,
    Evaluation, EvaluationLink, ProjectPerformance, Communication
)

User = get_user_model()



### USER & ORGANIZATIONAL SERIALIZERS

class CollegeSerializer(serializers.ModelSerializer):
    dean_name = serializers.CharField(source='dean.full_name', read_only=True)
    coordinator_name = serializers.CharField(source='extension_coordinator.full_name', read_only=True)
    department_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = [
            'college_id', 'college_name', 'college_code', 'dean', 'dean_name',
            'extension_coordinator', 'coordinator_name', 'department_count',
            'project_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['college_id', 'created_at', 'updated_at']

        def get_department_count(self, obj):
            return obj.departments.count()
        
        def get_project_count(self, obj):
            return obj.projects.count()

class CollegeListSerializer(serializers.ModelSerializer):
    """"Lightweight serializer for dropdown/list views"""
    class Meta:
        model = College
        fields = ['colleged_id', 'college_name', 'college_code']



class DepartmentSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='college.college_name', read_only=True)
    head_name = serializers.CharField(source='department_head.full_name', read_only=True)
    user_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'department_id', 'department_name', 'department_code', 'college',
            'college_name', 'department_head', 'head_name', 'user_count',
            'project_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['department_id', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        return obj.users.count()

    def get_project_count(self, obj):
        return obj.projects.count()


class DepartmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown/list views"""
    college_code = serializers.CharField(source='college.college_code', read_only=True)
    
    class Meta:
        model = Department
        fields = ['department_id', 'department_name', 'department_code', 'college_code']



class CustomUserSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='college.college_name', read_only=True)
    department_name = serializers.CharField(source='department.department_name', read_only=True)
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    managed_projects_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'user_type_display', 'phone_number', 'employee_id', 'position',
            'department', 'department_name', 'college', 'college_name', 'is_active',
            'managed_projects_count', 'date_joined', 'last_login'
        ]
        read_only_fields  = ['user_id', 'date_joined', 'last_login', 'full_name']
        extra_kwargs = {
            'password': {'write_only': True},
            'last_login': {'read_only': True}
        }

    def get_managed_projects_count(self, obj):
        return obj.led_projects.count()
    


class CustomUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password_confirm', 'first_name', 
            'last_name', 'user_type', 'phone_number', 'employee_id', 'position',
            'department', 'college'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save
        return user
    


class CustomUserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown/list views"""
    class Meta:
        model = CustomUser
        fields = ['user_id', 'full_name', 'email', 'user_type']



### PROJECT MANAGEMENT SERIALIZERS

class ProjectMemberSerializers(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            'member_id', 'user', 'user_name', 'user_email', 'role', 
            'role_display', 'assigned_date', 'is_active'
        ]
        read_only_fields = ['member_id', 'assigned_date']



class ProjectTrainerSerializer(serializers.ModelSerializer):
    trainer_name = serializers.CharField(source='trainer.trainer_name', read_only=True)
    trainer_email = serializers.CharField(source='trainer.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProjectTrainer
        fields = [
            'assignment_id', 'trainer', 'trainer_name', 'trainer_email',
            'training_date', 'training_topic', 'duration_hours', 'location',
            'status', 'status_display', 'notes', 'honorarium'
        ]
        read_only_fields = ['assignment_id']



class ProjectSerializer(serializers.ModelSerializer):
    project_leader_name = serializers.CharField(source='project_leader.full_name', read_only=True)
    college_name = serializers.CharField(source='college.college_name', read_only=True)
    department_name = serializers.CharField(source='department.department_name', read_only=True)
    project_type_display = serializers.CharField(source='get_project_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_days = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    member_count = serializers.SerializerMethodField()
    
    # Nested serializers for detailed view
    members = ProjectMemberSerializer(many=True, read_only=True)
    trainer_assignments = ProjectTrainerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'project_id', 'title', 'description', 'project_type', 'project_type_display',
            'status', 'status_display', 'start_date', 'end_date', 'duration_days',
            'budget', 'location', 'project_leader', 'project_leader_name',
            'college', 'college_name', 'department', 'department_name',
            'expected_beneficiaries', 'is_active', 'member_count',
            'members', 'trainer_assignments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['project_id', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()

    def validate(self, attrs):
        if attrs.get('start_date') and attrs.get('end_date'):
            if attrs['start_date'] >= attrs['end_date']:
                raise serializers.ValidationError("End date must be after start date")
        return attrs



class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    project_leader_name = serializers.CharField(source='project_leader.full_name', read_only=True)
    college_name = serializers.CharField(source='college.college_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'project_id', 'title', 'project_type', 'status', 'status_display',
            'start_date', 'end_date', 'budget', 'project_leader_name',
            'college_name', 'expected_beneficiaries'
        ]



class ProjectPerformanceSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.full_name', read_only=True)
    
    class Meta:
        model = ProjectPerformance
        fields = [
            'performance_id', 'project', 'project_title', 'total_beneficiaries',
            'completion_percentage', 'budget_utilization', 'impact_score',
            'sustainability_rating', 'last_updated', 'updated_by', 'updated_by_name'
        ]
        read_only_fields = ['performance_id', 'last_updated']



### TRAINER SERIALIZER

class TrainerSerializer(serializers.ModelSerializer):
    assignment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Trainer
        fields = [
            'trainer_id', 'trainer_name', 'email', 'phone_number', 'expertise',
            'bio', 'is_internal', 'cv_file', 'assignment_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['trainer_id', 'created_at', 'updated_at']

    def get_assignment_count(self, obj):
        return obj.project_assignments.count()


class TrainerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdown/list views"""
    class Meta:
        model = Trainer
        fields = ['trainer_id', 'trainer_name', 'email', 'is_internal']



### DOCUMENT MANAGEMENT SERIALIZERS

class DocumentaryRequirementSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = DocumentaryRequirement
        fields = [
            'requirement_id', 'project', 'project_title', 'requirement_name',
            'description', 'due_date', 'status', 'status_display', 'is_overdue',
            'assigned_by', 'assigned_by_name', 'assigned_to', 'assigned_to_name',
            'submitted_date', 'approved_by', 'approved_by_name', 'approval_date',
            'rejection_reasion', 'created_at'
        ]
        read_only_fields = ['requirement_id', 'created_at', 'is_overdue']


class FileSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    requirement_name = serializers.CharField(source='requirement.requirement_name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    approval_status_display = serializers.CharField(source='get_approval_status_display', read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    
    class Meta:
        model = File
        fields = [
            'file_id', 'project', 'project_title', 'requirement', 'requirement_name',
            'file_name', 'file_type', 'file_type_display', 'file_path', 'file_size',
            'file_size_mb', 'uploaded_by', 'uploaded_by_name', 'uploaded_date',
            'approval_status', 'approval_status_display', 'approved_by',
            'approved_by_name', 'approval_date'
        ]
        read_only_fields = ['file_id', 'uploaded_date', 'file_size_mb']


class AccomplishmentReportSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AccomplishmentReport
        fields = [
            'report_id', 'project', 'project_title', 'report_type', 'report_type_display',
            'reporting_period', 'achievements', 'challenges', 'recommendations',
            'submitted_by', 'submitted_by_name', 'submission_date', 'status',
            'status_display', 'reviewed_by', 'reviewed_by_name', 'review_date',
            'review_comments'
        ]
        read_only_fields = ['report_id', 'submission_date']



### ATTENDANCE & EVALUATION SERIALIZERS

class AttendanceRecordSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'attendance_id', 'participant_name', 'participant_email', 'organization',
            'contact_number', 'check_in_time', 'check_out_time', 'status',
            'status_display', 'notes'
        ]
        read_only_fields = ['attendance_id']


class AttendanceTemplateSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    attendance_count = serializers.SerializerMethodField()
    attendance_records = AttendanceRecordSerializer(many=True, read_only=True)
    
    class Meta:
        model = AttendanceTemplate
        fields = [
            'template_id', 'project', 'project_title', 'template_name',
            'session_date', 'session_time', 'venue', 'expected_participants',
            'created_by', 'created_by_name', 'created_at', 'is_active',
            'attendance_count', 'attendance_records'
        ]
        read_only_fields = ['template_id', 'created_at']

    def get_attendance_count(self, obj):
        return obj.attendance_records.filter(status='PRESENT').count()


class EvaluationSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    evaluator_name_display = serializers.SerializerMethodField()
    trainer_name = serializers.CharField(source='trainer.trainer_name', read_only=True)
    evaluation_type_display = serializers.CharField(source='get_evaluation_type_display', read_only=True)
    
    class Meta:
        model = Evaluation
        fields = [
            'evaluation_id', 'project', 'project_title', 'evaluator', 'trainer',
            'trainer_name', 'evaluation_type', 'evaluation_type_display', 'rating',
            'feedback', 'evaluation_date', 'is_anonymous', 'evaluator_name',
            'evaluator_name_display', 'evaluator_email'
        ]
        read_only_fields = ['evaluation_id', 'evaluation_date']

    def get_evaluator_name_display(self, obj):
        if obj.is_anonymous:
            return obj.evaluator_name or "Anonymous"
        return obj.evaluator.full_name if obj.evaluator else "N/A"


class EvaluationLinkSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    link_type_display = serializers.CharField(source='get_link_type_display', read_only=True)
    is_expired = serializers.ReadOnlyField()
    is_usage_exceeded = serializers.ReadOnlyField()
    
    class Meta:
        model = EvaluationLink
        fields = [
            'link_id', 'project', 'project_title', 'link_type', 'link_type_display',
            'unique_token', 'expiration_date', 'created_by', 'created_by_name',
            'created_at', 'is_active', 'usage_count', 'max_usage', 'is_expired',
            'is_usage_exceeded'
        ]
        read_only_fields = ['link_id', 'unique_token', 'created_at', 'usage_count']



# COMMUNICATION SERIALIZER

class CommunicationSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    email_type_display = serializers.CharField(source='get_email_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Communication
        fields = [
            'communication_id', 'project', 'project_title', 'sender', 'sender_name',
            'recipient_email', 'recipient_name', 'email_type', 'email_type_display',
            'subject', 'message', 'sent_date', 'is_automated', 'status',
            'status_display', 'error_message', 'read_at'
        ]
        read_only_fields = ['communication_id', 'sent_date']



# DASHBOARD & ANALYTICS SERIALIZERS

class ProjectStatsSerializer(serializers.Serializer):
    """Serializer for project statistics"""
    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    completed_projects = serializers.IntegerField()
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_beneficiaries = serializers.IntegerField()
    projects_by_type = serializers.DictField()
    projects_by_status = serializers.DictField()
    projects_by_college = serializers.DictField()


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    users_by_type = serializers.DictField()
    users_by_college = serializers.DictField()


class DashboardSerializer(serializers.Serializer):
    """Combined dashboard statistics"""
    project_stats = ProjectStatsSerializer()
    user_stats = UserStatsSerializer()
    recent_projects = ProjectListSerializer(many=True)
    upcoming_deadlines = DocumentaryRequirementSerializer(many=True)
    recent_evaluations = EvaluationSerializer(many=True)




