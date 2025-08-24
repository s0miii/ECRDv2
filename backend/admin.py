from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from .models import (
    CustomUser, College, Department, Project, ProjectMember, 
    Trainer, ProjectTrainer, DocumentaryRequirement, File, 
    AccomplishmentReport, AttendanceTemplate, AttendanceRecord,
    Evaluation, EvaluationLink, ProjectPerformance, Communication,
    ProjectStatusChoices, UserTypeChoices
)


# ============================================================================
# CONSTANTS 
# ============================================================================

# Admin Configuration Constants
DEFAULT_LIST_PER_PAGE = 25
SEARCH_HELP_TEXT = "Search across multiple fields"
DATE_HIERARCHY_FIELD = 'created_at'
MAX_INLINE_EXTRA_ITEMS = 1

# Status Colors - Centralized for consistency
STATUS_COLORS = {
    'PLANNING': '#6c757d',
    'APPROVED': '#17a2b8',
    'ONGOING': '#28a745',
    'COMPLETED': '#007bff',
    'SUSPENDED': '#ffc107',
    'CANCELLED': '#dc3545',
    'PENDING': '#6c757d',
    'SUBMITTED': '#17a2b8',
    'REJECTED': '#dc3545',
    'REVISION_NEEDED': '#ffc107',
    'SCHEDULED': '#6c757d',
    'DRAFT': '#6c757d',
    'SENT': '#17a2b8',
    'FAILED': '#dc3545',
    'DELIVERED': '#28a745'
}

# Performance Score Thresholds
EXCELLENT_SCORE_THRESHOLD = 4.0
GOOD_SCORE_THRESHOLD = 3.0
FAIR_SCORE_THRESHOLD = 2.0

# Display Formatting Constants
MAX_TEXT_DISPLAY_LENGTH = 50
CURRENCY_SYMBOL = '₱'
STAR_FULL = '★'
STAR_EMPTY = '☆'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_colored_status_display(status, color_map=None):
    """
    Return colored HTML status display.
    Single responsibility: Format status with appropriate color.
    """
    if color_map is None:
        color_map = STATUS_COLORS
    
    color = color_map.get(status, '#6c757d')
    display_name = status.replace('_', ' ').title()
    return format_html(
        '<span style="color: {}; font-weight: bold;">{}</span>',
        color, display_name
    )


def get_star_rating_display(rating, max_rating=5):
    """
    Return star rating HTML display.
    Single responsibility: Convert numeric rating to visual stars.
    """
    full_stars = int(rating)
    empty_stars = max_rating - full_stars
    stars = STAR_FULL * full_stars + STAR_EMPTY * empty_stars
    return format_html(
        '<span title="{}/{}" style="color: #ffc107;">{}</span>', 
        rating, max_rating, stars
    )


def get_progress_bar_html(percentage, width=100):
    """
    Return progress bar HTML.
    Single responsibility: Create visual progress representation.
    """
    color = _get_percentage_color(percentage)
    return format_html(
        '<div style="width: {}px; background: #f0f0f0; border-radius: 3px;">'
        '<div style="width: {}%; height: 20px; background: {}; border-radius: 3px; '
        'text-align: center; color: white; font-size: 12px; line-height: 20px;">'
        '{}%</div></div>',
        width, percentage, color, percentage
    )


def _get_percentage_color(percentage):
    """Private helper for color coding percentages."""
    if percentage >= 80:
        return '#28a745'  # Green
    elif percentage >= 60:
        return '#ffc107'  # Yellow
    elif percentage >= 40:
        return '#fd7e14'  # Orange
    else:
        return '#dc3545'  # Red


def truncate_text_display(text, max_length=MAX_TEXT_DISPLAY_LENGTH):
    """
    Truncate text for display purposes.
    Single responsibility: Format text for UI display.
    """
    if not text:
        return '-'
    return text if len(text) <= max_length else f"{text[:max_length-3]}..."


def format_currency_display(amount):
    """
    Format currency for display.
    Single responsibility: Format monetary values.
    """
    return f"{CURRENCY_SYMBOL}{amount:,.2f}" if amount else '-'


# ============================================================================
# BASE CLASSES 
# ============================================================================

