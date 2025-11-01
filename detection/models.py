from django.db import models
from django.conf import settings
from django.utils import timezone


class EventLog(models.Model):
    EVENT_TYPE_CHOICES = [
        ('focus_lost', 'Focus Lost'),
        ('no_face', 'No Face Detected'),
        ('multiple_faces', 'Multiple Faces Detected'),
        ('phone_detected', 'Phone Detected'),
        ('notes_detected', 'Notes Detected'),
        ('device_detected', 'Device Detected'),
        ('drowsiness', 'Drowsiness Detected'),
        ('audio_anomaly', 'Audio Anomaly'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    interview = models.ForeignKey(
        'interviews.Interview', 
        on_delete=models.CASCADE, 
        related_name='event_logs'
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)  # Changed from auto_now_add
    description = models.TextField(blank=True)
    confidence_score = models.FloatField(
        default=0.0, 
        help_text="Confidence score for the detection (0-1)"
    )
    
    # Auto-calculated severity
    severity = models.CharField(
        max_length=10, 
        choices=SEVERITY_CHOICES, 
        default='medium'
    )
    
    # Additional context
    frame_number = models.IntegerField(null=True, blank=True)
    screenshot = models.ImageField(
        upload_to='event_screenshots/%Y/%m/%d/', 
        blank=True, 
        null=True
    )
    
    # Review status
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_events'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    
    # False positive flag
    is_false_positive = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['interview', 'event_type']),
            models.Index(fields=['event_type', 'severity']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def save(self, *args, **kwargs):
        """Auto-set severity based on event type"""
        if not self.severity or self.severity == 'medium':
            severity_map = {
                'phone_detected': 'high',
                'notes_detected': 'high',
                'multiple_faces': 'high',
                'device_detected': 'high',
                'focus_lost': 'medium',
                'no_face': 'medium',
                'drowsiness': 'medium',
                'audio_anomaly': 'low',
            }
            self.severity = severity_map.get(self.event_type, 'medium')
        
        super().save(*args, **kwargs)


class DetectionSession(models.Model):
    """Track detection sessions"""
    interview = models.ForeignKey(
        'interviews.Interview',
        on_delete=models.CASCADE,
        related_name='detection_sessions'
    )
    
    started_at = models.DateTimeField(default=timezone.now)  # Changed
    ended_at = models.DateTimeField(null=True, blank=True)
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Session metadata
    total_frames_processed = models.IntegerField(default=0)
    total_events_logged = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Detection Session for {self.interview} - {self.started_at}"
