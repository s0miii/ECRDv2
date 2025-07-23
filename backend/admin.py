from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils import timezone
from .models import (
    CustomUser, College, Department, Project, ProjectMember, 
    Trainer, ProjectTrainer, DocumentaryRequirement, File, 
    AccomplishmentReport, AttendanceTemplate, AttendanceRecord,
    Evaluation, EvaluationLink, ProjectPerformance, Communication
)



@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'email', 'first_name', 'last_name', 'user_type',
        'college', 'department', 'is_active', 'date_joined'
    ]
    list_filter = [
        'user_type', 'is_active', 'college', 'department',
        'date_joined', 'is_staff'
    ]
    search_fields = [
        'email', 'first_name', 'last_name', 'employee_id'
    ]
    ordering = ['last_name', 'first_name']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'employee_id', 'position')
        }),
        ('Role & Assignment', {
            'fields': ('user_type', 'college', 'department')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Role & Assignment', {
            'fields': ('user_type', 'college', 'department')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('college', 'department')



@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = [
        'college_code', 'college_name', 'dean', 
        'extension_coordinator', 'department_count', 'project_count'
    ]
    list_filter = ['created_at']
    search_fields = ['college_name', 'college_code']
    ordering = ['college_code']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'dean', 'extension_coordinator'
        ).annotate(
            department_count=Count('departments'),
            project_count=Count('projects')
        )
    
    def department_count(self, obj):
        return obj.department_count
    department_count.short_description = 'Departments'
    department_count.admin_order_field = 'department_count'

    def project_count(self, obj):
        return obj.project_count
    project_count.short_description = 'Projects'
    project_count.admin_order_field = 'project_count'



@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = [
        'department_code', 'department_name', 'college', 
        'department_head', 'user_count', 'project_count'
    ]
    list_filter = ['college', 'created_at']
    search_fields = ['department_name', 'department_code', 'college__college_name']
    ordering = ['college', 'department_code']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'college', 'department_head'
        ).annotate(
            user_count=Count('users'),
            project_count=Count('projects')
        )
    
    def user_count(self, obj):
        return obj.user_count
    user_count.short_description = 'Users'
    user_count.admin_order_field = 'user_count'

    def project_count(self, obj):
        return obj.project_count
    project_count.short_description = 'Projects'
    project_count.admin_order_field = 'project_count'

class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    autocomplete_fields = ['user']


class ProjectTrainerInline(admin.TabularInline):
    model = ProjectTrainer
    extra = 1
    autocomplete_fields = ['trainer']


class DocumentaryRequirementInline(admin.TabularInline):
    model = DocumentaryRequirement
    extra = 1
    fields = ['requirement_name', 'due_date', 'status', 'assigned_to']
    readonly_fields = ['created_at']



@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'project_type', 'status', 'project_leader', 
        'college', 'start_date', 'end_date', 'budget', 'member_count'
    ]
    list_filter = [
        'status', 'project_type', 'college', 'department', 
        'start_date', 'created_at'
    ]
    search_fields = ['title', 'description', 'location']
    ordering = ['-created_at']
    date_hierarchy = 'start_date'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'project_type', 'status')
        }),
        ('Timeline & Budget', {
            'fields': ('start_date', 'end_date', 'budget', 'location')
        }),
        ('Assignment', {
            'fields': ('project_leader', 'college', 'department', 'expected_beneficiaries')
        }),
    )

    inlines = [ProjectMemberInline, ProjectTrainerInline, DocumentaryRequirementInline]

    autocomplete_fields = ['project_leader', 'college', 'department']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'project_leader', 'college', 'department'
        ).annotate(
            member_count=Count('members')
        )
    
    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = 'Members'
    member_count.admin_order_field = 'member_count'



@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'role', 'assigned_date', 'is_active']
    list_filter = ['role', 'is_active', 'assigned_date']
    search_fields = ['user__first_name', 'user__last_name', 'project__title']
    ordering = ['-assigned_date']

    autocomplete_fields = ['project', 'user']



@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = [
        'trainer_name', 'email', 'is_internal', 
        'assignment_count', 'created_at'
    ]
    list_filter = ['is_internal', 'created_at']
    search_fields = ['trainer_name', 'email', 'expertise']
    ordering = ['trainer_name']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            assignment_count=Count('project_assignments')
        )
    
    def assignment_count(self, obj):
        return obj.assignment_count
    assignment_count.short_description = 'Assignments'
    assignment_count.admin_order_field = 'assignment_count'



@admin.register(ProjectTrainer)
class ProjectTrainerAdmin(admin.ModelAdmin):
    list_display = [
        'trainer', 'project', 'training_topic', 'training_date', 
        'duration_hours', 'status', 'honorarium'
    ]
    list_filter = ['status', 'training_date']
    search_fields = ['trainer__trainer_name', 'project__title', 'training_topic']
    ordering = ['-training_date']
    date_hierarchy = 'training_date'
    
    autocomplete_fields = ['project', 'trainer']