class BaseModelAdmin(admin.ModelAdmin):
    """
    Base admin class with common configurations.
    Implements DRY by centralizing common admin behavior.
    """
    list_per_page = DEFAULT_LIST_PER_PAGE
    show_full_result_count = False
    
    def get_readonly_fields(self, request, obj=None):
        """
        Automatically make timestamp fields readonly.
        Prevents accidental modification of audit trail fields.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Add common timestamp fields if they exist on the model
        timestamp_fields = ['created_at', 'updated_at', 'sent_date', 'uploaded_date']
        for field_name in timestamp_fields:
            if (hasattr(self.model, field_name) and 
                field_name not in readonly_fields):
                readonly_fields.append(field_name)
        
        return readonly_fields


class BaseTabularInline(admin.TabularInline):
    """
    Base inline class with common configurations.
    Implements consistent inline behavior across the application.
    """
    extra = MAX_INLINE_EXTRA_ITEMS
    show_change_link = True
    
    def get_readonly_fields(self, request, obj=None):
        """Apply same readonly logic as base admin."""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if hasattr(self.model, 'assigned_date') and 'assigned_date' not in readonly_fields:
            readonly_fields.append('assigned_date')
        return readonly_fields


# ============================================================================
# CUSTOM FILTERS
# ============================================================================

class GenericStatusFilter(SimpleListFilter):
    """
    Reusable status filter for any model with status field.
    Single responsibility: Filter by status values.
    """
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        if hasattr(model_admin.model, 'status'):
            field = model_admin.model._meta.get_field('status')
            if hasattr(field, 'choices'):
                return field.choices
        return ()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class ProjectActivityFilter(SimpleListFilter):
    """
    Filter projects by activity status.
    Single responsibility: Categorize projects by active/inactive status.
    """
    title = 'Project Activity'
    parameter_name = 'activity_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active Projects'),
            ('inactive', 'Inactive Projects'),
        )

    def queryset(self, request, queryset):
        active_statuses = ['APPROVED', 'ONGOING']
        if self.value() == 'active':
            return queryset.filter(status__in=active_statuses)
        elif self.value() == 'inactive':
            return queryset.exclude(status__in=active_statuses)
        return queryset


# ============================================================================
# INLINE CLASSES
# ============================================================================

class DepartmentInline(BaseTabularInline):
    """Inline for managing departments within colleges."""
    model = Department
    fields = ['department_code', 'department_name', 'department_head']
    autocomplete_fields = ['department_head']


class ProjectMemberInline(BaseTabularInline):
    """Inline for managing project team members."""
    model = ProjectMember
    fields = ['user', 'role', 'assigned_date', 'is_active']
    readonly_fields = ['assigned_date']
    autocomplete_fields = ['user']


class ProjectTrainerInline(BaseTabularInline):
    """Inline for managing project trainers."""
    model = ProjectTrainer
    fields = ['trainer', 'training_topic', 'training_date', 'duration_hours', 'status']
    autocomplete_fields = ['trainer']


class DocumentaryRequirementInline(BaseTabularInline):
    """Inline for managing project requirements."""
    model = DocumentaryRequirement
    fields = ['requirement_name', 'due_date', 'status', 'assigned_to']
    autocomplete_fields = ['assigned_to']


class FileInline(BaseTabularInline):
    """Inline for managing project files."""
    model = File
    fields = ['file_name', 'file_type', 'approval_status']
    readonly_fields = ['uploaded_date', 'file_size']


# ============================================================================
# MAIN ADMIN CLASSES 
# ============================================================================

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Enhanced user admin with improved fieldsets and search.
    Fixed: Inherits from UserAdmin only to avoid MRO conflicts.
    """
    
    list_display = [
        'email', 'full_name_display', 'user_type', 'college_display', 
        'department_display', 'is_active', 'date_joined'
    ]
    
    list_filter = [
        'user_type', 'is_active', 'college', 'department',
        'date_joined', 'is_staff'
    ]
    
    # Enhanced search - following recommendation
    search_fields = [
        'email', 'first_name', 'last_name', 'employee_id', 'position',
        'college__college_name', 'department__department_name'
    ]
    
    ordering = ['last_name', 'first_name']
    list_select_related = ['college', 'department']
    list_per_page = DEFAULT_LIST_PER_PAGE

    # Fieldsets for Clarity - following recommendation
    fieldsets = (
        ('Account Information', {
            'fields': ('username', 'password'),
            'classes': ('wide',)
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'last_name', 'email', 
                'phone_number', 'employee_id', 'position'
            ),
            'classes': ('wide',)
        }),
        ('Institutional Assignment', {
            'fields': ('user_type', 'college', 'department'),
            'classes': ('wide',)
        }),
        ('Permissions & Access', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    # Display methods following "Self-Explanatory Code" principle
    def full_name_display(self, obj):
        """Display user's full name."""
        return obj.full_name
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'

    def college_display(self, obj):
        """Display college code or indication of no assignment."""
        return obj.college.college_code if obj.college else 'No College'
    college_display.short_description = 'College'
    college_display.admin_order_field = 'college__college_code'

    def department_display(self, obj):
        """Display department code or indication of no assignment."""
        return obj.department.department_code if obj.department else 'No Department'
    department_display.short_description = 'Department'
    department_display.admin_order_field = 'department__department_code'


@admin.register(College)
class CollegeAdmin(BaseModelAdmin):
    """
    Enhanced college admin with inline departments.
    Implements: Inline Admin for Relationships
    """
    
    list_display = [
        'college_code', 'college_name', 'dean_display', 
        'extension_coordinator_display', 'department_count', 
        'project_count', 'user_count'
    ]
    
    list_filter = ['created_at']
    search_fields = ['college_name', 'college_code']
    ordering = ['college_code']
    
    # Inline Admin for Relationships - following recommendation
    inlines = [DepartmentInline]

    def get_queryset(self, request):
        """Optimize queries with annotations."""
        return super().get_queryset(request).select_related(
            'dean', 'extension_coordinator'
        ).annotate(
            department_count=Count('departments', distinct=True),
            project_count=Count('projects', distinct=True),
            user_count=Count('users', distinct=True)
        )

    # Display methods with meaningful names
    def dean_display(self, obj):
        """Display dean name with fallback."""
        return obj.dean.full_name if obj.dean else 'Not Assigned'
    dean_display.short_description = 'Dean'

    def extension_coordinator_display(self, obj):
        """Display extension coordinator with fallback."""
        return obj.extension_coordinator.full_name if obj.extension_coordinator else 'Not Assigned'
    extension_coordinator_display.short_description = 'Extension Coordinator'

    def department_count(self, obj):
        """Display department count."""
        return obj.department_count
    department_count.short_description = 'Departments'
    department_count.admin_order_field = 'department_count'

    def project_count(self, obj):
        """Display project count."""
        return obj.project_count
    project_count.short_description = 'Projects'
    project_count.admin_order_field = 'project_count'

    def user_count(self, obj):
        """Display user count."""
        return obj.user_count
    user_count.short_description = 'Users'
    user_count.admin_order_field = 'user_count'


@admin.register(Department)
class DepartmentAdmin(BaseModelAdmin):
    """
    Department admin with college relationship management.
    """
    
    list_display = [
        'department_code', 'department_name', 'college_display', 
        'department_head_display', 'user_count'
    ]
    
    list_filter = ['college', 'created_at']
    search_fields = ['department_name', 'department_code', 'college__college_name']
    ordering = ['college__college_code', 'department_code']
    list_select_related = ['college', 'department_head']
    autocomplete_fields = ['college', 'department_head']

    def get_queryset(self, request):
        """Optimize with user count annotation."""
        return super().get_queryset(request).annotate(
            user_count=Count('users', distinct=True)
        )

    def college_display(self, obj):
        """Display college code."""
        return obj.college.college_code
    college_display.short_description = 'College'
    college_display.admin_order_field = 'college__college_code'

    def department_head_display(self, obj):
        """Display department head with fallback."""
        return obj.department_head.full_name if obj.department_head else 'Not Assigned'
    department_head_display.short_description = 'Department Head'

    def user_count(self, obj):
        """Display user count."""
        return obj.user_count
    user_count.short_description = 'Users'
    user_count.admin_order_field = 'user_count'


@admin.register(Project)
class ProjectAdmin(BaseModelAdmin):
    """
    Enhanced project admin with comprehensive inlines and fieldsets.
    Implements: All recommendations (inlines, fieldsets, search, readonly)
    """
    
    list_display = [
        'title', 'project_type', 'status_display', 'project_leader_display',
        'college_display', 'timeline_display', 'budget_display', 'member_count'
    ]
    
    list_filter = [
        ProjectActivityFilter, 'project_type', 'college', 'department', 
        'start_date', 'created_at'
    ]
    
    # Enhanced search - following recommendation
    search_fields = [
        'title', 'description', 'location',
        'project_leader__first_name', 'project_leader__last_name',
        'college__college_name', 'department__department_name'
    ]
    
    ordering = ['-created_at']
    date_hierarchy = 'start_date'
    list_select_related = ['project_leader', 'college', 'department']

    # Fieldsets for Clarity - following recommendation
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'project_type', 'status'),
            'classes': ('wide',)
        }),
        ('Timeline & Budget', {
            'fields': ('start_date', 'end_date', 'budget', 'location'),
            'classes': ('wide',)
        }),
        ('Institutional Assignment', {
            'fields': (
                'project_leader', 'college', 'department', 
                'expected_beneficiaries'
            ),
            'classes': ('wide',)
        }),
    )

    # Inline Admin for Relationships - following recommendation
    inlines = [
        ProjectMemberInline, 
        ProjectTrainerInline, 
        DocumentaryRequirementInline, 
        FileInline
    ]

    autocomplete_fields = ['project_leader', 'college', 'department']

    def get_queryset(self, request):
        """Optimize with member count annotation."""
        return super().get_queryset(request).annotate(
            member_count=Count('members', distinct=True)
        )

    # Display methods following "Self-Explanatory Code" principle
    def status_display(self, obj):
        """Display status with appropriate color coding."""
        return get_colored_status_display(obj.status)
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'

    def project_leader_display(self, obj):
        """Display project leader's full name."""
        return obj.project_leader.full_name
    project_leader_display.short_description = 'Project Leader'
    project_leader_display.admin_order_field = 'project_leader__first_name'

    def college_display(self, obj):
        """Display college code."""
        return obj.college.college_code
    college_display.short_description = 'College'
    college_display.admin_order_field = 'college__college_code'

    def timeline_display(self, obj):
        """Display project timeline in readable format."""
        return f"{obj.start_date} to {obj.end_date}"
    timeline_display.short_description = 'Timeline'

    def budget_display(self, obj):
        """Display formatted budget amount."""
        return format_currency_display(obj.budget)
    budget_display.short_description = 'Budget'
    budget_display.admin_order_field = 'budget'

    def member_count(self, obj):
        """Display team member count."""
        return obj.member_count
    member_count.short_description = 'Members'
    member_count.admin_order_field = 'member_count'


