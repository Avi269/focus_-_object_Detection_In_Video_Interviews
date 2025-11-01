from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ('candidate', 'Candidate'),
        ('interviewer', 'Interviewer'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='candidate')
    
    # Profile fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True, help_text="Short biography")
    
    # Account status fields - FIX: Use default instead of auto_now_add for existing migration
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)  # Changed from auto_now_add
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(default=timezone.now)
    
    # Metadata
    total_interviews = models.IntegerField(default=0)
    average_integrity_score = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def get_full_name(self):
        """Override to handle empty names"""
        full_name = super().get_full_name()
        return full_name if full_name.strip() else self.username
    
    def update_interview_stats(self):
        """Update user's interview statistics"""
        if self.role == 'candidate':
            from reports.models import Report
            reports = Report.objects.filter(interview__candidate=self)
            self.total_interviews = reports.count()
            if self.total_interviews > 0:
                self.average_integrity_score = reports.aggregate(
                    models.Avg('integrity_score')
                )['integrity_score__avg'] or 0.0
        elif self.role == 'interviewer':
            self.total_interviews = self.interviewer_interviews.count()
        
        self.save(update_fields=['total_interviews', 'average_integrity_score'])
