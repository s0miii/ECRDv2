import React, { useState, useEffect } from 'react';
import { Link2, Users, Briefcase, Copy, Check, ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';

// Temporary mock data - replace with actual API calls
const TEMP_PROJECTS = [
  { 
    id: '1', 
    title: 'Community Health Initiative', 
    code: 'CHI-2024-001',
    leaderId: '1',
    leaderName: 'Dr. Maria Santos'
  },
  { 
    id: '2', 
    title: 'Educational Support Program', 
    code: 'ESP-2024-002',
    leaderId: '2',
    leaderName: 'Prof. Juan Dela Cruz'
  },
  { 
    id: '3', 
    title: 'Agricultural Development Project', 
    code: 'ADP-2024-003',
    leaderId: '3',
    leaderName: 'Dr. Ana Reyes'
  },
  { 
    id: '4', 
    title: 'Youth Empowerment Initiative', 
    code: 'YEI-2024-004',
    leaderId: '1',
    leaderName: 'Dr. Maria Santos'
  },
];

interface FormData {
  projectId: string;
}

interface FormErrors {
  projectId?: string;
}

interface ProjectEvaluationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const ProjectEvaluationModal: React.FC<ProjectEvaluationModalProps> = ({ 
  open, 
  onOpenChange 
}) => {
  const [formData, setFormData] = useState<FormData>({
    projectId: '',
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedLink, setGeneratedLink] = useState<string>('');
  const [isCopied, setIsCopied] = useState(false);
  const [selectedProject, setSelectedProject] = useState<typeof TEMP_PROJECTS[0] | null>(null);

  useEffect(() => {
    if (formData.projectId) {
      const project = TEMP_PROJECTS.find(p => p.id === formData.projectId);
      setSelectedProject(project || null);
    } else {
      setSelectedProject(null);
    }
  }, [formData.projectId]);

  useEffect(() => {
    if (isCopied) {
      const timer = setTimeout(() => setIsCopied(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [isCopied]);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.projectId) {
      newErrors.projectId = 'Please select a project';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleProjectChange = (value: string) => {
    setFormData({ projectId: value });
    setGeneratedLink('');
    setIsCopied(false);
    
    if (errors.projectId) {
      setErrors({});
    }
  };

  const generateUniqueToken = (): string => {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  };

  const handleGenerateLink = async () => {
    if (!validateForm()) {
      return;
    }

    setIsGenerating(true);

    try {
      // TODO: Replace with actual API call to Django REST Framework
      // Example:
      // const response = await fetch('/api/evaluation-links/', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ project_id: formData.projectId })
      // });
      // const data = await response.json();
      // setGeneratedLink(data.evaluation_url);
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const token = generateUniqueToken();
      const baseUrl = window.location.origin;
      const evaluationUrl = `${baseUrl}/evaluate/${formData.projectId}/${token}`;
      
      console.log('Evaluation link data:', {
        projectId: formData.projectId,
        projectTitle: selectedProject?.title,
        token: token,
        generatedUrl: evaluationUrl,
      });
      
      setGeneratedLink(evaluationUrl);
    } catch (error) {
      console.error('Error generating evaluation link:', error);
      alert('Failed to generate evaluation link. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(generatedLink);
      setIsCopied(true);
    } catch (error) {
      console.error('Error copying to clipboard:', error);
      alert('Failed to copy link. Please copy manually.');
    }
  };

  const handleOpenLink = () => {
    window.open(generatedLink, '_blank');
  };

  const handleClose = () => {
    setFormData({ projectId: '' });
    setErrors({});
    setGeneratedLink('');
    setIsCopied(false);
    setSelectedProject(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-primary" />
            Generate Project Evaluation Link
          </DialogTitle>
          <DialogDescription>
            Create a shareable link for participants to evaluate the project
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4 overflow-y-auto flex-1">
          {/* Project Selection */}
          <div className="space-y-2">
            <Label htmlFor="project-select" className="flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              Select Project
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
                <SelectValue placeholder="Select a project to evaluate" />
              </SelectTrigger>
              <SelectContent className='bg-white'>
                {TEMP_PROJECTS.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    <div className="flex flex-col">
                      <span className="font-medium">{project.title}</span>
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

          {/* Project Leader Display */}
          {selectedProject && (
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                Project Leader
              </Label>
              <div className="flex items-center gap-3 p-3 bg-muted rounded-lg border">
                <Users className="h-5 w-5 text-primary" />
                <div>
                  <p className="text-sm font-medium">{selectedProject.leaderName}</p>
                  <p className="text-xs text-muted-foreground">
                    Leading {selectedProject.title}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Generate Button */}
          {selectedProject && !generatedLink && (
            <Button 
              onClick={handleGenerateLink}
              disabled={isGenerating}
              className="w-full"
            >
              {isGenerating ? 'Generating Link...' : 'Generate Evaluation Link'}
            </Button>
          )}

          {/* Generated Link Display */}
          {generatedLink && (
            <div className="space-y-3">
              <Alert className="bg-green-50 border-green-200">
                <Check className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  Evaluation link generated successfully! Share this link with participants.
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Link2 className="w-4 h-4" />
                  Shareable Link
                </Label>
                <div className="flex gap-2">
                  <Input
                    value={generatedLink}
                    readOnly
                    className="font-mono text-sm bg-muted"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleCopyLink}
                    className="flex-shrink-0"
                  >
                    {isCopied ? (
                      <Check className="h-4 w-4 text-green-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleOpenLink}
                    className="flex-shrink-0"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  {isCopied ? 'Link copied to clipboard!' : 'Click the copy icon to copy the link'}
                </p>
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="text-sm font-medium text-blue-900 mb-2">
                  How to use this link:
                </h4>
                <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
                  <li>Share this link with project participants via email or messaging</li>
                  <li>Participants can access the evaluation form without logging in</li>
                  <li>The link is unique to this project and evaluation session</li>
                  <li>You can generate a new link anytime for additional evaluations</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t flex-shrink-0">
          <Button 
            variant="outline" 
            onClick={handleClose}
          >
            {generatedLink ? 'Done' : 'Cancel'}
          </Button>
          {generatedLink && (
            <Button 
              onClick={() => {
                setFormData({ projectId: '' });
                setGeneratedLink('');
                setIsCopied(false);
                setSelectedProject(null);
              }}
            >
              Generate Another Link
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ProjectEvaluationModal;