@admin.register(ProjectMember)
class ProjectMemberAdmin(BaseModelAdmin):
    """
    Project member admin for managing team assignments.
    """
    
    list_display = [
        'user_display', 'project_display', 'role', 
        'assigned_date', 'is_active'
    ]
    
    list_filter = ['role', 'is_active', 'assigned_date']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'project__title'
    ]
    
    ordering = ['-assigned_date']
    list_select_related = ['user', 'project']
    autocomplete_fields = ['user', 'project']

    def user_display(self, obj):
        """Display user's full name."""
        return obj.user.full_name
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__first_name'

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 40)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'


@admin.register(Trainer)
class TrainerAdmin(BaseModelAdmin):
    """
    Trainer admin with internal/external categorization.
    """
    
    list_display = [
        'trainer_name', 'email', 'trainer_type_display', 
        'expertise_display', 'project_count'
    ]
    
    list_filter = ['is_internal', 'created_at']
    search_fields = ['trainer_name', 'email', 'expertise']
    ordering = ['trainer_name']

    def get_queryset(self, request):
        """Optimize with project count annotation."""
        return super().get_queryset(request).annotate(
            project_count=Count('project_assignments', distinct=True)
        )

    def trainer_type_display(self, obj):
        """Display trainer type with color coding."""
        if obj.is_internal:
            return format_html('<span style="color: #28a745;">Internal</span>')
        return format_html('<span style="color: #17a2b8;">External</span>')
    trainer_type_display.short_description = 'Type'
    trainer_type_display.admin_order_field = 'is_internal'

    def expertise_display(self, obj):
        """Display truncated expertise."""
        return truncate_text_display(obj.expertise, 60)
    expertise_display.short_description = 'Expertise'

    def project_count(self, obj):
        """Display project assignment count."""
        return obj.project_count
    project_count.short_description = 'Projects'
    project_count.admin_order_field = 'project_count'


