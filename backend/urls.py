# app-level urls.py
""" 
This module defines API endpoints for the system,
organizing ViewSets with URL patterns following RESTful conventions.

URL Structure:
- /api/auth/ - Authentication endpoints
- /api/users/ - User management
- /api/colleges/ - College Management
- /api/departments/ - Department Management
- /api/projects/ - Project management
- /api/members/ - Project membership
- /api/trainers/ - Trainer management
- /api/project-trainers/ - Project-trainer assignments
- /api/requirements/ - Documentary requirements
- /api/files/ - File management
- /api/reports/ - Accomplishment reports
- /api/attendance-templates/ - Attendance session templates
- /api/attendance-records/ - Individual attendance records
- /api/evaluations/ - Project and trainer evaluations
- /api/evaluation-links/ - shareable evaluation links
- /api/performance/ - Project performance metrics
- /api/communications/ - Email communications and notifications
- /api/dashboard/ - Dashboard analytics and system health
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import ViewSets following separtion of concerns
from .views import (
    # Authentication ViewSets
    AuthenticationViewSet,
    
    # User Management ViewSets
    CustomUserViewSet,
    
    # Organizational Structure ViewSets  
    CollegeViewSet,
    DepartmentViewSet,
    
    # Project Management ViewSets
    ProjectViewSet,
    ProjectPerformanceViewSet,
    
    # Membership and Team ViewSets
    ProjectMemberViewSet,
    TrainerViewSet,
    ProjectTrainerViewSet,
    
    # Document and File Management ViewSets
    DocumentaryRequirementViewSet,
    FileViewSet,
    AccomplishmentReportViewSet,
    
    # Attendance Management ViewSets
    AttendanceTemplateViewSet,
    AttendanceRecordViewSet,
    
    # Evaluation System ViewSets
    EvaluationViewSet,
    EvaluationLinkViewSet,
    
    # Communication System ViewSets
    CommunicationViewSet,
    
    # Dashboard and Analytics ViewSets
    DashboardViewSet,
    SystemHealthViewSet,
    DataExportViewSet,
    NotificationViewSet,
)

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# API Version Prefix
API_VERSION_PREFIX = 'api'

# URL Namespace
APP_NAMESPACE = 'extension_management'

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

def create_api_router():
    """ 
    Create and configure here the main API router.

    Single responsibility: Router setup and ViewSet registration.
    Centralizes routing configuration for maintainability.

    Returns:
        DefaultRouter: Configured router with all ViewSets registered
    """
    router = DefaultRouter()

    # Authentication endpoints
    router.register(
        r'auth',
        AuthenticationViewSet,
        basename='authentication'
    )

    # User management endpoints
    router.register(
        r'users',
        CustomUserViewSet,
        basename='users'
    )

    # Organizational structure endpoints
    router.register(
        r'colleges',
        CollegeViewSet,
        basename='colleges'
    )
    router.register(
        r'departments',
        DepartmentViewSet,
        basename='departments'
    )

    # Project management endpoints
    router.register(
        r'projects',
        ProjectViewSet,
        basename='projects'
    )
    router.register(
        r'performance',
        ProjectPerformanceViewSet,
        basename='project-performance'
    )

    # team and membership endpoints
    router.register(
        r'members',
        ProjectMemberViewSet,
        basename='project-members'
    )
    router.register(
        r'trainers',
        TrainerViewSet,
        basename='trainers'
    )
    router.register(
        r'project-trainers',
        ProjectTrainerViewSet,
        basename='project-trainers'
    )

    # Document and file management endpoints
    router.register(
        r'requirements',
        DocumentaryRequirementViewSet,
        basename='requirements'
    )
    router.register(
        r'files',
        FileViewSet,
        basename='files'
    )
    router.register(
        r'reports',
        AccomplishmentReportViewSet,
        basename='reports'
    )

    # Attendance management endpoints
    router.register(
        r'attendance-templates',
        AttendanceTemplateViewSet,
        basename='attendance-templates'
    )
    router.register(
        r'attendance-records',
        AttendanceRecordViewSet,
        basename='attendance-records'
    )

    # Evaluation system endpoints
    router.register(
        r'evaluations',
        EvaluationViewSet,
        basename='evaluations'
    )
    router.register(
        r'evaluation-links',
        EvaluationLinkViewSet,
        basename='evaluation-links'
    )

    # Communication system endpoints
    router.register(
        r'communications',
        CommunicationViewSet,
        basename='communications'
    )

    # Dashboard and system management endpoints
    router.register(
        r'dashboard',
        DashboardViewSet,
        basename='dashboard'
    )
    router.register(
        r'system-health',
        SystemHealthViewSet,
        basename='system-health'
    )
    router.register(
        r'data-export',
        DataExportViewSet,
        basename='data-export'
    )
    router.register(
        r'notifications',
        NotificationViewSet,
        basename='notifications'
    )

    return router


# ============================================================================
# URL PATTERNS CONFIGURATION
# ============================================================================

# Create router instance
api_router = create_api_router()

# define URL patterns
urlpatterns = [
    # API endpoints - all routes under /api/ prefix
    path(f'{API_VERSION_PREFIX}/', include(api_router.urls)),

    # DRF browsable API authentication
    path(f'{API_VERSION_PREFIX}/auth/', include('rest_framework.urls')),
]

# Set app namespace for URL reversing
app_name = APP_NAMESPACE


# ============================================================================
# URL PATTERN DOCUMENTATION
# ============================================================================

"""
Generated URL Patterns:

