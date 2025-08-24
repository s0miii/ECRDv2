from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator
from django.utils import timezone
import uuid


# Constants for choices - avoiding hard-coded values
class UserTypeChoices(models.TextChoices):
    SYSTEM_ADMIN = 'SYSTEM_ADMIN', 'System Administrator'
    EXTENSION_ADMIN_STAFF = 'EXTENSION_ADMIN_STAFF', 'Extension Administrative Staff'
    PROJECT_LEADER = 'PROJECT_LEADER', 'Project Leader'
    PROPONENT = 'PROPONENT', 'Proponent'
    EXTENSION_COORDINATOR = 'EXTENSION_COORDINATOR', 'College Extension Coordinator'
    DEPARTMENT_HEAD = 'DEPARTMENT_HEAD', 'Department Head'
    COLLEGE_HEAD = 'COLLEGE_HEAD', 'College Head/Dean'


class ProjectTypeChoices(models.TextChoices):
    EXTENSION = 'EXTENSION', 'Extension Project'
    TRAINING = 'TRAINING', 'Training Program'
    COMMUNITY_SERVICE = 'COMMUNITY_SERVICE', 'Community Service'
    RESEARCH_EXTENSION = 'RESEARCH_EXTENSION', 'Research Extension'
    CAPACITY_BUILDING = 'CAPACITY_BUILDING', 'Capacity Building'


class ProjectStatusChoices(models.TextChoices):
    PLANNING = 'PLANNING', 'Planning'
    APPROVED = 'APPROVED', 'Approved'
    ONGOING = 'ONGOING', 'Ongoing'
    COMPLETED = 'COMPLETED', 'Completed'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    CANCELLED = 'CANCELLED', 'Cancelled'


class RequirementStatusChoices(models.TextChoices):
    PENDING = 'PENDING', 'Pending Submission'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    REVISION_NEEDED = 'REVISION_NEEDED', 'Revision Needed'


