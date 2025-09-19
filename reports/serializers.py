from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    interview_details = serializers.CharField(source='interview', read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'interview', 'interview_details', 'candidate_name', 'focus_loss_count', 
                 'suspicious_events', 'integrity_score', 'generated_at', 'total_duration',
                 'face_detection_accuracy', 'audio_quality_score', 'focus_lost_events',
                 'no_face_events', 'multiple_faces_events', 'phone_detected_events',
                 'notes_detected_events', 'device_detected_events', 'drowsiness_events',
                 'audio_anomaly_events']
        read_only_fields = ['id', 'generated_at']
