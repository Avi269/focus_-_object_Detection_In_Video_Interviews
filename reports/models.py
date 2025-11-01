from django.db import models
from django.conf import settings
from django.utils import timezone


class Report(models.Model):
    interview = models.OneToOneField(
        'interviews.Interview', 
        on_delete=models.CASCADE, 
        related_name='report'
    )
    candidate_name = models.CharField(max_length=100)
    focus_loss_count = models.IntegerField(default=0)
    suspicious_events = models.IntegerField(default=0)
    integrity_score = models.IntegerField(
        default=100, 
        help_text="Integrity score out of 100"
    )
    generated_at = models.DateTimeField(default=timezone.now)  # Changed from auto_now_add
    
    # Additional metrics
    total_duration = models.DurationField(null=True, blank=True)
    face_detection_accuracy = models.FloatField(
        default=0.0, 
        help_text="Face detection accuracy (0-1)"
    )
    audio_quality_score = models.FloatField(
        default=0.0, 
        help_text="Audio quality score (0-1)"
    )
    
    # Detailed breakdown
    focus_lost_events = models.IntegerField(default=0)
    no_face_events = models.IntegerField(default=0)
    multiple_faces_events = models.IntegerField(default=0)
    phone_detected_events = models.IntegerField(default=0)
    notes_detected_events = models.IntegerField(default=0)
    device_detected_events = models.IntegerField(default=0)
    drowsiness_events = models.IntegerField(default=0)
    audio_anomaly_events = models.IntegerField(default=0)
    
    # Report status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('final', 'Final'),
        ('disputed', 'Disputed'),
    ]
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='final'
    )
    
    # Review tracking
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Recommendations
    recommendations = models.TextField(blank=True, null=True)
    overall_assessment = models.TextField(blank=True, null=True)
    
    # Export tracking
    pdf_generated = models.BooleanField(default=False)
    csv_generated = models.BooleanField(default=False)
    last_exported_at = models.DateTimeField(null=True, blank=True)
    
    # Version control
    version = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['integrity_score']),
            models.Index(fields=['generated_at']),
            models.Index(fields=['candidate_name']),
        ]
    
    def __str__(self):
        return f"Report for {self.candidate_name} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
    
    def calculate_integrity_score(self):
        """Calculate integrity score"""
        base_score = 100
        deductions = 0
        
        deductions += self.focus_lost_events * 2
        deductions += self.suspicious_events * 5
        deductions += self.no_face_events * 3
        deductions += self.multiple_faces_events * 8
        deductions += self.phone_detected_events * 10
        deductions += self.notes_detected_events * 8
        deductions += self.device_detected_events * 6
        deductions += self.drowsiness_events * 3
        deductions += self.audio_anomaly_events * 4
        
        self.integrity_score = max(0, base_score - deductions)
        return self.integrity_score
    
    def generate_recommendations(self):
        """Auto-generate recommendations"""
        recommendations = []
        
        if self.high_severity_count > 0:
            recommendations.append("Critical integrity issues detected.")
        
        if not recommendations:
            recommendations.append("Excellent performance. No significant issues detected.")
        
        self.recommendations = "\n".join(f"• {rec}" for rec in recommendations)
        return self.recommendations
    
    @property
    def high_severity_count(self):
        return (self.multiple_faces_events + self.phone_detected_events + 
                self.notes_detected_events + self.device_detected_events)
    
    def save(self, *args, **kwargs):
        if not self.recommendations:
            self.generate_recommendations()
        super().save(*args, **kwargs)
