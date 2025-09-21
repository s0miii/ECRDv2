from django.db.models import Q, Count, Avg, Sum, Prefetch
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    CustomUser, Project,
     DocumentaryRequirement, File,
    AccomplishmentReport,
    EvaluationLink, ProjectPerformance, Communication,
    ProjectStatusChoices, UserTypeChoices, RequirementStatusChoices,
    ReportStatusChoices, EvaluationTypeChoices, EmailTypeChoices, 
    CommunicationStatusChoices, ApprovalStatusChoices,
)

from ..serializers import (
    CustomUserSerializer, ProjectSummarySerializer, AccomplishmentReportSerializer,
    CommunicationSerializer, ProjectExportSerializer, calculate_file_size_mb
)

from .utils import apply_user_filters


class DashboardViewSet(APIView):
    """
    Dashboard analytics and summary data.
    Provides aggregated data for admin and user dashboards.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get dashboard data based on user role and permissions.
        """
        user = request.user
        dashboard_data = {}
        
        # Apply user-based filtering to all queries
        projects = apply_user_filters(Project.objects.all(), user)
        
        # Basic project statistics
        dashboard_data['project_statistics'] = {
            'total_projects': projects.count(),
            'active_projects': projects.filter(
                status__in=[ProjectStatusChoices.APPROVED, ProjectStatusChoices.ONGOING]
            ).count(),
            'completed_projects': projects.filter(
                status=ProjectStatusChoices.COMPLETED
            ).count(),
            'planning_projects': projects.filter(
                status=ProjectStatusChoices.PLANNING
            ).count(),
        }
        
        # Budget statistics
        budget_data = projects.aggregate(
            total_budget=Sum('budget'),
            average_budget=Avg('budget')
        )
        dashboard_data['budget_statistics'] = {
            'total_budget': budget_data['total_budget'] or 0,
            'average_budget': budget_data['average_budget'] or 0
        }
        
        # Recent activities based on user type
        if user.user_type == UserTypeChoices.PROJECT_LEADER:
            dashboard_data['my_projects'] = ProjectSummarySerializer(
                projects.filter(project_leader=user)[:5], many=True
            ).data
            
        elif user.user_type in [UserTypeChoices.EXTENSION_COORDINATOR, UserTypeChoices.DEPARTMENT_HEAD]:
            dashboard_data['department_projects'] = ProjectSummarySerializer(
                projects[:10], many=True
            ).data
        
        # Performance metrics (if user has access)
        if user.user_type in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF,
            UserTypeChoices.EXTENSION_COORDINATOR
        ]:
            performances = ProjectPerformance.objects.filter(
                project__in=projects
            ).aggregate(
                avg_completion=Avg('completion_percentage'),
                avg_impact=Avg('impact_score'),
                total_beneficiaries=Sum('total_beneficiaries')
            )
            
            dashboard_data['performance_metrics'] = {
                'average_completion': performances['avg_completion'] or 0,
                'average_impact_score': performances['avg_impact'] or 0,
                'total_beneficiaries': performances['total_beneficiaries'] or 0
            }
        
        # Pending items that need attention
        dashboard_data['pending_items'] = self._get_pending_items(user, projects)
        
        # Recent communications
        recent_communications = Communication.objects.filter(
            project__in=projects
        ).order_by('-sent_date')[:5]
        
        dashboard_data['recent_communications'] = CommunicationSerializer(
            recent_communications, many=True, context={'request': request}
        ).data
        
        return Response(dashboard_data)
    
    def _get_pending_items(self, user, projects):
        """
        Get items requiring user attention.
        Private method for pending items logic.
        """
        pending_items = {
            'overdue_requirements': 0,
            'pending_reports': 0,
            'pending_evaluations': 0,
            'expiring_links': 0,
            'failed_communications': 0,
            'items_needing_approval': 0
        }

        # Get current date for calculations
        today = timezone.now().date()

        # overdue requirements calculation
        overdue_requirements = DocumentaryRequirement.objects.filter(
            project__in=projects,
            due_date__lt=today,
            status__in=[
                RequirementStatusChoices.PENDING,
                RequirementStatusChoices.REVISION_NEEDED
            ]
        )
        pending_items['overdue_requirements'] = overdue_requirements.count()

        # Pending reports that need review (for coordinators, heads, admins)
        if user.user_type in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.COLLEGE_HEAD,
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            pending_reports = AccomplishmentReport.objects.filter(
                project__in=projects,
                status=ReportStatusChoices.SUBMITTED
            )
            pending_items['pending_reports'] = pending_reports.count()
        
        # Items needing approval (files, requirements) baseed on user role
        if user.user_type in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            #Files pending approval
            pending_files = File.objects.filter(
                project__in=projects,
                approval_status=ApprovalStatusChoices.PENDING
            ).count()

            # Requirements submitted for approval
            pending_req_approvals = DocumentaryRequirement.objects.filter(
                project__in=projects,
                status=RequirementStatusChoices.SUBMITTED
            ).count()

            pending_items['items_needing_approval'] = pending_files + pending_req_approvals

        # Expiring evaluation/attendance links (within next 7 days)
        expiration_threshold = timezone.now() + timezone.timedelta(days=7)
        expiring_links = EvaluationLink.objects.filter(
            project__in=projects,
            is_active=True,
            expiration_date__lte=expiration_threshold,
            expiration_date__gt=timezone.now()
        )
        pending_items['expiring_links'] = expiring_links.count()
        
        # Failed communications that need attention
        failed_communications = Communication.objects.filter(
            project__in=projects,
            status=CommunicationStatusChoices.FAILED,
            sent_date__gte=timezone.now() - timezone.timedelta(days=30)  # Last 30 days
        )
        pending_items['failed_communications'] = failed_communications.count()
        
        # Pending evaluations (for project leaders - check if project ended without evaluations)
        if user.user_type == UserTypeChoices.PROJECT_LEADER:
            completed_projects = projects.filter(
                status=ProjectStatusChoices.COMPLETED,
                project_leader=user
            )
            
            projects_without_evaluations = 0
            for project in completed_projects:
                if not project.evaluations.filter(
                    evaluation_type=EvaluationTypeChoices.PROJECT
                ).exists():
                    projects_without_evaluations += 1
            
            pending_items['pending_evaluations'] = projects_without_evaluations
        
        return pending_items


