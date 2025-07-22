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





