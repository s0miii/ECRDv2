from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    College, Department,
)

from ..serializers import (
    UserBasicInfoSerializer, CollegeSerializer, DepartmentSerializer,
    ProjectSummarySerializer,
)

from .base_views import BaseModelViewSet

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