"""
Main Project URL Configuration

This is the root URL configuration that includes all app-level URLs
and provides the main entry points for the Extension Management System.

URL Structure:
- /admin/ - Django admin interface
- /api/ - REST API endpoints (from extension_management app)
- / - Root redirects to API documentation or admin
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from rest_framework.documentation import include_docs_urls
from rest_framework.schemas import get_schema_view


# ============================================================================
# CONSTANTS AND CONFIGURATION  
# ============================================================================

# API configuration
API_TITLE = 'ECRD Project Monitoring & Evaluation API'
API_DESCRIPTION = 'Endpoints for managing users, projects, reports, attendance, and evaluations.'
API_VERSION = 'v1'

# URL Patterns
ADMIN_URL_PREFIX = 'admin/'
API_URL_PREFIX = 'api/'
DOCS_URL_PREFIX = 'docs/'
SCHEMA_URL_PREFIX = 'schema/'



# ============================================================================
# SCHEMA AND DOCUMENTATION VIEWS
# ============================================================================

# API Schema view for OpenAPI/Swagger integration
schema_view = get_schema_view(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)


# ============================================================================
# URL PATTERNS CONFIGURATION
# ============================================================================

urlpatterns = [
    # django Admin interface
    path(ADMIN_URL_PREFIX, admin.site.urls),

    # Extension Management API
    path(API_URL_PREFIX, include('extension_management.urls')),

    # API Documentation (optional - requires djangorestframework and coreapi)
    path(DOCS_URL_PREFIX, include_docs_urls(
        title=API_TITLE,
        description=API_DESCRIPTION
    )),

    # API Schema (OpenAPI/Swagger format)
    path(SCHEMA_URL_PREFIX, schema_view),

    # Root URL redirect to API docs or adminm
    path('', RedirectView.as_view(url=f'{API_URL_PREFIX}', permanent=False)),
]


# ============================================================================
# DEVELOPMENT AND MEDIA FILE SERVING
# ============================================================================

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )

    # Add debug toolbar URLs if installed
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns


# ============================================================================
# ERROR HANDLER CONFIGURATION (Optional)
# ============================================================================

# Custom error handlers for production
if not settings.DEBUG:
    from django.views.defaults import (
        bad_request, permission_denied, 
        page_not_found, server_error
    )
    
    # Custom error views can be defined here
    # handler400 = 'myproject.views.bad_request'
    # handler403 = 'myproject.views.permission_denied'  
    # handler404 = 'myproject.views.page_not_found'
    # handler500 = 'myproject.views.server_error'


# ============================================================================
# URL PATTERN EXAMPLES AND TESTING
# ============================================================================

"""
Available Endpoints:

Administrative:
- http://localhost:8000/admin/ - Django admin interface

API Endpoints:
- http://localhost:8000/api/ - API root (browsable API)
- http://localhost:8000/api/auth/ - Authentication endpoints
- http://localhost:8000/api/users/ - User management
- http://localhost:8000/api/projects/ - Project management
- http://localhost:8000/api/files/ - File management
- ... (all other endpoints from app URLs)

Documentation:
- http://localhost:8000/docs/ - API documentation
- http://localhost:8000/schema/ - OpenAPI schema

Testing Examples:

# List all projects
GET http://localhost:8000/api/projects/

# Create a new project
POST http://localhost:8000/api/projects/
Content-Type: application/json
{
    "title": "Test Project",
    "description": "A test project",
    "project_type": "EXTENSION",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "budget": 50000.00,
    "location": "University Campus",
    "project_leader": 1,
    "college": 1,
    "department": 1,
    "expected_beneficiaries": 100
}

# Get project details
GET http://localhost:8000/api/projects/1/

# Update project status
POST http://localhost:8000/api/projects/1/change_status/
Content-Type: application/json
{
    "status": "APPROVED",
    "reason": "Project meets all requirements"
}

# Search projects
POST http://localhost:8000/api/projects/search/
Content-Type: application/json
{
    "query": "community",
    "project_type": "EXTENSION",
    "status": "APPROVED",
    "start_date_from": "2024-01-01",
    "budget_min": 10000,
    "ordering": "-created_at"
}

# Upload a file
POST http://localhost:8000/api/files/
Content-Type: multipart/form-data
project: 1
requirement: 1
file_path: [binary file data]

# User authentication
POST http://localhost:8000/api/auth/login/
Content-Type: application/json
{
    "email": "user@example.com",
    "password": "securepassword"
}
"""






