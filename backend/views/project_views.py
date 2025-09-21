from django.db.models import Q, Count, Avg, Sum
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


from ..models import (
    ProjectPerformance, ProjectStatusChoices, ProjectTrainer
)

from ..serializers import (
    ProjectSerializer, ProjectDetailSerializer, ProjectCreateSerializer,
    ProjectPerformanceSerializer, ProjectExportSerializer, ProjectSearchSerializer,
    ProjectStatisticsSerializer, BulkOperationSerializer, ProjectTrainerSerializer
)

from .base_views import BaseModelViewSet

from .utils import get_optimized_project_queryset, apply_user_filters



# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# Bulk Operation Limits
MAX_BULK_OPERATIONS = 100

# Performance Thresholds
EXCELLENT_PERFORMANCE_THRESHOLD = 4.0
GOOD_PERFORMANCE_THRESHOLD = 3.0


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