@admin.register(ProjectTrainer)
class ProjectTrainerAdmin(BaseModelAdmin):
    """
    Project trainer assignment admin.
    """
    
    list_display = [
        'trainer_display', 'project_display', 'training_topic',
        'training_date', 'duration_hours', 'status_display'
    ]
    
    list_filter = ['status', 'training_date', 'trainer__is_internal']
    search_fields = [
        'trainer__trainer_name', 'project__title', 'training_topic'
    ]
    
    ordering = ['-training_date']
    list_select_related = ['trainer', 'project']
    autocomplete_fields = ['trainer', 'project']

    def trainer_display(self, obj):
        """Display trainer name."""
        return obj.trainer.trainer_name
    trainer_display.short_description = 'Trainer'
    trainer_display.admin_order_field = 'trainer__trainer_name'

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 30)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'

    def status_display(self, obj):
        """Display status with color coding."""
        return get_colored_status_display(obj.status)
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'


@admin.register(DocumentaryRequirement)
class DocumentaryRequirementAdmin(BaseModelAdmin):
    """
    Enhanced requirement admin with overdue detection.
    Implements: Search Optimization, Status Display
    """
    
    list_display = [
        'requirement_name', 'project_display', 'assigned_to_display', 
        'due_date', 'status_display', 'overdue_indicator'
    ]
    
    list_filter = ['status', 'due_date', 'created_at']
    
    # Enhanced search - following recommendation
    search_fields = [
        'requirement_name', 'description',
        'project__title', 
        'assigned_to__first_name', 'assigned_to__last_name',
        'assigned_to__email'
    ]
    
    ordering = ['due_date', 'requirement_name']
    date_hierarchy = 'due_date'
    list_select_related = ['project', 'assigned_to', 'assigned_by']
    
    autocomplete_fields = ['project', 'assigned_by', 'assigned_to', 'approved_by']

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 40)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'

    def assigned_to_display(self, obj):
        """Display assigned user's full name."""
        return obj.assigned_to.full_name
    assigned_to_display.short_description = 'Assigned To'
    assigned_to_display.admin_order_field = 'assigned_to__first_name'

    def status_display(self, obj):
        """Display status with color coding."""
        return get_colored_status_display(obj.status)
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'

    def overdue_indicator(self, obj):
        """Display overdue status with visual indicator."""
        if obj.is_overdue:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Overdue</span>'
            )
        return format_html('<span style="color: green;">✓ On Time</span>')
    overdue_indicator.short_description = 'Deadline Status'


