from django.db.models import Count
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    AttendanceTemplate, AttendanceRecord, EvaluationLink,
    LinkTypeChoices, AttendanceStatusChoices,
)

from ..serializers import (
    AttendanceTemplateSerializer, AttendanceRecordSerializer, EvaluationLinkSerializer,
)

from .base_views import BaseModelViewSet

from .utils import apply_user_filters



class AttendanceTemplateViewSet(BaseModelViewSet):
    """ 
    Attendance template management for sessions and events.
    Handles creation and management of attendance sheets.
    """
    queryset = AttendanceTemplate.objects.all()
    serializer_class = AttendanceTemplateSerializer
    filterset_fields = ['project', 'session_date', 'is_active', 'created_by']
    ordering = ['-session_date', '-session_time']

    def get_queryset(self):
        """ 
        Optimize with related data and apply user filters.
        """
        queryset = AttendanceTemplate.objects.select_related(
            'project', 'created_by'
        ).annotate(
            attendance_count=Count('attendance_records')
        )
        return apply_user_filters(queryset, self.request.user)
    
    def perform_create(self, serializer):
        """ 
        Set creator on template creation
        """
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def attendance_records(self, request, pk=None):
        """ 
        Get all attendance records for a template
        """
        template = self.get_object()
        records = template.attendance_records.all()

        page = self.paginate_queryset(records)
        if page is not None:
            serializer = AttendanceRecordSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = AttendanceRecordSerializer(
            records, many=True, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def generate_attendance_link(self, request, pk=None):
        """ 
        Generate public link for attendance marking
        """
        template = self.get_object()

        # create evaluation link for attendance
        link = EvaluationLink.objects.create(
            project=template.project,
            link_type=LinkTypeChoices.ATTENDANCE,
            expiration_date=timezone.now() + timezone.timedelta(days=7), # 7 days validity
            created_by=request.user,
            max_usage=template.expected_participants * 2 # allow some buffer
        )

        serializer = EvaluationLinkSerializer(link, context={'request': request})
        return Response({
            'message': 'Attendance link generated successfully!',
            'link': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def deactivate_template(self, request, pk=None):
        """ 
        Deactivate attendance template
        """
        template = self.get_object()
        template.is_active = False
        template.save()

        return Response({'message': 'Attendance template deactivated'})
    

class AttendanceRecordViewSet(BaseModelViewSet):
    """ 
    Individual attendance record management.
    Handles participant check-in/check-out operations.
    """
    queryset = AttendanceRecord.objects.all()
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ['template', 'status', 'participant_email']
    ordering = ['participant_name']

    def get_queryset(self):
        """ 
        Optimize with template and project data.
        """
        return AttendanceRecord.objects.select_related(
            'template', 'template__project'
        )
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """ 
        Mark participate as checked in.
        """
        record = self.get_object()

        if record.check_in_time:
            return Response(
                {'error': 'Participant already checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record.check_in_time = timezone.now()
        record.status = AttendanceStatusChoices.PRESENT
        record.save()

        return Response({
            'message': 'Check-in successful',
            'check_in_time': record.check_in_time
        })
    
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """ 
        Mark participant as checked out
        """
        record = self.get_object()

        if not record.check_in_time:
            return Response(
                {'error': 'Participant must check in first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if record.check_out_time:
            return Response(
                {'error': 'Participant already checked out'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record.check_out_time = timezone.now()
        record.save()

        return Response({
            'message': 'Check-out successful',
            'check_out_time': record.check_out_time
        })
    
    @action(detail=False, methods=['post'])
    def bulk_mark_attendance(self, request):
        """ 
        Mark attendance for multiple participants at once
        """
        template_id = request.data.get('template_id')
        participants = request.data.get('participants', []) # list of participant emails
        attendance_status = request.data.get('status', AttendanceStatusChoices.PRESENT)

        if not template_id or not participants:
            return Response(
                {'error': 'template_id and participants list are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            template = AttendanceTemplate.objects.get(template_id=template_id)
            updated_count = 0

            with transaction.atomic():
                for participante_email in participants:
                    record, created = AttendanceRecord.objects.get_or_create(
                        template=template,
                        participante_email=participante_email,
                        defaults={
                            'participant_name': participante_email.split('@')[0],
                            'status': attendance_status
                        }
                    )

                    if not created and record.status != attendance_status:
                        record.status = attendance_status
                        if attendance_status == AttendanceStatusChoices.PRESENT:
                            record.check_in_time = timezone.now()
                        record.save()

                    updated_count += 1

            return Response({
                'message': f'Attendance marked for {updated_count} participants',
                'updated_count': updated_count
            })
        except AttendanceTemplate.DoesNotExist:
            return Response(
                {'error': 'Attendance template not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        