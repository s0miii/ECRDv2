import React, { useState } from 'react';
import { X, Upload, FileText, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';

// Temporary mock data - replace with actual API calls
const TEMP_PROJECTS = [
  { id: '1', name: 'Community Health Initiative', code: 'CHI-2024-001' },
  { id: '2', name: 'Educational Support Program', code: 'ESP-2024-002' },
  { id: '3', name: 'Agricultural Development Project', code: 'ADP-2024-003' },
  { id: '4', name: 'Youth Empowerment Initiative', code: 'YEI-2024-004' },
];

const MAX_FILE_SIZE_MB = 10;
const ALLOWED_FILE_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

interface FormData {
  projectId: string;
  file: File | null;
  comments: string;
}

interface FormErrors {
  projectId?: string;
  file?: string;
}

interface SubmitReportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const SubmitReportModal: React.FC<SubmitReportModalProps> = ({ 
  open, 
  onOpenChange 
}) => {
  const [formData, setFormData] = useState<FormData>({
    projectId: '',
    file: null,
    comments: '',
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      return `File size exceeds ${MAX_FILE_SIZE_MB}MB limit`;
    }
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      return 'Invalid file type. Please upload PDF, DOC, DOCX, XLS, or XLSX files';
    }
    return null;
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.projectId) {
      newErrors.projectId = 'Please select a project';
    }

    if (!formData.file) {
      newErrors.file = 'Please upload a file';
    } else {
      const fileError = validateFile(formData.file);
      if (fileError) {
        newErrors.file = fileError;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleProjectChange = (value: string) => {
    setFormData(prev => ({ ...prev, projectId: value }));
    
    if (errors.projectId) {
      setErrors(prev => ({ ...prev, projectId: undefined }));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    
    if (file) {
      const fileError = validateFile(file);
      if (fileError) {
        setErrors(prev => ({ ...prev, file: fileError }));
        setFormData(prev => ({ ...prev, file: null }));
        e.target.value = '';
      } else {
        setFormData(prev => ({ ...prev, file }));
        setErrors(prev => ({ ...prev, file: undefined }));
      }
    }
  };

  const handleRemoveFile = () => {
    setFormData(prev => ({ ...prev, file: null }));
    setErrors(prev => ({ ...prev, file: undefined }));
    const fileInput = document.getElementById('file-upload') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  const handleCommentsChange = (value: string) => {
    setFormData(prev => ({ ...prev, comments: value }));
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // TODO: Replace with actual API call to Django REST Framework
      // Example:
      // const formDataToSend = new FormData();
      // formDataToSend.append('project_id', formData.projectId);
      // formDataToSend.append('file', formData.file);
      // formDataToSend.append('comments', formData.comments);
      // 
      // await fetch('/api/reports/', {
      //   method: 'POST',
      //   body: formDataToSend
      // });
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      console.log('Report data to be submitted:', {
        projectId: formData.projectId,
        fileName: formData.file?.name,
        fileSize: formData.file?.size,
        comments: formData.comments,
      });

      // Reset form and close modal after successful submission
      setFormData({
        projectId: '',
        file: null,
        comments: '',
      });
      setErrors({});
      onOpenChange(false);
      
      // Show success message (you can use a toast library later)
      alert('Report submitted successfully!');
    } catch (error) {
      console.error('Error submitting report:', error);
      alert('Failed to submit report. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      projectId: '',
      file: null,
      comments: '',
    });
    setErrors({});
    onOpenChange(false);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Submit Project Report
          </DialogTitle>
          <DialogDescription>
            Upload your project report and provide additional comments for review
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Project Selection */}
          <div className="space-y-2">
            <Label htmlFor="project-select" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Submit to (Project)
              <span className="text-destructive">*</span>
            </Label>
            <Select 
              value={formData.projectId}
              onValueChange={handleProjectChange}
            >
              <SelectTrigger 
                id="project-select"
                className={`w-full ${errors.projectId ? 'border-destructive' : ''}`}
              >
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent className='bg-white'>
                {TEMP_PROJECTS.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    <div className="flex flex-col">
                      <span className="font-medium">{project.name}</span>
                      <span className="text-xs text-muted-foreground">{project.code}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.projectId && (
              <p className="text-sm text-destructive">{errors.projectId}</p>
            )}
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label htmlFor="file-upload" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Upload File(s)
              <span className="text-destructive">*</span>
            </Label>
            
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  variant="outline"
                  className={`w-full h-24 border-2 border-dashed hover:border-primary transition-colors ${
                    errors.file ? 'border-destructive' : ''
                  }`}
                  onClick={() => document.getElementById('file-upload')?.click()}
                >
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="h-6 w-6 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      Click to upload file(s)
                    </span>
                    <span className="text-xs text-muted-foreground">
                      PDF, DOC, DOCX, XLS, XLSX (Max {MAX_FILE_SIZE_MB}MB)
                    </span>
                  </div>
                </Button>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  accept=".pdf,.doc,.docx,.xls,.xlsx"
                  onChange={handleFileChange}
                />
              </div>

              {formData.file && (
                <div className="flex items-center justify-between p-3 bg-muted rounded-lg border">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <FileText className="h-5 w-5 text-primary flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{formData.file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(formData.file.size)}
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleRemoveFile}
                    className="flex-shrink-0 ml-2"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}

              {errors.file && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{errors.file}</AlertDescription>
                </Alert>
              )}
            </div>
          </div>

          {/* Comments */}
          <div className="space-y-2">
            <Label htmlFor="comments" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Comments
            </Label>
            <Textarea
              id="comments"
              placeholder="Add any additional comments or notes about this report..."
              value={formData.comments}
              onChange={(e) => handleCommentsChange(e.target.value)}
              rows={4}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              Optional: Provide context or additional information about the report
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button 
            variant="outline" 
            onClick={handleCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Submitting Report...' : 'Submit'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default SubmitReportModal;