import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Calendar, Building2, Users, Target, Briefcase } from 'lucide-react';

// Temporary data - to be replaced with API calls later
const TEMP_LEADERS = [
  { id: '1', name: 'Dr. Maria Santos' },
  { id: '2', name: 'Prof. Juan Dela Cruz' },
  { id: '3', name: 'Dr. Ana Reyes' },
];

const TEMP_COLLEGES = [
  { id: '1', name: 'College of Engineering' },
  { id: '2', name: 'College of Science' },
  { id: '3', name: 'College of Business Administration' },
  { id: '4', name: 'College of Education' },
];

const TEMP_PARTNER_AGENCIES = [
  { id: '1', name: 'Department of Science and Technology (DOST)' },
  { id: '2', name: 'Local Government Unit - Cagayan de Oro' },
  { id: '3', name: 'Department of Agriculture (DA)' },
  { id: '4', name: 'Philippine Council for Health Research and Development' },
];

interface FormData {
  title: string;
  leaderId: string;
  collegeId: string;
  targetDate: string;
  partnerAgencyId: string;
}

interface FormErrors {
  title?: string;
  leaderId?: string;
  collegeId?: string;
  targetDate?: string;
  partnerAgencyId?: string;
}

interface CreateProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ 
  open, 
  onOpenChange 
}) => {
  const [formData, setFormData] = useState<FormData>({
    title: '',
    leaderId: '',
    collegeId: '',
    targetDate: '',
    partnerAgencyId: '',
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Project title is required';
    } else if (formData.title.trim().length < 5) {
      newErrors.title = 'Project title must be at least 5 characters';
    }

    if (!formData.leaderId) {
      newErrors.leaderId = 'Project leader is required';
    }

    if (!formData.collegeId) {
      newErrors.collegeId = 'College/Campus is required';
    }

    if (!formData.targetDate) {
      newErrors.targetDate = 'Target date is required';
    } else {
      const selectedDate = new Date(formData.targetDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      if (selectedDate < today) {
        newErrors.targetDate = 'Target date must be in the future';
      }
    }

    if (!formData.partnerAgencyId) {
      newErrors.partnerAgencyId = 'Partner agency is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // TODO: Replace with actual API call to Django REST Framework
      // Example: await fetch('/api/projects/', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(formData)
      // });
      
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      console.log('Project data to be submitted:', formData);
      
      // Reset form and close modal after successful submission
      setFormData({
        title: '',
        leaderId: '',
        collegeId: '',
        targetDate: '',
        partnerAgencyId: '',
      });
      setErrors({});
      onOpenChange(false);
      
      // Show success message (you can use a toast library later)
      alert('Project created successfully!');
    } catch (error) {
      console.error('Error creating project:', error);
      alert('Failed to create project. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      title: '',
      leaderId: '',
      collegeId: '',
      targetDate: '',
      partnerAgencyId: '',
    });
    setErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary" />
            Create New Project
          </DialogTitle>
          <DialogDescription>
            Fill in the project details to create a new monitoring entry
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="title" className="flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              Project Title
              <span className="text-destructive">*</span>
            </Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => handleInputChange('title', e.target.value)}
              placeholder="Enter project title"
              className={errors.title ? 'border-destructive' : ''}
            />
            {errors.title && (
              <p className="text-sm text-destructive">{errors.title}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="leader" className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              Project Leader
              <span className="text-destructive">*</span>
            </Label>
            <Select 
              value={formData.leaderId}
              onValueChange={(value) => handleInputChange('leaderId', value)}
            >
              <SelectTrigger className={errors.leaderId ? 'border-destructive' : ''}>
                <SelectValue placeholder="Select project leader" />
              </SelectTrigger>
              <SelectContent>
                {TEMP_LEADERS.map(leader => (
                  <SelectItem key={leader.id} value={leader.id}>
                    {leader.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.leaderId && (
              <p className="text-sm text-destructive">{errors.leaderId}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="college" className="flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              College/Campus
              <span className="text-destructive">*</span>
            </Label>
            <Select 
              value={formData.collegeId}
              onValueChange={(value) => handleInputChange('collegeId', value)}
            >
              <SelectTrigger className={errors.collegeId ? 'border-destructive' : ''}>
                <SelectValue placeholder="Select college/campus" />
              </SelectTrigger>
              <SelectContent>
                {TEMP_COLLEGES.map(college => (
                  <SelectItem key={college.id} value={college.id}>
                    {college.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.collegeId && (
              <p className="text-sm text-destructive">{errors.collegeId}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="targetDate" className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Target Date
              <span className="text-destructive">*</span>
            </Label>
            <Input
              id="targetDate"
              type="date"
              value={formData.targetDate}
              onChange={(e) => handleInputChange('targetDate', e.target.value)}
              className={errors.targetDate ? 'border-destructive' : ''}
            />
            {errors.targetDate && (
              <p className="text-sm text-destructive">{errors.targetDate}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="partnerAgency" className="flex items-center gap-2">
              <Target className="w-4 h-4" />
              Partner Agency
              <span className="text-destructive">*</span>
            </Label>
            <Select 
              value={formData.partnerAgencyId}
              onValueChange={(value) => handleInputChange('partnerAgencyId', value)}
            >
              <SelectTrigger className={errors.partnerAgencyId ? 'border-destructive' : ''}>
                <SelectValue placeholder="Select partner agency" />
              </SelectTrigger>
              <SelectContent>
                {TEMP_PARTNER_AGENCIES.map(agency => (
                  <SelectItem key={agency.id} value={agency.id}>
                    {agency.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.partnerAgencyId && (
              <p className="text-sm text-destructive">{errors.partnerAgencyId}</p>
            )}
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
            {isSubmitting ? 'Creating Project...' : 'Create Project'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CreateProjectModal;