Authentication:
- POST /api/auth/login/ - User login
- POST /api/auth/register/ - User registration  
- POST /api/auth/logout/ - User logout

Users:
- GET /api/users/ - List users
- POST /api/users/ - Create user
- GET /api/users/{id}/ - Retrieve user
- PUT /api/users/{id}/ - Update user
- DELETE /api/users/{id}/ - Delete user
- GET /api/users/profile/ - Current user profile
- POST /api/users/{id}/activate/ - Activate user
- POST /api/users/{id}/deactivate/ - Deactivate user
- GET /api/users/by_role/ - Filter users by role

Colleges:
- GET /api/colleges/ - List colleges
- POST /api/colleges/ - Create college
- GET /api/colleges/{id}/ - Retrieve college
- PUT /api/colleges/{id}/ - Update college
- DELETE /api/colleges/{id}/ - Delete college
- GET /api/colleges/{id}/departments/ - College departments
- GET /api/colleges/{id}/projects/ - College projects

Departments:
- GET /api/departments/ - List departments
- POST /api/departments/ - Create department
- GET /api/departments/{id}/ - Retrieve department
- PUT /api/departments/{id}/ - Update department
- DELETE /api/departments/{id}/ - Delete department
- GET /api/departments/{id}/users/ - Department users

Projects:
- GET /api/projects/ - List projects
- POST /api/projects/ - Create project
- GET /api/projects/{id}/ - Retrieve project
- PUT /api/projects/{id}/ - Update project
- DELETE /api/projects/{id}/ - Delete project
- GET /api/projects/summary/ - Project statistics
- POST /api/projects/search/ - Advanced search
- GET /api/projects/export/ - Export projects
- POST /api/projects/{id}/change_status/ - Change project status
- POST /api/projects/bulk_operations/ - Bulk operations

Project Members:
- GET /api/members/ - List project members
- POST /api/members/ - Assign member to project
- GET /api/members/{id}/ - Retrieve member
- PUT /api/members/{id}/ - Update member
- DELETE /api/members/{id}/ - Remove member
- POST /api/members/assign_member/ - Assign member with validation
- POST /api/members/{id}/remove_member/ - Remove member from project

Trainers:
- GET /api/trainers/ - List trainers
- POST /api/trainers/ - Create trainer
- GET /api/trainers/{id}/ - Retrieve trainer
- PUT /api/trainers/{id}/ - Update trainer
- DELETE /api/trainers/{id}/ - Delete trainer
- GET /api/trainers/available/ - Available trainers

Project Trainers:
- GET /api/project-trainers/ - List project trainer assignments
- POST /api/project-trainers/ - Create assignment
- GET /api/project-trainers/{id}/ - Retrieve assignment
- PUT /api/project-trainers/{id}/ - Update assignment
- DELETE /api/project-trainers/{id}/ - Delete assignment

Requirements:
- GET /api/requirements/ - List requirements
- POST /api/requirements/ - Create requirement
- GET /api/requirements/{id}/ - Retrieve requirement
- PUT /api/requirements/{id}/ - Update requirement
- DELETE /api/requirements/{id}/ - Delete requirement
- POST /api/requirements/{id}/submit/ - Submit requirement
- POST /api/requirements/{id}/approve/ - Approve requirement
- POST /api/requirements/{id}/reject/ - Reject requirement

