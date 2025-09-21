from django.db.models import Count
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    Project, DocumentaryRequirement, Communication,
    RequirementStatusChoices, EmailTypeChoices, CommunicationStatusChoices,
)

from ..serializers import (
    CommunicationSerializer
)

from .base_views import BaseModelViewSet

from .utils import apply_user_filters


class CommunicationViewSet(BaseModelViewSet):
    """
    Communication management for email notifications and tracking.
    Handles automated and manual communications.
    """
    queryset = Communication.objects.all()
    serializer_class = CommunicationSerializer
    filterset_fields = ['project', 'sender', 'email_type', 'status', 'is_automated']
    ordering = ['-sent_date']
    
    def get_queryset(self):
        """
        Optimize with related data and apply user filters.
        """
        queryset = Communication.objects.select_related(
            'project', 'sender'
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """
        Set sender on communication creation.
        """
        serializer.save(sender=self.request.user)
    
    @action(detail=False, methods=['post'])
    def send_notification(self, request):
        """
        Send notification email to specific recipients.
        """
        project_id = request.data.get('project_id')
        recipients = request.data.get('recipients', [])
        email_type = request.data.get('email_type', EmailTypeChoices.NOTIFICATION)
        subject = request.data.get('subject')
        message = request.data.get('message')
        
        if not recipients or not subject or not message:
            return Response(
                {'error': 'recipients, subject, and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project = None
        if project_id:
            try:
                project = Project.objects.get(project_id=project_id)
            except Project.DoesNotExist:
                return Response(
                    {'error': 'Project not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        communications_created = []
        
        with transaction.atomic():
            for recipient in recipients:
                communication = Communication.objects.create(
                    project=project,
                    sender=request.user,
                    recipient_email=recipient.get('email'),
                    recipient_name=recipient.get('name'),
                    email_type=email_type,
                    subject=subject,
                    message=message,
                    is_automated=False
                )
                communications_created.append(communication)
        
        return Response({
            'message': f'Created {len(communications_created)} communication records',
            'communications': CommunicationSerializer(
                communications_created, many=True, context={'request': request}
            ).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def delivery_statistics(self, request):
        """
        Get email delivery statistics.
        """
        communications = self.get_queryset()
        
        project_id = request.query_params.get('project_id')
        if project_id:
            communications = communications.filter(project_id=project_id)
        
        statistics = {
            'total_sent': communications.count(),
            'delivered': communications.filter(
                status=CommunicationStatusChoices.DELIVERED
            ).count(),
            'failed': communications.filter(
                status=CommunicationStatusChoices.FAILED
            ).count(),
            'pending': communications.filter(
                status=CommunicationStatusChoices.PENDING
            ).count(),
            'read_count': communications.filter(read_at__isnull=False).count(),
            'by_type': dict(
                communications.values('email_type').annotate(count=Count('email_type'))
                .values_list('email_type', 'count')
            ),
            'automated_vs_manual': {
                'automated': communications.filter(is_automated=True).count(),
                'manual': communications.filter(is_automated=False).count()
            }
        }
        
        return Response(statistics)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark communication as read.
        """
        communication = self.get_object()
        communication.mark_as_read()
        
        return Response({
            'message': 'Communication marked as read',
            'read_at': communication.read_at
        })
    
    @action(detail=False, methods=['post'])
    def send_bulk_reminders(self, request):
        """
        Send bulk reminder emails for overdue requirements.
        """
        # Get overdue requirements
        overdue_requirements = DocumentaryRequirement.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=[RequirementStatusChoices.PENDING, RequirementStatusChoices.REVISION_NEEDED]
        ).select_related('assigned_to', 'project')
        
        reminder_count = 0
        
        with transaction.atomic():
            for requirement in overdue_requirements:
                # Check if reminder already sent today
                today_reminders = Communication.objects.filter(
                    recipient_email=requirement.assigned_to.email,
                    email_type=EmailTypeChoices.REMINDER,
                    sent_date__date=timezone.now().date()
                )
                
                if not today_reminders.exists():
                    Communication.objects.create(
                        project=requirement.project,
                        sender=request.user,
                        recipient_email=requirement.assigned_to.email,
                        recipient_name=requirement.assigned_to.get_full_name(),
                        email_type=EmailTypeChoices.REMINDER,
                        subject=f'Reminder: {requirement.requirement_name} is overdue',
                        message=f'The requirement "{requirement.requirement_name}" for project "{requirement.project.title}" was due on {requirement.due_date}. Please submit as soon as possible.',
                        is_automated=True
                    )
                    reminder_count += 1
        
        return Response({
            'message': f'Sent {reminder_count} reminder emails',
            'reminders_sent': reminder_count
        })