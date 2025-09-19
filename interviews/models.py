# interviews/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Interview(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),  # Add this for better management
    ]
    
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidate_interviews')
    interviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interviewer_interviews')
    
    title = models.CharField(max_length=200, default='Interview Session')
    description = models.TextField(blank=True, null=True)
    
    # FIX: Don't use timezone.now as default for scheduled_time
    scheduled_time = models.DateTimeField()  # Remove default
    duration = models.PositiveIntegerField(help_text="Duration in minutes", null=True, blank=True)
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.candidate.username}"
    
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
    
    def save(self, *args, **kwargs):
        """Override save to add validation"""
        if self.status == 'completed' and not self.end_time:
            self.end_time = timezone.now()
        super().save(*args, **kwargs)

class VideoRecording(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='recordings')
    video_file = models.FileField(upload_to='recordings/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Recording for {self.interview} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