@admin.register(File)
class FileAdmin(BaseModelAdmin):
    """
    File management admin with approval workflow.
    """
    
    list_display = [
        'file_name', 'project_display', 'file_type', 'file_size_display',
        'uploaded_by_display', 'uploaded_date', 'approval_status_display'
    ]
    
    list_filter = [
        'file_type', 'approval_status', 'uploaded_date'
    ]
    
    search_fields = [
        'file_name', 'project__title',
        'uploaded_by__first_name', 'uploaded_by__last_name'
    ]
    
    ordering = ['-uploaded_date']
    list_select_related = ['project', 'uploaded_by', 'approved_by']
    autocomplete_fields = ['project', 'requirement', 'uploaded_by', 'approved_by']

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 30)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'

    def file_size_display(self, obj):
        """Display file size in MB."""
        return f"{obj.file_size_mb} MB"
    file_size_display.short_description = 'Size'
    file_size_display.admin_order_field = 'file_size'

    def uploaded_by_display(self, obj):
        """Display uploader's full name."""
        return obj.uploaded_by.full_name
    uploaded_by_display.short_description = 'Uploaded By'
    uploaded_by_display.admin_order_field = 'uploaded_by__first_name'

    def approval_status_display(self, obj):
        """Display approval status with color coding."""
        return get_colored_status_display(obj.approval_status)
    approval_status_display.short_description = 'Status'
    approval_status_display.admin_order_field = 'approval_status'


