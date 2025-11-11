"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  ChartContainer, 
  ChartTooltip, 
  ChartTooltipContent 
} from '@/components/ui/chart';
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';
import { 
  FolderPlus, 
  FileText, 
  ClipboardCheck, 
  Upload,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Clock,
  Users,
  DollarSign
} from 'lucide-react';

import CreateProjectModal from "./_components/CreateProjectModal";
// import SubmitReportModal from "./_components/SubmitReportModal";
// import EvaluateProjectModal from "./_components/EvaluateProjectModal";
// import UploadDocumentModal from "./_components/UploadDocumentModal";


// Temporary mock data - replace with API calls later
const MOCK_KEY_METRICS = {
  totalProjects: 24,
  activeProjects: 18,
  completedProjects: 6,
  totalBudget: 2500000,
  utilizationRate: 78,
  onTimeDelivery: 85
};

const MOCK_ACTIVITY_FEED = [
  {
    id: 1,
    type: 'project_created',
    title: 'New project created',
    description: 'Community Health Outreach Program',
    user: 'Dr. Maria Santos',
    timestamp: '2 hours ago',
    icon: 'folder'
  },
  {
    id: 2,
    type: 'report_submitted',
    title: 'Monthly report submitted',
    description: 'Education Enhancement Initiative - October 2024',
    user: 'Prof. Juan Dela Cruz',
    timestamp: '5 hours ago',
    icon: 'file'
  },
  {
    id: 3,
    type: 'evaluation_completed',
    title: 'Project evaluation completed',
    description: 'Agricultural Sustainability Project',
    user: 'Dr. Ana Reyes',
    timestamp: '1 day ago',
    icon: 'check'
  },
  {
    id: 4,
    type: 'document_uploaded',
    title: 'Document uploaded',
    description: 'Financial Statement Q3 2024',
    user: 'Accounting Office',
    timestamp: '2 days ago',
    icon: 'upload'
  }
];

const MOCK_RECENT_PROJECTS = [
  {
    id: 1,
    name: 'Community Health Outreach Program',
    status: 'active',
    progress: 65,
    leader: 'Dr. Maria Santos',
    budget: 450000,
    deadline: '2025-03-15'
  },
  {
    id: 2,
    name: 'Education Enhancement Initiative',
    status: 'active',
    progress: 42,
    leader: 'Prof. Juan Dela Cruz',
    budget: 320000,
    deadline: '2025-04-30'
  },
  {
    id: 3,
    name: 'Agricultural Sustainability Project',
    status: 'completed',
    progress: 100,
    leader: 'Dr. Ana Reyes',
    budget: 280000,
    deadline: '2024-10-31'
  },
  {
    id: 4,
    name: 'Youth Skills Development Program',
    status: 'active',
    progress: 28,
    leader: 'Ms. Sofia Martinez',
    budget: 195000,
    deadline: '2025-06-20'
  }
];

const MOCK_BUDGET_DATA = [
  { month: 'Jul', allocated: 380, spent: 320 },
  { month: 'Aug', allocated: 420, spent: 380 },
  { month: 'Sep', allocated: 450, spent: 410 },
  { month: 'Oct', allocated: 490, spent: 455 },
  { month: 'Nov', allocated: 510, spent: 480 }
];

const chartConfig = {
  allocated: {
    label: 'Allocated',
    color: 'hsl(var(--chart-1))'
  },
  spent: {
    label: 'Spent',
    color: 'hsl(var(--chart-2))'
  }
};

