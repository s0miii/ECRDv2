from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator
from django.utils import timezone
import uuid




class College(models.Model):
    college_id = models.AutoField(primary_key=True)
    college_name = models.CharField(max_length=200, unique=True)
    college_code = models.CharField(max_length=10, unique=True)
    dean = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colleges_as_dean',
        limit_choices_to={'user_type': 'COLLEGE_HEAD'}
    )
    extension_coordinator = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colleges_as_coordinator',
        limit_choices_to={'user_type': 'EXTENSION_COORDINATOR'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'colleges'
        ordering = ['college_name']
    
    def __str__(self):
        return f"{self.college_code} - {self.college_name}"
    

class Department(models.Model):
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
        limit_choices_to={'user_type': 'DEPARTMENT_HEAD'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'
        unique_together = ['department_code', 'college']
        ordering = ['college', 'department_name']

    def __str__(self):
        return f"{self.college.college_code}-{self.department_code} - {self.department_name}"
    

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('SYSTEM_ADMIN', 'System Administrator'),
        ('EXTENSION_ADMIN_STAFF', 'Extension Administrative Staff'),
        ('PROJECT_LEADER', 'Project Leader'),
        ('PROPONENT', 'Proponent'),
        ('EXTENSION_COORDINATOR', 'College Extension Coordinator'),
        ('DEPARTMENT_HEAD', 'Department Head'),
        ('COLLEGE_HEAD', 'College Head/Dean'),
    ]

    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    user_type = models.CharField(max_length=25, choices=USER_TYPE_CHOICES)
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'user_type']

    class Meta:
        db_table = 'custom_users'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_user_type_display()})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_managed_projects(self):
        """Return projects where this user is the project leader"""
        return self.led_projects.all()
    

class Project(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('EXTENSION', 'Extension Project'),
        ('TRAINING', 'Training Program'),
        ('COMMUNITY_SERVICE', 'Community Service'),
        ('RESEARCH_EXTENSION', 'Research Extension'),
        ('CAPACITY_BUILDING', 'Capacity Building'),
    ]

    STATUS_CHOICES = [
        ('PLANNING', 'Planning'),
        ('APPROVED', 'Approved'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('SUSPENDED', 'Suspended'),
        ('CANCELLED', 'Cancelled'),
    ]

    project_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=300)
    description = models.TextField()
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PLANNING')
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    location = models.CharField(max_length=200)
    
    project_leader = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='led_projects',
        limit_choices_to={'user_type': 'PROJECT_LEADER'}
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days
    
    @property
    def is_active(self):
        return self.status in ['APPROVED', 'ONGOING']



class ProjectMember(models.Model):
    ROLE_CHOICES = [
        ('MEMBER', 'Team Member'),
    ]

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
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='MEMBER')
    assigned_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'project_members'
        unique_together = ['project', 'user']
        ordering = ['project', 'role']

    def __str__(self):
        return f"{self.user.full_name} - {self.project.title} ({self.get_role_display()})"
    


class Trainer(models.Model):
    trainer_id = models.AutoField(primary_key=True)
    trainer_name = models.CharField(max_length=200)
    email = models.EmailField(validators=[EmailValidator()])
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    expertise = models.TextField()
    bio = models.TextField(blank=True, null=True)
    is_internal = models.BooleanField(default=False, help_text="Is this trainer from USTP?")
    cv_file = models.FileField(upload_to='trainer_cvs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trainers'
        ordering = ['trainer_name']

    def __str__(self):
        return f"{self.trainer_name} ({'Internal' if self.is_internal else 'External'})"
    


class ProjectTrainer(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

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
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, validators=[MinValueValidator(0.5)])
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='SCHEDULED')
    notes = models.TextField(blank=True, null=True)
    honorarium = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'project_trainers'
        ordering = ['training_date']

    def __str__(self):
        return f"{self.trainer.trainer_name} - {self.project.title} ({self.training_date})"
    


class DocumentaryRequirement(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Submission'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REVISION_NEEDED', 'Revision Needed'),
    ]

    requirement_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='requirements'
    )
    requirement_name = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    status = models .CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
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
    rejection_reasion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documentary_requirements'
        ordering = ['due_date', 'requirement_name']

    def __str__(self):
        return f"{self.project.title} - {self.requirement_name}"
    
    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.status in ['PENDING', 'REVISION_NEEDED']
    