@admin.register(AccomplishmentReport)
class AccomplishmentReportAdmin(BaseModelAdmin):
    """
    Accomplishment report admin with review workflow.
    """
    
    list_display = [
        'project_display', 'report_type', 'reporting_period',
        'submitted_by_display', 'submission_date', 'status_display'
    ]
    
    list_filter = ['report_type', 'status', 'submission_date']
    search_fields = [
        'project__title', 'reporting_period',
        'submitted_by__first_name', 'submitted_by__last_name'
    ]
    
    ordering = ['-submission_date']
    list_select_related = ['project', 'submitted_by', 'reviewed_by']
    autocomplete_fields = ['project', 'submitted_by', 'reviewed_by']

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 30)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'

    def submitted_by_display(self, obj):
        """Display submitter's full name."""
        return obj.submitted_by.full_name
    submitted_by_display.short_description = 'Submitted By'
    submitted_by_display.admin_order_field = 'submitted_by__first_name'

    def status_display(self, obj):
        """Display status with color coding."""
        return get_colored_status_display(obj.status)
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'


@admin.register(AttendanceTemplate)
class AttendanceTemplateAdmin(BaseModelAdmin):
    """
    Attendance template admin for session management.
    """
    
    list_display = [
        'template_name', 'project_display', 'session_date',
        'session_time', 'expected_participants', 'is_active'
    ]
    
    list_filter = ['is_active', 'session_date', 'created_at']
    search_fields = ['template_name', 'project__title', 'venue']
    ordering = ['-session_date', '-session_time']
    list_select_related = ['project', 'created_by']
    autocomplete_fields = ['project', 'created_by']

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 30)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(BaseModelAdmin):
    """
    Attendance record admin for participant tracking.
    """
    
    list_display = [
        'participant_name', 'template_display', 'participant_email',
        'organization', 'check_in_time', 'status_display'
    ]
    
    list_filter = ['status', 'template__session_date']
    search_fields = [
        'participant_name', 'participant_email', 'organization',
        'template__template_name'
    ]
    
    ordering = ['template__session_date', 'participant_name']
    list_select_related = ['template', 'template__project']
    autocomplete_fields = ['template']

    def template_display(self, obj):
        """Display template name."""
        return obj.template.template_name
    template_display.short_description = 'Session'
    template_display.admin_order_field = 'template__template_name'

    def status_display(self, obj):
        """Display attendance status with color coding."""
        return get_colored_status_display(obj.status)
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'


@admin.register(Evaluation)
class EvaluationAdmin(BaseModelAdmin):
    """
    Evaluation admin with rating display.
    """
    
    list_display = [
        'project_display', 'evaluator_display', 'evaluation_type',
        'rating_display', 'evaluation_date', 'is_anonymous'
    ]
    
    list_filter = [
        'evaluation_type', 'rating', 'is_anonymous', 'evaluation_date'
    ]
    
    search_fields = [
        'project__title', 'evaluator__first_name', 'evaluator__last_name',
        'evaluator_name', 'evaluator_email', 'feedback'
    ]
    
    ordering = ['-evaluation_date']
    list_select_related = ['project', 'evaluator', 'trainer']
    autocomplete_fields = ['project', 'evaluator', 'trainer']

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 30)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'

    def evaluator_display(self, obj):
        """Display evaluator name (anonymous if applicable)."""
        if obj.is_anonymous:
            return obj.evaluator_name or 'Anonymous'
        return obj.evaluator.full_name if obj.evaluator else 'Unknown'
    evaluator_display.short_description = 'Evaluator'

    def rating_display(self, obj):
        """Display star rating."""
        return get_star_rating_display(obj.rating)
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'


