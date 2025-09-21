from django.db.models import Q, Count, Avg, Sum, Prefetch

from ..models import (
    Project, UserTypeChoices
)


# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# File Upload Limits (MB)
MAX_FILE_SIZE_MB = 50
ALLOWED_FILE_TYPES = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt',
    'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov'
]


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