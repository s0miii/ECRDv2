from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    CustomUser, Project, ProjectMember,
    Trainer, 
)

from ..serializers import (
    ProjectMemberSerializer, TrainerSerializer, 
)

from .base_views import BaseModelViewSet


class ProjectMemberViewSet(BaseModelViewSet):
    """ 
    Project team member management.
    Handles project membership assignments and roles.
    """
    queryset = ProjectMember.objects.all()
    serializer_class = ProjectMemberSerializer
    filterset_fields = ['project', 'user', 'role', 'is_active']
    ordering = ['project', 'role', 'assigned_date']

    def get_queryset(self):
        """ 
        Optimize with related user and project data
        """
        return ProjectMember.objects.select_related(
            'user', 'project'
        )
    
    @action(detail=False, methods=['post'])
    def assign_member(self, request):
        """ 
        Assign user to project with role validation.
        """
        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'MEMBER')

        try:
            project = Project.objects.get(project_id=project_id)
            user = CustomUser.objects.get(user_id=user_id)

            # Check if membership already exists
            if ProjectMember.objects.filter(project=project, user=user).exists():
                return Response({'error': 'User is already a member of this project.'},
                                status=status.HTTP_400_BAD_REQUEST)
            
            member = ProjectMember.objects.create(
                project=project,
                user=user,
                role=role
            )

            serializer = ProjectMemberSerializer(member, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Project.DoesNotExist:
            return Response({'error': 'Project not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """ 
        Remove member from project.
        """
        member = self.get_object()
        member.is_active = False
        member.save()

        return Response({'message': 'Member removed from the project successfully!'})
    

# ============================================================================
# TRAINER MANAGEMENT VIEWS
# ============================================================================

class TrainerViewSet(BaseModelViewSet):
    """
    Trainer management for internal and external trainers.
    Handles trainer profiles and assignment tracking.
    """
    queryset = Trainer.objects.all()
    serializer_class = TrainerSerializer
    search_fields = ['trainer_name', 'email', 'expertise']
    filterset_fields = ['is_internal', 'created_at']
    ordering = ['trainer_name']
    
    def get_queryset(self):
        """
        Annotate with assignment count.
        """
        return Trainer.objects.annotate(
            assignment_count=Count('project_assignments')
        )
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get trainers available for assignment.
        """
        trainers = self.get_queryset().filter(is_internal=True)  # or other availability logic
        serializer = TrainerSerializer(trainers, many=True, context={'request': request})
        return Response(serializer.data)