@admin.register(EvaluationLink)
class EvaluationLinkAdmin(BaseModelAdmin):
    """
    Evaluation link admin for managing shareable links.
    """
    
    list_display = [
        'project_display', 'link_type', 'expiration_date',
        'usage_display', 'is_active', 'created_by_display'
    ]
    
    list_filter = ['link_type', 'is_active', 'expiration_date', 'created_at']
    search_fields = ['project__title', 'created_by__first_name', 'created_by__last_name']
    ordering = ['-created_at']
    list_select_related = ['project', 'created_by']
    autocomplete_fields = ['project', 'created_by']
    readonly_fields = ['unique_token', 'usage_count']

    def project_display(self, obj):
        """Display truncated project title."""
        return truncate_text_display(obj.project.title, 30)
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'

    def usage_display(self, obj):
        """Display usage count with limit."""
        if obj.max_usage:
            return f"{obj.usage_count}/{obj.max_usage}"
        return f"{obj.usage_count}/∞"
    usage_display.short_description = 'Usage'
    usage_display.admin_order_field = 'usage_count'

    def created_by_display(self, obj):
        """Display creator's full name."""
        return obj.created_by.full_name
    created_by_display.short_description = 'Created By'
    created_by_display.admin_order_field = 'created_by__first_name'


@admin.register(ProjectPerformance)
class ProjectPerformanceAdmin(BaseModelAdmin):
    """
    Project performance metrics admin.
    """
    
    list_display = [
        'project_display', 'completion_percentage_display',
        'budget_utilization_display', 'impact_score_display',
        'overall_score_display', 'last_updated'
    ]
    
    list_filter = ['last_updated']
    search_fields = ['project__title']
    ordering = ['-last_updated']
    list_select_related = ['project', 'updated_by']
    autocomplete_fields = ['project', 'updated_by']

    def project_display(self, obj):
        """Display project title."""
        return obj.project.title
    project_display.short_description = 'Project'
    project_display.admin_order_field = 'project__title'

    def completion_percentage_display(self, obj):
        """Display completion as progress bar."""
        return get_progress_bar_html(float(obj.completion_percentage), 80)
    completion_percentage_display.short_description = 'Completion'
    completion_percentage_display.admin_order_field = 'completion_percentage'

    def budget_utilization_display(self, obj):
        """Display budget utilization as progress bar."""
        return get_progress_bar_html(float(obj.budget_utilization), 80)
    budget_utilization_display.short_description = 'Budget Usage'
    budget_utilization_display.admin_order_field = 'budget_utilization'

    def impact_score_display(self, obj):
        """Display impact score as stars."""
        return get_star_rating_display(float(obj.impact_score))
    impact_score_display.short_description = 'Impact'
    impact_score_display.admin_order_field = 'impact_score'

    def overall_score_display(self, obj):
        """Display overall performance score as stars."""
        return get_star_rating_display(obj.overall_performance_score)
    overall_score_display.short_description = 'Overall'


@admin.register(Communication)
class CommunicationAdmin(BaseModelAdmin):
    """
    Communication admin for email tracking.
    """
    
    list_display = [
        'subject_display', 'recipient_email', 'email_type',
        'status_display', 'sent_date', 'is_automated', 'is_read'
    ]
    
    list_filter = [
        'email_type', 'status', 'is_automated', 'read_at', 'sent_date'
    ]
    
    search_fields = [
        'subject', 'recipient_email', 'recipient_name',
        'sender__first_name', 'sender__last_name'
    ]
    
    ordering = ['-sent_date']
    list_select_related = ['sender', 'project']
    autocomplete_fields = ['sender', 'project']

    def subject_display(self, obj):
        """Display truncated subject."""
        return truncate_text_display(obj.subject, 50)
    subject_display.short_description = 'Subject'
    subject_display.admin_order_field = 'subject'

    def status_display(self, obj):
        """Display communication status with color coding."""
        return get_colored_status_display(obj.status)
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'


# ============================================================================
# ADMIN SITE CONFIGURATION
# ============================================================================

# Configure admin site appearance
admin.site.site_header = "Extension Management System"
admin.site.site_title = "EMS Admin"
admin.site.index_title = "Extension Management Administration"

# Enable autocomplete for all registered models
admin.site.enable_nav_sidebar = False  # Optional: disable sidebar for cleaner look