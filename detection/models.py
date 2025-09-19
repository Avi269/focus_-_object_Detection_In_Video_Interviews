from django.db import models
from django.conf import settings


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
    
    interview = models.ForeignKey('interviews.Interview', on_delete=models.CASCADE, related_name='event_logs')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0.0, help_text="Confidence score for the detection (0-1)")
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
