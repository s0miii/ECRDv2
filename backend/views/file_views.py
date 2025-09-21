from django.http import FileResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser


from ..models import (
    File,
)

from ..serializers import (
    FileSerializer,
)

from .base_views import BaseModelViewSet

from .utils import validate_file_upload



class FileViewSet(BaseModelViewSet):
    """ 
    File management with upload handling and approval workflow.
    Implements secure file upload and management.
    """
    queryset = File.objects.all()
    serializer_class = FileSerializer
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ['project', 'requirement', 'file_type', 'approval_status']
    ordering = ['-uploaded_date']

    def get_queryset(self):
        """ 
        Optimize with related data.
        """
        return File.objects.select_related(
            'project', 'requirement', 'uploaded_by', 'approved_by'
        )
    
    def create(self, request, *args, **kwargs):
        """ 
        Handle file upload with validation
        """
        try:
            uploaded_file = request.FILES.get('file_path')
            if not uploaded_file:
                return Response({'error': 'No file provided'},
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Validate file
            validate_file_upload(uploaded_file)

            # set file metadata
            request.data['file_name'] = uploaded_file.name
            request.data['file_size'] = uploaded_file.size
            request.data['uploaded_by'] = request.user.user_id

            # Determine file type based on extension
            file_extension = uploaded_file.name.split('.')[-1].lower()
            file_type_map = {
                'pdf': 'DOCUMENT',
                'doc': 'DOCUMENT', 'docx': 'DOCUMENT',
                'xls': 'SPREADSHEET', 'xlsx': 'SPREADSHEET',
                'ppt': 'PRESENTATION', 'pptx': 'PRESENTATION',
                'jpg': 'IMAGE', 'jpeg': 'IMAGE', 'png': 'IMAGE', 'gif': 'IMAGE',
                'mp4': 'VIDEO', 'avi': 'VIDEO', 'mov': 'VIDEO'
            }
            request.data['file_type'] = file_type_map.get(file_extension, 'OTHER')

            return super().create(request, *args, **kwargs)
        
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """ 
        Download file with permission check.
        """
        file_obj = self.get_object()

        # Check permissions (implement as needed)
        if not file_obj.file_path:
            return Response({'error': 'File not found'},
                            status=status.HTTP_404_NOT_FOUND)
        
        return FileResponse(
            file_obj.file_path.open('rb'),
            as_attachment=True,
            filename=file_obj.file_name
        )