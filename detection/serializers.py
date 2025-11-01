from rest_framework import serializers
from django.utils import timezone
from .models import EventLog


class EventLogSerializer(serializers.ModelSerializer):
    """Basic event log serializer"""
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    interview_title = serializers.CharField(source='interview.title', read_only=True)
    candidate_name = serializers.CharField(source='interview.candidate.get_full_name', read_only=True)
    time_ago = serializers.SerializerMethodField()
    severity = serializers.SerializerMethodField()
    
    class Meta:
        model = EventLog
        fields = ['id', 'interview', 'interview_title', 'candidate_name',
                  'event_type', 'event_type_display', 'timestamp', 'time_ago',
                  'description', 'confidence_score', 'severity']
        read_only_fields = ['id', 'timestamp']
    
    def get_time_ago(self, obj):
        """Get human-readable time difference"""
        now = timezone.now()
        diff = now - obj.timestamp
        
        seconds = int(diff.total_seconds())
        
        if seconds < 60:
            return f"{seconds} seconds ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
    
    def get_severity(self, obj):
        """Determine event severity level"""
        high_severity = ['multiple_faces', 'phone_detected', 'notes_detected', 'device_detected']
        medium_severity = ['focus_lost', 'no_face', 'drowsiness']
        
        if obj.event_type in high_severity:
            return 'high'
        elif obj.event_type in medium_severity:
            return 'medium'
        else:
            return 'low'


class EventLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating event logs"""
    
    class Meta:
        model = EventLog
        fields = ['interview', 'event_type', 'description', 'confidence_score']
    
    def validate_confidence_score(self, value):
        """Ensure confidence score is between 0 and 1"""
        if value < 0 or value > 1:
            raise serializers.ValidationError(
                "Confidence score must be between 0 and 1."
            )
        return value
    
    def validate(self, attrs):
        """Validate interview is ongoing"""
        interview = attrs.get('interview')
        if interview and interview.status != 'ongoing':
            raise serializers.ValidationError({
                "interview": "Can only log events for ongoing interviews."
            })
        return attrs


class EventLogDetailSerializer(EventLogSerializer):
    """Detailed event log with additional interview context"""
    interview_status = serializers.CharField(source='interview.get_status_display', read_only=True)
    interviewer_name = serializers.CharField(source='interview.interviewer.get_full_name', read_only=True)
    
    class Meta(EventLogSerializer.Meta):
        fields = EventLogSerializer.Meta.fields + ['interview_status', 'interviewer_name']


class EventLogStatsSerializer(serializers.Serializer):
    """Serializer for event statistics"""
    total_events = serializers.IntegerField()
    focus_lost_count = serializers.IntegerField()
    no_face_count = serializers.IntegerField()
    multiple_faces_count = serializers.IntegerField()
    phone_detected_count = serializers.IntegerField()
    notes_detected_count = serializers.IntegerField()
    device_detected_count = serializers.IntegerField()
    drowsiness_count = serializers.IntegerField()
    audio_anomaly_count = serializers.IntegerField()
    high_severity_count = serializers.IntegerField()
    medium_severity_count = serializers.IntegerField()
    low_severity_count = serializers.IntegerField()
    average_confidence = serializers.FloatField()