class ApprovalStatusChoices(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class FileTypeChoices(models.TextChoices):
    DOCUMENT = 'DOCUMENT', 'Document'
    IMAGE = 'IMAGE', 'Image'
    VIDEO = 'VIDEO', 'Video'
    PRESENTATION = 'PRESENTATION', 'Presentation'
    SPREADSHEET = 'SPREADSHEET', 'Spreadsheet'
    OTHER = 'OTHER', 'Other'


class ReportTypeChoices(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly Report'
    QUARTERLY = 'QUARTERLY', 'Quarterly Report'
    ANNUAL = 'ANNUAL', 'Annual Report'
    FINAL = 'FINAL', 'Final Report'


class ReportStatusChoices(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    APPROVED = 'APPROVED', 'Approved'
    REVISION_NEEDED = 'REVISION_NEEDED', 'Revision Needed'


class AttendanceStatusChoices(models.TextChoices):
    PRESENT = 'PRESENT', 'Present'
    ABSENT = 'ABSENT', 'Absent'
    LATE = 'LATE', 'Late'
    EXCUSED = 'EXCUSED', 'Excused'


class TrainerStatusChoices(models.TextChoices):
    SCHEDULED = 'SCHEDULED', 'Scheduled'
    ONGOING = 'ONGOING', 'Ongoing'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class EvaluationTypeChoices(models.TextChoices):
    PROJECT = 'PROJECT', 'Project Evaluation'
    TRAINER = 'TRAINER', 'Trainer Evaluation'
    OVERALL = 'OVERALL', 'Overall Program Evaluation'


class LinkTypeChoices(models.TextChoices):
    ATTENDANCE = 'ATTENDANCE', 'Attendance Link'
    EVALUATION = 'EVALUATION', 'Evaluation Link'
    FEEDBACK = 'FEEDBACK', 'Feedback Link'


class EmailTypeChoices(models.TextChoices):
    NOTIFICATION = 'NOTIFICATION', 'Notification'
    REMINDER = 'REMINDER', 'Reminder'
    APPROVAL = 'APPROVAL', 'Approval Notification'
    REJECTION = 'REJECTION', 'Rejection Notification'
    DEADLINE = 'DEADLINE', 'Deadline Alert'
    WELCOME = 'WELCOME', 'Welcome Email'
    COMPLETION = 'COMPLETION', 'Completion Notice'


class CommunicationStatusChoices(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    FAILED = 'FAILED', 'Failed'
    DELIVERED = 'DELIVERED', 'Delivered'


class MemberRoleChoices(models.TextChoices):
    MEMBER = 'MEMBER', 'Team Member'


# Constants for validation
MIN_BUDGET = 0
MIN_DURATION_HOURS = 0.5
MIN_RATING = 1
MAX_RATING = 5
MIN_PERCENTAGE = 0
MAX_PERCENTAGE = 100
BYTES_TO_MB = 1024 * 1024


class TimestampedModel(models.Model):
    """Abstract base model with created_at and updated_at timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class College(TimestampedModel):
    """Model representing academic colleges within the university"""
    college_id = models.AutoField(primary_key=True)
    college_name = models.CharField(max_length=200, unique=True)
    college_code = models.CharField(max_length=10, unique=True)
    dean = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colleges_as_dean',
        limit_choices_to={'user_type': UserTypeChoices.COLLEGE_HEAD}
    )
    extension_coordinator = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colleges_as_coordinator',
        limit_choices_to={'user_type': UserTypeChoices.EXTENSION_COORDINATOR}
    )

    class Meta:
        db_table = 'colleges'
        ordering = ['college_name']
        verbose_name = 'College'
        verbose_name_plural = 'Colleges'
    
    def __str__(self):
        return f"{self.college_code} - {self.college_name}"


class Department(TimestampedModel):
    """Model representing departments within colleges"""
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=200)
    department_code = models.CharField(max_length=10)
    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='departments'
    )
    department_head = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments_as_head',
        limit_choices_to={'user_type': UserTypeChoices.DEPARTMENT_HEAD}
    )

    class Meta:
        db_table = 'departments'
        ordering = ['college', 'department_name']
        unique_together = ['department_code', 'college']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return f"{self.college.college_code}-{self.department_code} - {self.department_name}"


class CustomUser(AbstractUser):
    """
    Extended user model with university-specific fields and roles.
    
    This model replaces Django's default User model and resolves the
    reverse accessor conflicts by explicitly setting related_name.
    """
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    user_type = models.CharField(max_length=25, choices=UserTypeChoices.choices)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    college = models.ForeignKey(
        College,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Fix for reverse accessor conflicts - explicitly set related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_users',  # Changed from default 'user_set'
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_users',  # Changed from default 'user_set'
        related_query_name='custom_user',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'user_type']

    class Meta:
        db_table = 'custom_users'
        ordering = ['last_name', 'first_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_user_type_display()})"
    
    @property
    def overall_performance_score(self):
        """Calculate overall performance score based on all metrics"""
        # Simple average of normalized scores (0-5 scale)
        completion_score = (self.completion_percentage / 100) * MAX_RATING
        budget_score = (self.budget_utilization / 100) * MAX_RATING
        
        total_score = (completion_score + budget_score + 
                      float(self.impact_score) + float(self.sustainability_rating)) / 4
        return round(total_score, 2)


class Project(TimestampedModel):
    """Model representing extension projects"""
    project_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=300)
    description = models.TextField()
    project_type = models.CharField(max_length=20, choices=ProjectTypeChoices.choices)
    status = models.CharField(
        max_length=15, 
        choices=ProjectStatusChoices.choices, 
        default=ProjectStatusChoices.PLANNING
    )
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(MIN_BUDGET)]
    )
    location = models.CharField(max_length=200)
    project_leader = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='led_projects',
        limit_choices_to={'user_type': UserTypeChoices.PROJECT_LEADER}
    )
    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    expected_beneficiaries = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def duration_days(self):
        """Calculate project duration in days"""
        return (self.end_date - self.start_date).days
    
    @property
    def is_active(self):
        """Check if project is currently active"""
        active_statuses = [ProjectStatusChoices.APPROVED, ProjectStatusChoices.ONGOING]
        return self.status in active_statuses


class ProjectMember(models.Model):
    """Model representing project team members"""
    member_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='project_memberships'
    )
    role = models.CharField(
        max_length=15, 
        choices=MemberRoleChoices.choices, 
        default=MemberRoleChoices.MEMBER
    )
    assigned_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'project_members'
        ordering = ['project', 'role']
        unique_together = ['project', 'user']
        verbose_name = 'Project Member'
        verbose_name_plural = 'Project Members'

    def __str__(self):
        return f"{self.user.full_name} - {self.project.title} ({self.get_role_display()})"


class Trainer(TimestampedModel):
    """Model representing internal and external trainers"""
    trainer_id = models.AutoField(primary_key=True)
    trainer_name = models.CharField(max_length=200)
    email = models.EmailField(validators=[EmailValidator()])
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    expertise = models.TextField()
    bio = models.TextField(blank=True, null=True)
    is_internal = models.BooleanField(
        default=False, 
        help_text="Is this trainer from USTP?"
    )
    cv_file = models.FileField(upload_to='trainer_cvs/', blank=True, null=True)

    class Meta:
        db_table = 'trainers'
        ordering = ['trainer_name']
        verbose_name = 'Trainer'
        verbose_name_plural = 'Trainers'

    def __str__(self):
        trainer_type = 'Internal' if self.is_internal else 'External'
        return f"{self.trainer_name} ({trainer_type})"


class ProjectTrainer(models.Model):
    """Model representing trainer assignments to projects"""
    assignment_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='trainer_assignments'
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name='project_assignments'
    )
    training_date = models.DateField()
    training_topic = models.CharField(max_length=300)
    duration_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        validators=[MinValueValidator(MIN_DURATION_HOURS)]
    )
    location = models.CharField(max_length=200)
    status = models.CharField(
        max_length=15, 
        choices=TrainerStatusChoices.choices, 
        default=TrainerStatusChoices.SCHEDULED
    )
    notes = models.TextField(blank=True, null=True)
    honorarium = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True
    )

    class Meta:
        db_table = 'project_trainers'
        ordering = ['training_date']
        verbose_name = 'Project Trainer'
        verbose_name_plural = 'Project Trainers'

    def __str__(self):
        return f"{self.trainer.trainer_name} - {self.project.title} ({self.training_date})"


class DocumentaryRequirement(TimestampedModel):
    """Model representing project documentary requirements"""
    requirement_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='requirements'
    )
    requirement_name = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=20, 
        choices=RequirementStatusChoices.choices, 
        default=RequirementStatusChoices.PENDING
    )
    assigned_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='assigned_requirements'
    )
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_requirements'
    )
    submitted_date = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requirements'
    )
    approval_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)  # Fixed typo

    class Meta:
        db_table = 'documentary_requirements'
        ordering = ['due_date', 'requirement_name']
        verbose_name = 'Documentary Requirement'
        verbose_name_plural = 'Documentary Requirements'

    def __str__(self):
        return f"{self.project.title} - {self.requirement_name}"
    
    @property
    def is_overdue(self):
        """Check if requirement is overdue"""
        overdue_statuses = [RequirementStatusChoices.PENDING, RequirementStatusChoices.REVISION_NEEDED]
        return (self.due_date < timezone.now().date() and 
                self.status in overdue_statuses)


class File(models.Model):
    """Model representing project files and documents"""
    file_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='files'
    )
    requirement = models.ForeignKey(
        DocumentaryRequirement,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='files'
    )
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=15, choices=FileTypeChoices.choices)
    file_path = models.FileField(upload_to='project_files/%Y/%m/')
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='uploaded_files'
    )
    uploaded_date = models.DateTimeField(auto_now_add=True)  # Fixed field name consistency
    approval_status = models.CharField(
        max_length=15, 
        choices=ApprovalStatusChoices.choices, 
        default=ApprovalStatusChoices.PENDING
    )
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_files'
    )
    approval_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'files'
        ordering = ['-uploaded_date']  # Fixed field name
        verbose_name = 'File'
        verbose_name_plural = 'Files'

    def __str__(self):
        return f"{self.file_name} - {self.project.title}"
    
    @property
    def file_size_mb(self):
        """Convert file size from bytes to MB"""
        return round(self.file_size / BYTES_TO_MB, 2)


class AccomplishmentReport(models.Model):
    """Model representing project accomplishment reports"""
    report_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='accomplishment_reports'
    )
    report_type = models.CharField(max_length=15, choices=ReportTypeChoices.choices)
    reporting_period = models.CharField(max_length=50)
    achievements = models.TextField()
    challenges = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    submitted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='submitted_reports'
    )
    submission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        choices=ReportStatusChoices.choices, 
        default=ReportStatusChoices.DRAFT
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports'
    )
    review_date = models.DateTimeField(blank=True, null=True)
    review_comments = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'accomplishment_reports'
        ordering = ['-submission_date']
        unique_together = ['project', 'report_type', 'reporting_period']
        verbose_name = 'Accomplishment Report'
        verbose_name_plural = 'Accomplishment Reports'

    def __str__(self):
        return f"{self.project.title} - {self.get_report_type_display()} ({self.reporting_period})"


class AttendanceTemplate(TimestampedModel):
    """Model representing attendance sheet templates"""
    template_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='attendance_templates'
    )
    template_name = models.CharField(max_length=200)
    session_date = models.DateField()
    session_time = models.TimeField()
    venue = models.CharField(max_length=200)
    expected_participants = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='created_templates'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'attendance_templates'
        ordering = ['session_date', 'session_time']
        verbose_name = 'Attendance Template'
        verbose_name_plural = 'Attendance Templates'

    def __str__(self):
        return f"{self.template_name} - {self.session_date}"


class AttendanceRecord(models.Model):
    """Model representing individual attendance records"""
    attendance_id = models.AutoField(primary_key=True)
    template = models.ForeignKey(
        AttendanceTemplate,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    participant_name = models.CharField(max_length=200)
    participant_email = models.EmailField(validators=[EmailValidator()])
    organization = models.CharField(max_length=200, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    check_in_time = models.DateTimeField(blank=True, null=True)
    check_out_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=10, 
        choices=AttendanceStatusChoices.choices, 
        default=AttendanceStatusChoices.ABSENT
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'attendance_records'
        ordering = ['participant_name']
        unique_together = ['template', 'participant_email']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'

    def __str__(self):
        return f"{self.participant_name} - {self.template.template_name}"


class Evaluation(models.Model):
    """Model representing project and trainer evaluations"""
    evaluation_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )
    evaluator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='given_evaluations',
        blank=True,
        null=True
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='evaluations'
    )
    evaluation_type = models.CharField(max_length=15, choices=EvaluationTypeChoices.choices)
    rating = models.IntegerField(
        validators=[MinValueValidator(MIN_RATING), MaxValueValidator(MAX_RATING)]
    )
    feedback = models.TextField()
    evaluation_date = models.DateTimeField(auto_now_add=True)
    is_anonymous = models.BooleanField(default=False)
    evaluator_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="For anonymous evaluations"
    )
    evaluator_email = models.EmailField(
        blank=True, 
        null=True, 
        help_text="For anonymous evaluations"
    )

    class Meta:
        db_table = 'evaluations'
        ordering = ['-evaluation_date']
        verbose_name = 'Evaluation'
        verbose_name_plural = 'Evaluations'

    def __str__(self):
        evaluator_name = (self.evaluator.full_name if self.evaluator 
                         else self.evaluator_name or "Anonymous")
        return f"{evaluator_name} - {self.project.title} ({self.rating}/{MAX_RATING})"


class EvaluationLink(TimestampedModel):
    """Model representing shareable links for evaluations and attendance"""
    link_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='evaluation_links'
    )
    link_type = models.CharField(max_length=15, choices=LinkTypeChoices.choices)
    unique_token = models.UUIDField(default=uuid.uuid4, unique=True)
    expiration_date = models.DateTimeField()
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='created_links'
    )
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)
    max_usage = models.PositiveIntegerField(
        blank=True, 
        null=True, 
        help_text="Leave blank for unlimited usage"
    )

    class Meta:
        db_table = 'evaluation_links'
        ordering = ['-created_at']
        verbose_name = 'Evaluation Link'
        verbose_name_plural = 'Evaluation Links'

    def __str__(self):
        return f"{self.get_link_type_display()} - {self.project.title}"

    @property
    def is_expired(self):
        """Check if the link has expired"""
        return timezone.now() > self.expiration_date

    @property
    def is_usage_exceeded(self):
        """Check if the usage limit has been exceeded"""
        if self.max_usage is None:
            return False
        return self.usage_count >= self.max_usage

    @property
    def is_valid(self):
        """Check if the link is valid (active, not expired, usage not exceeded)"""
        return (self.is_active and 
                not self.is_expired and 
                not self.is_usage_exceeded)


class ProjectPerformance(models.Model):
    """Model representing project performance metrics"""
    performance_id = models.AutoField(primary_key=True)
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='performance'
    )
    total_beneficiaries = models.PositiveIntegerField(default=0)
    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(MIN_PERCENTAGE), MaxValueValidator(MAX_PERCENTAGE)],
        default=0
    )
    budget_utilization = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(MIN_PERCENTAGE), MaxValueValidator(MAX_PERCENTAGE)],
        default=0
    )
    impact_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(MIN_RATING), MaxValueValidator(MAX_RATING)],
        default=0
    )
    sustainability_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(MIN_RATING), MaxValueValidator(MAX_RATING)],
        default=0
    )
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_performances'
    )

    class Meta:
        db_table = 'project_performance'
        ordering = ['-last_updated']
        verbose_name = 'Project Performance'
        verbose_name_plural = 'Project Performances'

    def __str__(self):
        return f"{self.project.title} - Performance Metrics"

    @property
    def overall_performance_score(self):
        """Calculate overall performance score based on all metrics"""
        # Simple average of normalized scores (0-5 scale)
        completion_score = (self.completion_percentage / 100) * MAX_RATING
        budget_score = (self.budget_utilization / 100) * MAX_RATING
        
        total_score = (completion_score + budget_score + 
                      float(self.impact_score) + float(self.sustainability_rating)) / 4
        return round(total_score, 2)


class Communication(models.Model):
    """Model representing email communications and notifications"""
    communication_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='communications',
        blank=True,
        null=True
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_communications'
    )
    recipient_email = models.EmailField(validators=[EmailValidator()])
    recipient_name = models.CharField(max_length=200, blank=True, null=True)
    email_type = models.CharField(max_length=15, choices=EmailTypeChoices.choices)
    subject = models.CharField(max_length=300)
    message = models.TextField()
    sent_date = models.DateTimeField(auto_now_add=True)
    is_automated = models.BooleanField(default=True)
    status = models.CharField(
        max_length=15, 
        choices=CommunicationStatusChoices.choices, 
        default=CommunicationStatusChoices.PENDING
    )
    error_message = models.TextField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'communications'
        ordering = ['-sent_date']
        verbose_name = 'Communication'
        verbose_name_plural = 'Communications'

    def __str__(self):
        return f"{self.subject} -> {self.recipient_email} ({self.get_status_display()})"

    @property
    def is_delivered(self):
        """Check if the communication was successfully delivered"""
        return self.status == CommunicationStatusChoices.DELIVERED

    @property
    def is_read(self):
        """Check if the communication has been read"""
        return self.read_at is not None

    def mark_as_read(self):
        """Mark the communication as read"""
        if not self.is_read:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])