Files:
- GET /api/files/ - List files
- POST /api/files/ - Upload file
- GET /api/files/{id}/ - Retrieve file
- PUT /api/files/{id}/ - Update file
- DELETE /api/files/{id}/ - Delete file
- GET /api/files/{id}/download/ - Download file

Reports:
- GET /api/reports/ - List reports
- POST /api/reports/ - Create report
- GET /api/reports/{id}/ - Retrieve report
- PUT /api/reports/{id}/ - Update report
- DELETE /api/reports/{id}/ - Delete report
- POST /api/reports/{id}/submit_for_review/ - Submit for review
- POST /api/reports/{id}/approve_report/ - Approve report
- POST /api/reports/{id}/request_revision/ - Request revision
- GET /api/reports/pending_reviews/ - Pending reviews

Attendance Templates:
- GET /api/attendance-templates/ - List templates
- POST /api/attendance-templates/ - Create template
- GET /api/attendance-templates/{id}/ - Retrieve template
- PUT /api/attendance-templates/{id}/ - Update template
- DELETE /api/attendance-templates/{id}/ - Delete template
- GET /api/attendance-templates/{id}/attendance_records/ - Get records
- POST /api/attendance-templates/{id}/generate_attendance_link/ - Generate link
- POST /api/attendance-templates/{id}/deactivate_template/ - Deactivate

Attendance Records:
- GET /api/attendance-records/ - List records
- POST /api/attendance-records/ - Create record
- GET /api/attendance-records/{id}/ - Retrieve record
- PUT /api/attendance-records/{id}/ - Update record
- DELETE /api/attendance-records/{id}/ - Delete record
- POST /api/attendance-records/{id}/check_in/ - Check in participant
- POST /api/attendance-records/{id}/check_out/ - Check out participant
- POST /api/attendance-records/bulk_mark_attendance/ - Bulk attendance

Evaluations:
- GET /api/evaluations/ - List evaluations
- POST /api/evaluations/ - Create evaluation
- GET /api/evaluations/{id}/ - Retrieve evaluation
- PUT /api/evaluations/{id}/ - Update evaluation
- DELETE /api/evaluations/{id}/ - Delete evaluation
- POST /api/evaluations/anonymous_evaluation/ - Submit anonymous evaluation
- GET /api/evaluations/project_statistics/ - Project evaluation stats
- GET /api/evaluations/trainer_ratings/ - Trainer ratings

Evaluation Links:
- GET /api/evaluation-links/ - List links
- POST /api/evaluation-links/ - Create link
- GET /api/evaluation-links/{id}/ - Retrieve link
- PUT /api/evaluation-links/{id}/ - Update link
- DELETE /api/evaluation-links/{id}/ - Delete link
- GET /api/evaluation-links/validate_token/ - Validate token
- POST /api/evaluation-links/{id}/increment_usage/ - Increment usage
- POST /api/evaluation-links/{id}/extend_expiration/ - Extend expiration

Performance:
- GET /api/performance/ - List performance metrics
- POST /api/performance/ - Create metrics
- GET /api/performance/{id}/ - Retrieve metrics
- PUT /api/performance/{id}/ - Update metrics
- DELETE /api/performance/{id}/ - Delete metrics
- GET /api/performance/dashboard_metrics/ - Dashboard metrics
- POST /api/performance/{id}/update_metrics/ - Update specific metrics

Communications:
- GET /api/communications/ - List communications
- POST /api/communications/ - Create communication
- GET /api/communications/{id}/ - Retrieve communication
- PUT /api/communications/{id}/ - Update communication
- DELETE /api/communications/{id}/ - Delete communication
- POST /api/communications/send_notification/ - Send notification
- GET /api/communications/delivery_statistics/ - Delivery stats
- POST /api/communications/{id}/mark_as_read/ - Mark as read
- POST /api/communications/send_bulk_reminders/ - Send bulk reminders

Dashboard:
- GET /api/dashboard/ - Dashboard data
- GET /api/system-health/ - System health metrics
- POST /api/system-health/cleanup_expired_tokens/ - Cleanup tokens
- GET /api/system-health/performance_metrics/ - Performance metrics

Data Export:
- POST /api/data-export/export_projects/ - Export projects
- POST /api/data-export/export_users/ - Export users
- GET /api/data-export/export_reports/ - Export reports

Notifications:
- GET /api/notifications/ - Get notifications
- POST /api/notifications/mark_all_read/ - Mark all read
- POST /api/notifications/send_system_alert/ - Send system alert
"""






