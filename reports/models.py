from django.db import models
from django.conf import settings


class Report(models.Model):
    interview = models.OneToOneField('interviews.Interview', on_delete=models.CASCADE, related_name='report')
    candidate_name = models.CharField(max_length=100)
    focus_loss_count = models.IntegerField(default=0)
    suspicious_events = models.IntegerField(default=0)
    integrity_score = models.IntegerField(default=100, help_text="Integrity score out of 100")
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Additional metrics
    total_duration = models.DurationField(null=True, blank=True)
    face_detection_accuracy = models.FloatField(default=0.0, help_text="Face detection accuracy (0-1)")
    audio_quality_score = models.FloatField(default=0.0, help_text="Audio quality score (0-1)")
    
    # Detailed breakdown
    focus_lost_events = models.IntegerField(default=0)
    no_face_events = models.IntegerField(default=0)
    multiple_faces_events = models.IntegerField(default=0)
    phone_detected_events = models.IntegerField(default=0)
    notes_detected_events = models.IntegerField(default=0)
    device_detected_events = models.IntegerField(default=0)
    drowsiness_events = models.IntegerField(default=0)
    audio_anomaly_events = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Report for {self.candidate_name} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
    
    def calculate_integrity_score(self):
        """
        Calculate integrity score based on violations
        Formula: Final Integrity Score = 100 - deductions
        """
        base_score = 100
        
        # Deduction system based on violation severity
        deductions = 0
        
        # Focus loss deductions (2 points per occurrence)
        deductions += self.focus_lost_events * 2
        
        # Suspicious event deductions (5 points per occurrence)
        deductions += self.suspicious_events * 5
        
        # Additional specific deductions
        deductions += self.no_face_events * 3  # No face detection
        deductions += self.multiple_faces_events * 8  # Multiple faces (more severe)
        deductions += self.phone_detected_events * 10  # Phone detection (most severe)
        deductions += self.notes_detected_events * 8   # Notes detection
        deductions += self.device_detected_events * 6  # Device detection
        deductions += self.drowsiness_events * 3       # Drowsiness
        deductions += self.audio_anomaly_events * 4    # Audio anomalies
        
        self.integrity_score = max(0, base_score - deductions)
        return self.integrity_score
