# interviews/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class Interview(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='candidate_interviews',
        limit_choices_to={'role': 'candidate', 'is_active': True}
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='interviewer_interviews',
        limit_choices_to={'role__in': ['interviewer', 'admin'], 'is_active': True}
    )
    
    title = models.CharField(max_length=200, default='Interview Session')
    description = models.TextField(blank=True, null=True)
    
    scheduled_time = models.DateTimeField()
    duration = models.PositiveIntegerField(
        help_text="Duration in minutes", 
        null=True, 
        blank=True,
        default=30
    )
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Audit trail - FIX: Use default instead of auto_now_add
    created_at = models.DateTimeField(default=timezone.now)  # Changed
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Allow null for existing records
        related_name='created_interviews'
    )
    
    # Additional fields
    meeting_link = models.URLField(blank=True, null=True, help_text="Video conference link")
    notes = models.TextField(blank=True, null=True, help_text="Interviewer notes")
    is_remote = models.BooleanField(default=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    
    # Cancellation tracking
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_interviews'
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    
    # Rescheduling tracking
    rescheduled_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rescheduled_interviews'
    )
    reschedule_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-scheduled_time']
        indexes = [
            models.Index(fields=['status', 'scheduled_time']),
            models.Index(fields=['candidate', 'status']),
            models.Index(fields=['interviewer', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.candidate.username} ({self.get_status_display()})"
    
    def clean(self):
        """Model-level validation"""
        super().clean()
        
        if self.candidate_id and self.interviewer_id and self.candidate_id == self.interviewer_id:
            raise ValidationError('Candidate and interviewer must be different users.')
        
        if not self.pk and self.scheduled_time and self.scheduled_time <= timezone.now():
            raise ValidationError('Scheduled time must be in the future.')
    
    def save(self, *args, **kwargs):
        """Override save to add auto-calculations"""
        if self.status == 'completed' and not self.end_time:
            self.end_time = timezone.now()
        
        if self.status == 'cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def get_duration_display(self):
        """Get human readable duration"""
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours:
                return f"{int(hours)}h {int(minutes)}m"
            return f"{int(minutes)}m"
        return f"{self.duration}m" if self.duration else "Not specified"
    
    @property
    def actual_duration(self):
        """Get actual duration as timedelta"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_upcoming(self):
        """Check if interview is upcoming"""
        return self.status == 'scheduled' and self.scheduled_time > timezone.now()
    
    @property
    def can_start(self):
        """Check if interview can be started"""
        if self.status != 'scheduled':
            return False
        
        allowed_start_time = self.scheduled_time - timezone.timedelta(minutes=15)
        return timezone.now() >= allowed_start_time


class VideoRecording(models.Model):
    interview = models.ForeignKey(
        Interview, 
        on_delete=models.CASCADE, 
        related_name='recordings'
    )
    video_file = models.FileField(upload_to='recordings/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(default=timezone.now)  # Changed
    
    # Metadata
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    duration = models.DurationField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_recordings'
    )
    
    # Processing status
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    processing_status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUS_CHOICES, 
        default='pending'
    )
    processing_error = models.TextField(blank=True, null=True)
    
    # Analysis results
    analyzed = models.BooleanField(default=False)
    analysis_completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Recording for {self.interview} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate file size"""
        if self.video_file and not self.file_size:
            self.file_size = self.video_file.size
        super().save(*args, **kwargs)
    
    @property
    def file_size_display(self):
        """Get human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
