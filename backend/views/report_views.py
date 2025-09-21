from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    DocumentaryRequirement, AccomplishmentReport, UserTypeChoices, 
    RequirementStatusChoices, ReportStatusChoices, 
)

from ..serializers import (
    DocumentaryRequirementSerializer, AccomplishmentReportSerializer,
)

from .base_views import BaseModelViewSet

from .utils import apply_user_filters



class DocumentaryRequirementViewSet(BaseModelViewSet):
    """ 
    Documentary requirement management with approval workflow.
    Handles requirement assignments and tracking.
    """
    queryset = DocumentaryRequirement.objects.all()
    serializer_class = DocumentaryRequirementSerializer
    filterset_fields = ['project', 'status', 'assigned_to', 'due_date']
    ordering = ['due_date', 'requirement_name']

    def get_queryset(self):
        """
        Optimize with related user and project data.
        """
        return DocumentaryRequirement.objects.select_related(
            'project', 'assigned_by', 'assigned_to', 'approved_by'
        )
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """ 
        Submit requirements for approval.
        """
        requirement = self.get_object()
        requirement.status = RequirementStatusChoices.SUBMITTED
        requirement.submitted_date = timezone.now()
        requirement.save()

        return Response({'message': 'Requirement submitted for approval'})
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """ 
        Approve submitted requirement.
        """
        requirement = self.get_object()
        requirement.status = RequirementStatusChoices.APPROVED
        requirement.approved_by = request.user
        requirement.approval_date = timezone.now()
        requirement.save()

        return Response({'message': 'Requirement approved.'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """ 
        Reject submitted requirement with reason
        """
        requirement = self.get_object()
        reason = request.data.get('reason')

        requirement.status = RequirementStatusChoices.REJECTED
        requirement.rejection_reason = reason
        requirement.save()

        return Response({'message': 'Requirement rejected'})
    
class AccomplishmentReportViewSet(BaseModelViewSet):
    """ 
    Accomplishment report management with review workflow.
    Handles report, submission, review, and approval processes.
    """
    queryset = AccomplishmentReport.objects.all()
    serializer_class = AccomplishmentReportSerializer
    filterset_fields = ['project', 'report_type', 'status', 'submitted_by']
    ordering = ['-submission_date']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters.
        """
        queryset = AccomplishmentReport.objects.select_related(
            'project', 'submitted_by', 'reviewed_by'
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """ 
        Set submitter and submission date on creation
        """
        serializer.save(submitted_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        """ 
        Submit report for review by changing status.
        """
        report = self.get_object()

        if report.status != ReportStatusChoices.DRAFT:
            return Response(
                {'error': 'Only draft reports can be submitted for review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = ReportStatusChoices.SUBMITTED
        report.save()

        return Response({
            'message': 'Report submitted for review successfully',
            'report': AccomplishmentReportSerializer(report, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def approve_report(self, request, pk=None):
        """ 
        Approve submitted report.
        """
        report = self.get_object()
        comments = request.data.get('review_comments', '')

        if report.status != ReportStatusChoices.SUBMITTED:
            return Response(
                {'error': 'Only submitted reports can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = ReportStatusChoices.APPROVED
        report.reviewed_by = request.user
        report.review_date = timezone.now()
        report.review_comments = comments
        report.save()

        return Response({
            'message': 'Report approved successfully',
            'report': AccomplishmentReportSerializer(report, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        """ 
        Request revision on submitted report.
        """
        report = self.get_object()
        comments = request.data.get('review_comments')

        if not comments:
            return Response(
                {'error': 'Review comments are required when requesting revision'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if report.status != ReportStatusChoices.SUBMITTED:
            return Response(
                {'error': 'Only submitted reports can be sent for revision'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = ReportStatusChoices.REVISION_NEEDED
        report.reviewed_by = request.user
        report.review_date = timezone.now()
        report.review_comments = comments
        report.save()

        return Response({
            'message': 'Revision requested successfully',
            'report': AccomplishmentReportSerializer(report, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def pending_reviews(self, request):
        """ 
        Get reports pending review for current user.
        """
        if request.user.user_type not in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.COLLEGE_HEAD,
            UserTypeChoices.SYSTEM_ADMIN
        ]:
            return Response(
                {'error': 'Insufficient permissions to review reports'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_reports = self.get_queryset().filter(
            status=ReportStatusChoices.SUBMITTED
        )

        page = self.paginate_queryset(pending_reports)
        if page is not None:
            serializer = AccomplishmentReportSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = AccomplishmentReportSerializer(
            pending_reports, many=True, context={'request': request}
        )
        return Response(serializer.data)