@admin.register(DocumentaryRequirement)
class DocumentaryRequirementAdmin(admin.ModelAdmin):
    list_display = [
        'requirement_name', 'project', 'assigned_to', 
        'due_date', 'status', 'is_overdue_display'
    ]
    list_filter = ['status', 'due_date', 'created_at']
    search_fields = ['requirement_name', 'project__title', 'assigned_to__first_name']
    ordering = ['due_date']
    date_hierarchy = 'due_date'
    
    autocomplete_fields = ['project', 'assigned_by', 'assigned_to', 'approved_by']
    
    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">Yes</span>')
        return 'No'
    is_overdue_display.short_description = 'Overdue'
    is_overdue_display.admin_order_field = 'due_date'


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = [
        'file_name', 'project', 'file_type', 'file_size_display',
        'uploaded_by', 'approval_status', 'uploaded_date'
    ]
    list_filter = ['file_type', 'approval_status', 'uploaded_date']
    search_fields = ['file_name', 'project__title', 'uploaded_by__first_name']
    ordering = ['-uploaded_date']
    date_hierarchy = 'uploaded_date'
    
    autocomplete_fields = ['project', 'requirement', 'uploaded_by', 'approved_by']
    
    def file_size_display(self, obj):
        return f"{obj.file_size_mb} MB"
    file_size_display.short_description = 'File Size'


@admin.register(AccomplishmentReport)
class AccomplishmentReportAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'report_type', 'reporting_period', 
        'status', 'submitted_by', 'submission_date'
    ]
    list_filter = ['report_type', 'status', 'submission_date']
    search_fields = ['project__title', 'reporting_period', 'achievements']
    ordering = ['-submission_date']
    date_hierarchy = 'submission_date'
    
    autocomplete_fields = ['project', 'submitted_by', 'reviewed_by']


@admin.register(AttendanceTemplate)
class AttendanceTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'template_name', 'project', 'session_date', 
        'session_time', 'expected_participants', 'attendance_count'
    ]
    list_filter = ['session_date', 'is_active']
    search_fields = ['template_name', 'project__title', 'venue']
    ordering = ['-session_date']
    date_hierarchy = 'session_date'
    
    autocomplete_fields = ['project', 'created_by']
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            attendance_count=Count('attendance_records')
        )
    
    def attendance_count(self, obj):
        return obj.attendance_count
    attendance_count.short_description = 'Attendees'


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = [
        'participant_name', 'participant_email', 'template', 
        'status', 'check_in_time', 'check_out_time'
    ]
    list_filter = ['status', 'template__session_date']
    search_fields = ['participant_name', 'participant_email', 'organization']
    ordering = ['template__session_date', 'participant_name']
    
    autocomplete_fields = ['template']


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'evaluator_display', 'evaluation_type', 
        'rating', 'evaluation_date', 'is_anonymous'
    ]
    list_filter = ['evaluation_type', 'rating', 'is_anonymous', 'evaluation_date']
    search_fields = ['project__title', 'feedback', 'evaluator_name']
    ordering = ['-evaluation_date']
    date_hierarchy = 'evaluation_date'
    
    autocomplete_fields = ['project', 'evaluator', 'trainer']
    
    def evaluator_display(self, obj):
        if obj.is_anonymous:
            return obj.evaluator_name or "Anonymous"
        return obj.evaluator.full_name if obj.evaluator else "N/A"
    evaluator_display.short_description = 'Evaluator'


@admin.register(EvaluationLink)
class EvaluationLinkAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'link_type', 'unique_token', 'is_active', 
        'usage_count', 'expiration_date', 'is_expired_display'
    ]
    list_filter = ['link_type', 'is_active', 'expiration_date']
    search_fields = ['project__title', 'unique_token']
    ordering = ['-created_at']
    
    autocomplete_fields = ['project', 'created_by']
    readonly_fields = ['unique_token', 'usage_count']
    
    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">Yes</span>')
        return 'No'
    is_expired_display.short_description = 'Expired'


@admin.register(ProjectPerformance)
class ProjectPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'total_beneficiaries', 'completion_percentage', 
        'budget_utilization', 'impact_score', 'sustainability_rating'
    ]
    search_fields = ['project__title']
    ordering = ['-last_updated']
    
    autocomplete_fields = ['project', 'updated_by']
    readonly_fields = ['last_updated']


@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = [
        'subject', 'recipient_email', 'email_type', 
        'status', 'sent_date', 'is_automated'
    ]
    list_filter = ['email_type', 'status', 'is_automated', 'sent_date']
    search_fields = ['subject', 'recipient_email', 'recipient_name']
    ordering = ['-sent_date']
    date_hierarchy = 'sent_date'
    
    autocomplete_fields = ['project', 'sender']
    readonly_fields = ['sent_date', 'read_at']


# Custom admin site configuration
admin.site.site_header = "Extension Management System"
admin.site.site_title = "EMS Admin"
admin.site.index_title = "Extension Management Administration"