class File(models.Model):
    FILE_TYPE_CHOICES = [
        ('DOCUMENT', 'Document'),
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('PRESENTATION', 'Presentation'),
        ('SPREADSHEET', 'Spreadsheet'),
        ('OTHER', 'Other'),
    ]

    APPROVAL_STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

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
    file_type = models.CharField(max_length=15, choices=FILE_TYPE_CHOICES)
    file_path = models.FileField(upload_to='project_files/%Y/%m/')
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='uploaded_files'
    )
    uploaded_date = models.DateTimeField(auto_now_add=True)
    approval_status = models.CharField(max_length=15, choices=APPROVAL_STATUS_CHOICES, default='PENDING')
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
        ordering = ["-upload_date"]

    def __str__(self):
        return f"{self.file_name} - {self.project.title}"
    
    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2)



class AccomplishmentReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('MONTHLY', 'Monthly Report'),
        ('QUARTERLY', 'Quarterly Report'),
        ('ANNUAL', 'Annual Report'),
        ('FINAL', 'Final Report'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REVISION_NEEDED', 'Revision Needed'),
    ]

    report_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='accomplishment_reports'
    )
    report_type = models.CharField(max_length=15, choices=REPORT_TYPE_CHOICES)
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
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

    def __str__(self):
        return f"{self.project.title} - {self.get_report_type_display()} ({self.reporting_period})"


class AttendanceTemplate(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'attendance_templates'
        ordering = ['session_date', 'session_time']

    def __str__(self):
        return f"{self.template_name} - {self.session_date}"


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused'),
    ]

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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABSENT')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'attendance_records'
        unique_together = ['template', 'participant_email']
        ordering = ['participant_name']

    def __str__(self):
        return f"{self.participant_name} - {self.template.template_name}"


class Evaluation(models.Model):
    EVALUATION_TYPE_CHOICES = [
        ('PROJECT', 'Project Evaluation'),
        ('TRAINER', 'Trainer Evaluation'),
        ('OVERALL', 'Overall Program Evaluation'),
    ]

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
    evaluation_type = models.CharField(max_length=15, choices=EVALUATION_TYPE_CHOICES)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField()
    evaluation_date = models.DateTimeField(auto_now_add=True)
    is_anonymous = models.BooleanField(default=False)
    evaluator_name = models.CharField(max_length=200, blank=True, null=True, help_text="For anonymous evaluations")
    evaluator_email = models.EmailField(blank=True, null=True, help_text="For anonymous evaluations")

    class Meta:
        db_table = 'evaluations'
        ordering = ['-evaluation_date']

    def __str__(self):
        evaluator_name = self.evaluator.full_name if self.evaluator else self.evaluator_name or "Anonymous"
        return f"{evaluator_name} - {self.project.title} ({self.rating}/5)"


class EvaluationLink(models.Model):
    LINK_TYPE_CHOICES = [
        ('ATTENDANCE', 'Attendance Link'),
        ('EVALUATION', 'Evaluation Link'),
        ('FEEDBACK', 'Feedback Link'),
    ]

    link_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='evaluation_links'
    )
    link_type = models.CharField(max_length=15, choices=LINK_TYPE_CHOICES)
    unique_token = models.UUIDField(default=uuid.uuid4, unique=True)
    expiration_date = models.DateTimeField()
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='created_links'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)
    max_usage = models.PositiveIntegerField(blank=True, null=True, help_text="Leave blank for unlimited usage")

    class Meta:
        db_table = 'evaluation_links'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_link_type_display()} - {self.project.title}"

    @property
    def is_expired(self):
        return timezone.now() > self.expiration_date

    @property
    def is_usage_exceeded(self):
        if self.max_usage is None:
            return False
        return self.usage_count >= self.max_usage


class ProjectPerformance(models.Model):
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
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    budget_utilization = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    impact_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0
    )
    sustainability_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
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

    def __str__(self):
        return f"{self.project.title} - Performance Metrics"


class Communication(models.Model):
    EMAIL_TYPE_CHOICES = [
        ('NOTIFICATION', 'Notification'),
        ('REMINDER', 'Reminder'),
        ('APPROVAL', 'Approval Notification'),
        ('REJECTION', 'Rejection Notification'),
        ('DEADLINE', 'Deadline Alert'),
        ('WELCOME', 'Welcome Email'),
        ('COMPLETION', 'Completion Notice'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('DELIVERED', 'Delivered'),
    ]

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
    email_type = models.CharField(max_length=15, choices=EMAIL_TYPE_CHOICES)
    subject = models.CharField(max_length=300)
    message = models.TextField()
    sent_date = models.DateTimeField(auto_now_add=True)
    is_automated = models.BooleanField(default=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'communications'
        ordering = ['-sent_date']

    def __str__(self):
        return f"{self.subject} -> {self.recipient_email} ({self.get_status_display()})"






