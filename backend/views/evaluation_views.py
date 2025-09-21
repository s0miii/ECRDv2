from django.db.models import Q, Count, Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    Evaluation, EvaluationLink, EvaluationTypeChoices, 
)

from ..serializers import (
    EvaluationSerializer, EvaluationLinkSerializer,
)

from .base_views import BaseModelViewSet

from .utils import apply_user_filters



class EvaluationViewSet(BaseModelViewSet):
    """ 
    Evaluation management for projects and trainers.
    handles feedback collection and rating systems.
    """
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    filterset_fields = ['project', 'evaluator', 'trainer', 'evaluation_type', 'rating']
    ordering = ['-evaluation_date']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters
        """
        queryset = Evaluation.objects.select_related(
            'project', 'evaluator', 'trainer'
        )
        return apply_user_filters(queryset, self.request.user)
    
    @action(detail=False, methods=['post'])
    def anonymous_evaluation(self, request):
        """ 
        submit anonymous evaluation without authentication
        """
        # allow anonymous access for this specific endpoint
        data = request.data.copy()
        data['is_anonymous'] = True

        serializer = EvaluationSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Anonymous evaluation submitted successfully',
                'evaluation_id': serializer.instance.evaluation_id
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def project_statistics(self, request):
        """ 
        Get evaluation statistics for projects.
        """
        project_id = request.query_params.get('project_id')

        if project_id:
            evaluations = self.get_queryset().filter(project_id=project_id)
        else:
            evaluations = self.get_queryset()

        statistics = {
            'total_evaluations': evaluations.count(),
            'average_rating': evaluations.aggregate(Avg('rating'))['rating__avg'] or 0,
            'rating_distribution': dict(
                evaluations.values('rating').annotate(count=Count('rating'))
                .values_list('rating', 'count')
            ),
            'evaluation_types': dict(
                evaluations.values('evaluation_type').annotate(count=Count('evaluation_type'))
                .values_list('evaluation_type', 'count')
            ),
            'anonymous_count': evaluations.filter(is_anonymous=True).count(),
            'identified_count': evaluations.filter(is_anonymous=False).count()
        }

        return Response(statistics)
    
    @action(detail=False, methods=['get'])
    def trainer_ratings(self, request):
        """ 
        Get trainer evaluation statistics
        """
        trainer_id = request.query_params.get('trainer_id')

        trainer_evaluations = self.get_queryset().filter(
            evaluation_type=EvaluationTypeChoices.TRAINER
        )

        if trainer_id:
            trainer_evaluations = trainer_evaluations.filter(trainer_id=trainer_id)

        trainer_stats = trainer_evaluations.values('trainer__trainer_name').annotate(
            average_rating=Avg('rating'),
            total_evaluation=Count('evaluation_id'),
            excellent_ratings=Count('rating', filter=Q(rating__gte=4)),
            poor_ratings=Count('rating', filter=Q(rating__lte=2))
        ).order_by('-average_rating')

        return Response(list(trainer_stats))
    

class EvaluationLinkViewSet(BaseModelViewSet):
    """ 
    Shareable link management for evaluations and attendance.
    Handles link generation, tracking, and validation.
    """
    queryset = EvaluationLink.objects.all()
    serializer_class = EvaluationLinkSerializer
    filterset_fields = ['project', 'link_type', 'is_active', 'created_by']
    ordering = ['-created_at']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters
        """
        queryset = EvaluationLink.objects.select_related(
            'project', 'created_by'
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """ 
        Set creator and generate unique token on creation
        """
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def validate_token(self, request):
        """
        Validate link token without authentication.
        """
        token = request.query_params.get('token')
        
        if not token:
            return Response(
                {'error': 'Token parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            link = EvaluationLink.objects.get(unique_token=token)
            
            if not link.is_valid:
                error_reasons = []
                if not link.is_active:
                    error_reasons.append('Link is inactive')
                if link.is_expired:
                    error_reasons.append('Link has expired')
                if link.is_usage_exceeded:
                    error_reasons.append('Usage limit exceeded')
                
                return Response({
                    'valid': False,
                    'errors': error_reasons
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'valid': True,
                'link': EvaluationLinkSerializer(link, context={'request': request}).data
            })
            
        except EvaluationLink.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Invalid token'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def increment_usage(self, request, pk=None):
        """
        Increment usage count for a link.
        """
        link = self.get_object()
        
        if not link.is_valid:
            return Response(
                {'error': 'Link is not valid for use'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        link.usage_count += 1
        link.save()
        
        return Response({
            'message': 'Usage count updated',
            'usage_count': link.usage_count,
            'remaining_uses': (link.max_usage - link.usage_count) if link.max_usage else None
        })
    
    @action(detail=True, methods=['post'])
    def extend_expiration(self, request, pk=None):
        """
        Extend link expiration date.
        """
        link = self.get_object()
        days = request.data.get('days', 7)
        
        link.expiration_date = timezone.now() + timezone.timedelta(days=days)
        link.save()
        
        return Response({
            'message': f'Link expiration extended by {days} days',
            'new_expiration': link.expiration_date
        })