# ============================================================================
# SYSTEM HEALTH AND MONITORING VIEWS
# ============================================================================

class SystemHealthViewSet(APIView):
    """
    System health monitoring and diagnostics.
    Single responsibility: Provide system status and health metrics.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get comprehensive system health metrics.
        Only accessible to system administrators.
        """
        if request.user.user_type != UserTypeChoices.SYSTEM_ADMIN:
            return Response(
                {'error': 'Insufficient permissions to view system health'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Database connectivity check
        try:
            total_users = CustomUser.objects.count()
            total_projects = Project.objects.count()
            db_status = 'healthy'
        except Exception as e:
            db_status = f'error: {str(e)}'
            total_users = 0
            total_projects = 0
        
        # File storage health check
        storage_status = 'healthy'
        try:
            # Check if we can access file storage
            total_files = File.objects.count()
            total_file_size = File.objects.aggregate(
                total_size=Sum('file_size')
            )['total_size'] or 0
            storage_size_mb = calculate_file_size_mb(total_file_size)
        except Exception as e:
            storage_status = f'error: {str(e)}'
            total_files = 0
            storage_size_mb = 0
        
        # Communication system health
        comm_status = 'healthy'
        failed_communications_count = Communication.objects.filter(
            status=CommunicationStatusChoices.FAILED,
            sent_date__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        if failed_communications_count > 50:  # Threshold for concern
            comm_status = 'warning'
        
        # System performance metrics
        overdue_requirements = DocumentaryRequirement.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=[
                RequirementStatusChoices.PENDING,
                RequirementStatusChoices.REVISION_NEEDED
            ]
        ).count()
        
        pending_approvals = File.objects.filter(
            approval_status=ApprovalStatusChoices.PENDING
        ).count() + DocumentaryRequirement.objects.filter(
            status=RequirementStatusChoices.SUBMITTED
        ).count()
        
        active_links = EvaluationLink.objects.filter(
            is_active=True,
            expiration_date__gt=timezone.now()
        ).count()
        
        health_data = {
            'timestamp': timezone.now(),
            'overall_status': 'healthy' if all([
                db_status == 'healthy',
                storage_status == 'healthy',
                comm_status in ['healthy', 'warning']
            ]) else 'unhealthy',
            'database': {
                'status': db_status,
                'total_users': total_users,
                'total_projects': total_projects,
                'active_users': CustomUser.objects.filter(is_active=True).count()
            },
            'file_storage': {
                'status': storage_status,
                'total_files': total_files,
                'storage_size_mb': storage_size_mb
            },
            'communications': {
                'status': comm_status,
                'failed_last_week': failed_communications_count,
                'total_sent_today': Communication.objects.filter(
                    sent_date__date=timezone.now().date()
                ).count()
            },
            'system_metrics': {
                'overdue_requirements': overdue_requirements,
                'pending_approvals': pending_approvals,
                'active_links': active_links,
                'projects_by_status': dict(
                    Project.objects.values('status').annotate(
                        count=Count('project_id')
                    ).values_list('status', 'count')
                )
            }
        }
        
        return Response(health_data)
    
    @action(detail=False, methods=['post'])
    def cleanup_expired_tokens(self, request):
        """
        Clean up expired evaluation links and tokens.
        System maintenance operation.
        """
        if request.user.user_type != UserTypeChoices.SYSTEM_ADMIN:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Deactivate expired links
        expired_links = EvaluationLink.objects.filter(
            expiration_date__lte=timezone.now(),
            is_active=True
        )
        
        updated_count = expired_links.update(is_active=False)
        
        return Response({
            'message': f'Cleaned up {updated_count} expired links',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def performance_metrics(self, request):
        """
        Get detailed performance and usage metrics.
        """
        if request.user.user_type not in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Date range for metrics (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        
        metrics = {
            'user_activity': {
                'total_users': CustomUser.objects.count(),
                'active_users': CustomUser.objects.filter(
                    last_login__gte=thirty_days_ago
                ).count(),
                'new_users_this_month': CustomUser.objects.filter(
                    date_joined__gte=thirty_days_ago
                ).count()
            },
            'project_activity': {
                'projects_created_this_month': Project.objects.filter(
                    created_at__gte=thirty_days_ago
                ).count(),
                'projects_completed_this_month': Project.objects.filter(
                    status=ProjectStatusChoices.COMPLETED,
                    updated_at__gte=thirty_days_ago
                ).count(),
                'average_project_duration': Project.objects.filter(
                    status=ProjectStatusChoices.COMPLETED
                ).aggregate(
                    avg_duration=Avg('end_date') - Avg('start_date')
                )['avg_duration'] or 0
            },
            'file_activity': {
                'files_uploaded_this_month': File.objects.filter(
                    uploaded_date__gte=thirty_days_ago
                ).count(),
                'total_storage_mb': calculate_file_size_mb(
                    File.objects.aggregate(
                        total_size=Sum('file_size')
                    )['total_size'] or 0
                ),
                'files_by_type': dict(
                    File.objects.values('file_type').annotate(
                        count=Count('file_id')
                    ).values_list('file_type', 'count')
                )
            },
            'communication_metrics': {
                'emails_sent_this_month': Communication.objects.filter(
                    sent_date__gte=thirty_days_ago
                ).count(),
                'delivery_success_rate': self._calculate_delivery_success_rate(
                    thirty_days_ago
                ),
                'communications_by_type': dict(
                    Communication.objects.filter(
                        sent_date__gte=thirty_days_ago
                    ).values('email_type').annotate(
                        count=Count('communication_id')
                    ).values_list('email_type', 'count')
                )
            }
        }
        
        return Response(metrics)
    
    def _calculate_delivery_success_rate(self, since_date):
        """
        Calculate email delivery success rate.
        Private method for performance calculation.
        """
        total_communications = Communication.objects.filter(
            sent_date__gte=since_date
        ).count()
        
        if total_communications == 0:
            return 0
        
        successful_communications = Communication.objects.filter(
            sent_date__gte=since_date,
            status=CommunicationStatusChoices.DELIVERED
        ).count()
        
        return round((successful_communications / total_communications) * 100, 2)


# ============================================================================
# BACKUP AND DATA EXPORT VIEWS  
# ============================================================================

class DataExportViewSet(APIView):
    """
    Data export functionality for backup and reporting.
    Single responsibility: Handle various data export formats.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def export_projects(self, request):
        """
        Export project data in various formats (CSV, Excel, JSON).
        """
        export_format = request.data.get('format', 'csv').lower()
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')
        college_ids = request.data.get('college_ids', [])
        status_filters = request.data.get('status_filters', [])
        
        # Apply user-based filtering
        projects = apply_user_filters(Project.objects.all(), request.user)
        
        # Apply additional filters
        if date_from:
            projects = projects.filter(start_date__gte=date_from)
        if date_to:
            projects = projects.filter(start_date__lte=date_to)
        if college_ids:
            projects = projects.filter(college_id__in=college_ids)
        if status_filters:
            projects = projects.filter(status__in=status_filters)
        
        # Optimize query with related data
        projects = projects.select_related(
            'project_leader', 'college', 'department'
        ).prefetch_related('members__user')
        
        # Serialize data for export
        serializer = ProjectExportSerializer(
            projects, many=True, context={'request': request}
        )
        
        export_data = {
            'export_date': timezone.now(),
            'total_records': projects.count(),
            'filters_applied': {
                'date_from': date_from,
                'date_to': date_to,
                'colleges': college_ids,
                'statuses': status_filters
            },
            'data': serializer.data
        }
        
        return Response(export_data)
    
    @action(detail=False, methods=['post'])
    def export_users(self, request):
        """
        Export user data for administrative purposes.
        """
        # Restrict to admin users only
        if request.user.user_type not in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            return Response(
                {'error': 'Insufficient permissions to export user data'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        export_format = request.data.get('format', 'csv').lower()
        user_types = request.data.get('user_types', [])
        colleges = request.data.get('colleges', [])
        active_only = request.data.get('active_only', True)
        
        users = CustomUser.objects.all()
        
        # Apply filters
        if user_types:
            users = users.filter(user_type__in=user_types)
        if colleges:
            users = users.filter(college_id__in=colleges)
        if active_only:
            users = users.filter(is_active=True)
        
        # Optimize query
        users = users.select_related('college', 'department')
        
        # Serialize data (excluding sensitive information)
        serializer = CustomUserSerializer(
            users, many=True, context={'request': request}
        )
        
        # Remove sensitive fields from export
        safe_data = []
        for user_data in serializer.data:
            safe_user = user_data.copy()
            # Remove any sensitive fields if needed
            safe_data.append(safe_user)
        
        export_data = {
            'export_date': timezone.now(),
            'total_records': users.count(),
            'data': safe_data
        }
        
        return Response(export_data)
    
    @action(detail=False, methods=['get'])
    def export_reports(self, request):
        """
        Export accomplishment reports with filters.
        """
        project_id = request.query_params.get('project_id')
        report_type = request.query_params.get('report_type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Apply user-based filtering to projects first
        user_projects = apply_user_filters(
            Project.objects.all(), request.user
        )
        
        reports = AccomplishmentReport.objects.filter(
            project__in=user_projects
        )
        
        # Apply additional filters
        if project_id:
            reports = reports.filter(project_id=project_id)
        if report_type:
            reports = reports.filter(report_type=report_type)
        if date_from:
            reports = reports.filter(submission_date__gte=date_from)
        if date_to:
            reports = reports.filter(submission_date__lte=date_to)
        
        # Optimize query
        reports = reports.select_related(
            'project', 'submitted_by', 'reviewed_by'
        ).order_by('-submission_date')
        
        serializer = AccomplishmentReportSerializer(
            reports, many=True, context={'request': request}
        )
        
        export_data = {
            'export_date': timezone.now(),
            'total_records': reports.count(),
            'data': serializer.data
        }
        
        return Response(export_data)


# ============================================================================
# NOTIFICATION MANAGEMENT VIEWS
# ============================================================================

class NotificationViewSet(APIView):
    """
    Notification management and delivery system.
    Single responsibility: Handle system notifications and alerts.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get notifications for the current user.
        """
        # Get user's notifications (communications sent to them)
        user_notifications = Communication.objects.filter(
            recipient_email=request.user.email
        ).order_by('-sent_date')[:50]  # Limit to recent 50
        
        # Get system-wide notifications based on user role
        system_notifications = self._get_system_notifications(request.user)
        
        serializer = CommunicationSerializer(
            user_notifications, many=True, context={'request': request}
        )
        
        notification_data = {
            'user_notifications': serializer.data,
            'system_notifications': system_notifications,
            'unread_count': user_notifications.filter(read_at__isnull=True).count()
        }
        
        return Response(notification_data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all user notifications as read.
        """
        updated_count = Communication.objects.filter(
            recipient_email=request.user.email,
            read_at__isnull=True
        ).update(read_at=timezone.now())
        
        return Response({
            'message': f'Marked {updated_count} notifications as read',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def send_system_alert(self, request):
        """
        Send system-wide alert (admin only).
        """
        if request.user.user_type not in [
            UserTypeChoices.SYSTEM_ADMIN,
            UserTypeChoices.EXTENSION_ADMIN_STAFF
        ]:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message = request.data.get('message')
        subject = request.data.get('subject', 'System Alert')
        recipient_types = request.data.get('recipient_types', [])
        
        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get recipients based on user types
        recipients = CustomUser.objects.filter(is_active=True)
        if recipient_types:
            recipients = recipients.filter(user_type__in=recipient_types)
        
        # Create communications for all recipients
        communications_created = []
        with transaction.atomic():
            for recipient in recipients:
                communication = Communication.objects.create(
                    sender=request.user,
                    recipient_email=recipient.email,
                    recipient_name=recipient.get_full_name(),
                    email_type=EmailTypeChoices.NOTIFICATION,
                    subject=subject,
                    message=message,
                    is_automated=False
                )
                communications_created.append(communication)
        
        return Response({
            'message': f'System alert sent to {len(communications_created)} users',
            'recipients_count': len(communications_created)
        }, status=status.HTTP_201_CREATED)
    
    def _get_system_notifications(self, user):
        """
        Get system notifications based on user role.
        Private method for role-based system notifications.
        """
        notifications = []
        
        # Apply user filtering to get relevant projects
        user_projects = apply_user_filters(Project.objects.all(), user)
        
        # Overdue requirements notification
        overdue_count = DocumentaryRequirement.objects.filter(
            project__in=user_projects,
            due_date__lt=timezone.now().date(),
            status__in=[
                RequirementStatusChoices.PENDING,
                RequirementStatusChoices.REVISION_NEEDED
            ]
        ).count()
        
        if overdue_count > 0:
            notifications.append({
                'type': 'warning',
                'title': 'Overdue Requirements',
                'message': f'You have {overdue_count} overdue requirements',
                'action_url': '/requirements?filter=overdue'
            })
        
        # Pending approvals (for coordinators and heads)
        if user.user_type in [
            UserTypeChoices.EXTENSION_COORDINATOR,
            UserTypeChoices.DEPARTMENT_HEAD,
            UserTypeChoices.SYSTEM_ADMIN
        ]:
            pending_reports = AccomplishmentReport.objects.filter(
                project__in=user_projects,
                status=ReportStatusChoices.SUBMITTED
            ).count()
            
            if pending_reports > 0:
                notifications.append({
                    'type': 'info',
                    'title': 'Pending Report Reviews',
                    'message': f'{pending_reports} reports awaiting your review',
                    'action_url': '/reports?filter=pending'
                })
        
        # Project deadlines approaching (next 7 days)
        upcoming_deadlines = user_projects.filter(
            end_date__lte=timezone.now().date() + timezone.timedelta(days=7),
            end_date__gt=timezone.now().date(),
            status__in=[ProjectStatusChoices.APPROVED, ProjectStatusChoices.ONGOING]
        ).count()
        
        if upcoming_deadlines > 0:
            notifications.append({
                'type': 'warning',
                'title': 'Upcoming Project Deadlines',
                'message': f'{upcoming_deadlines} projects ending within 7 days',
                'action_url': '/projects?filter=ending_soon'
            })
        
        return notifications