const ProjectMonitoringDashboard = () => {
  const [selectedAction, setSelectedAction] = useState(null);

  const quickActions = [
    {
      id: 'create_project',
      label: 'Create New Project',
      icon: FolderPlus,
      className: 'bg-primary hover:bg-primary/90 text-primary-foreground',
      description: 'Initialize a new ECRD project'
    },
    {
      id: 'submit_report',
      label: 'Submit Report',
      icon: FileText,
      className: 'bg-[var(--secondary-azure)] hover:bg-[var(--secondary-azure)]/90 text-white',
      description: 'Submit project progress report'
    },
    {
      id: 'evaluate_project',
      label: 'Evaluate Project',
      icon: ClipboardCheck,
      className: 'bg-[var(--secondary-sky)] hover:bg-[var(--secondary-sky)]/90 text-white',
      description: 'Conduct project evaluation'
    },
    {
      id: 'upload_document',
      label: 'Upload Document',
      icon: Upload,
      className: 'bg-accent hover:bg-accent/90 text-accent-foreground',
      description: 'Upload supporting documents'
    }
  ];

  const handleQuickAction = (actionId) => {
    setSelectedAction(actionId);
  };

  const closeModal = () => setSelectedAction(null);

  const getStatusBadgeVariant = (status) => {
    const statusMap = {
      active: 'default',
      completed: 'secondary',
      'on-hold': 'destructive',
      planning: 'outline'
    };
    return statusMap[status] || 'default';
  };

  const getActivityIcon = (type) => {
    const iconMap = {
      folder: FolderPlus,
      file: FileText,
      check: CheckCircle2,
      upload: Upload
    };
    return iconMap[type] || AlertCircle;
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-PH', {
      style: 'currency',
      currency: 'PHP',
      minimumFractionDigits: 0
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getCurrentTimestamp = () => {
    return new Date().toLocaleDateString('en-US', { 
      month: 'long', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header with USTP branding */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Project Monitoring Dashboard</h1>
            <p className="text-muted-foreground mt-1">burat</p>
          </div>
          <div className="text-sm text-muted-foreground">
            Last updated: {getCurrentTimestamp()}
          </div>
        </div>

        {/* Key Metrics Cards with USTP Blue accents */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card className="border-l-4 border-l-primary">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <FolderPlus className="h-4 w-4 text-primary" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">{MOCK_KEY_METRICS.totalProjects}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {MOCK_KEY_METRICS.activeProjects} active, {MOCK_KEY_METRICS.completedProjects} completed
              </p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-accent">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Budget</CardTitle>
              <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
                <DollarSign className="h-4 w-4 text-accent" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-accent">{formatCurrency(MOCK_KEY_METRICS.totalBudget)}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {MOCK_KEY_METRICS.utilizationRate}% utilization rate
              </p>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-[var(--secondary-sky)]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">On-Time Delivery</CardTitle>
              <div className="h-8 w-8 rounded-full bg-[var(--secondary-sky)]/10 flex items-center justify-center">
                <TrendingUp className="h-4 w-4 text-[var(--secondary-sky)]" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-[var(--secondary-sky)]">{MOCK_KEY_METRICS.onTimeDelivery}%</div>
              <p className="text-xs text-[var(--success)] mt-1">+5% from last quarter</p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions with USTP Color Scheme */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Frequently used operations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {quickActions.map((action) => {
                const IconComponent = action.icon;
                return (
                  <Button
                    key={action.id}
                    onClick={() => handleQuickAction(action.id)}
                    className={`${action.className} h-auto py-4 flex flex-col items-center gap-2 shadow-md hover:shadow-lg transition-all cursor-pointer`}
                  >
                    <IconComponent className="h-6 w-6" />
                    <span className="font-medium">{action.label}</span>
                  </Button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Modals */}
        {selectedAction === "create_project" && (
          <CreateProjectModal open={true} onOpenChange={closeModal} />
        )}
        {/* {selectedAction === "submit_report" && (
          <SubmitReportModal open={true} onOpenChange={closeModal} />
        )}
        {selectedAction === "evaluate_project" && (
          <EvaluateProjectModal open={true} onOpenChange={closeModal} />
        )}
        {selectedAction === "upload_document" && (
          <UploadDocumentModal open={true} onOpenChange={closeModal} />
        )} */}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Budget Tracking Chart with USTP Colors */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Budget Tracking
                <span className="h-2 w-2 rounded-full bg-primary animate-pulse"></span>
              </CardTitle>
              <CardDescription>Allocated vs Spent (in thousands PHP)</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={chartConfig} className="h-[300px] w-full">
                <BarChart data={MOCK_BUDGET_DATA}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis 
                    dataKey="month" 
                    tickLine={false}
                    axisLine={false}
                    className="text-xs"
                  />
                  <YAxis 
                    tickLine={false}
                    axisLine={false}
                    className="text-xs"
                  />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar 
                    dataKey="allocated" 
                    fill="#1a1b5f" 
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar 
                    dataKey="spent" 
                    fill="#fcb315" 
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>

          {/* Activity Feed with USTP Accents */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest updates and actions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {MOCK_ACTIVITY_FEED.map((activity) => {
                  const IconComponent = getActivityIcon(activity.icon);
                  return (
                    <div key={activity.id} className="flex gap-3 group">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 group-hover:bg-primary/20 flex items-center justify-center transition-colors">
                        <IconComponent className="h-4 w-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground">{activity.title}</p>
                        <p className="text-xs text-muted-foreground truncate">{activity.description}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-muted-foreground">{activity.user}</span>
                          <span className="text-xs text-muted-foreground/50">•</span>
                          <span className="text-xs text-muted-foreground">{activity.timestamp}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Projects with USTP Styling */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Projects</CardTitle>
            <CardDescription>Overview of current and completed projects</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {MOCK_RECENT_PROJECTS.map((project) => (
                <div 
                  key={project.id} 
                  className="border rounded-lg p-4 hover:border-primary/50 hover:shadow-md transition-all cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                        {project.name}
                      </h3>
                      <div className="flex items-center gap-3 mt-1">
                        <Badge variant={getStatusBadgeVariant(project.status)}>
                          {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                        </Badge>
                        <span className="text-sm text-muted-foreground flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          {project.leader}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-accent">{formatCurrency(project.budget)}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1 justify-end mt-1">
                        <Clock className="h-3 w-3" />
                        {formatDate(project.deadline)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium text-primary">{project.progress}%</span>
                    </div>
                    <Progress value={project.progress} className="h-2" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    

  );
};

export default ProjectMonitoringDashboard;