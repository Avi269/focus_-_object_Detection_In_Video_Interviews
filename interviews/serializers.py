from rest_framework import serializers
from django.utils import timezone
from .models import Interview, VideoRecording


class VideoRecordingSerializer(serializers.ModelSerializer):
    """Serializer for video recordings"""
    file_size = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoRecording
        fields = ['id', 'video_file', 'file_url', 'file_size', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_file_size(self, obj):
        """Get file size in MB"""
        try:
            size_mb = obj.video_file.size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except:
            return "Unknown"
    
    def get_file_url(self, obj):
        """Get full URL for video file"""
        request = self.context.get('request')
        if request and obj.video_file:
            return request.build_absolute_uri(obj.video_file.url)
        return None


class InterviewListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for interview lists"""
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    candidate_username = serializers.CharField(source='candidate.username', read_only=True)
    interviewer_name = serializers.CharField(source='interviewer.get_full_name', read_only=True)
    interviewer_username = serializers.CharField(source='interviewer.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_upcoming = serializers.SerializerMethodField()
    
    class Meta:
        model = Interview
        fields = ['id', 'title', 'candidate', 'candidate_name', 'candidate_username',
                  'interviewer', 'interviewer_name', 'interviewer_username', 
                  'scheduled_time', 'status', 'status_display', 'duration',
                  'is_upcoming', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_is_upcoming(self, obj):
        """Check if interview is upcoming"""
        if obj.status == 'scheduled':
            return obj.scheduled_time > timezone.now()
        return False


class InterviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single interview view"""
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    candidate_username = serializers.CharField(source='candidate.username', read_only=True)
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    
    interviewer_name = serializers.CharField(source='interviewer.get_full_name', read_only=True)
    interviewer_username = serializers.CharField(source='interviewer.username', read_only=True)
    interviewer_email = serializers.EmailField(source='interviewer.email', read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recordings = VideoRecordingSerializer(many=True, read_only=True)
    
    # Computed fields
    actual_duration = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    can_start = serializers.SerializerMethodField()
    can_end = serializers.SerializerMethodField()
    
    # Event statistics
    total_events = serializers.SerializerMethodField()
    violation_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Interview
        fields = [
            'id', 'title', 'description',
            'candidate', 'candidate_name', 'candidate_username', 'candidate_email',
            'interviewer', 'interviewer_name', 'interviewer_username', 'interviewer_email',
            'scheduled_time', 'start_time', 'end_time', 'duration', 'actual_duration',
            'status', 'status_display', 'is_active', 'can_start', 'can_end',
            'total_events', 'violation_count',
            'recordings', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'start_time', 'end_time']
    
    def get_actual_duration(self, obj):
        """Calculate actual interview duration"""
        if obj.start_time and obj.end_time:
            delta = obj.end_time - obj.start_time
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minutes"
        return None
    
    def get_is_active(self, obj):
        """Check if interview is currently active"""
        return obj.status == 'ongoing'
    
    def get_can_start(self, obj):
        """Check if interview can be started"""
        return obj.status == 'scheduled'
    
    def get_can_end(self, obj):
        """Check if interview can be ended"""
        return obj.status == 'ongoing'
    
    def get_total_events(self, obj):
        """Get total number of events logged"""
        return obj.event_logs.count()
    
    def get_violation_count(self, obj):
        """Get count of serious violations"""
        serious_violations = ['multiple_faces', 'phone_detected', 'notes_detected', 
                             'device_detected']
        return obj.event_logs.filter(event_type__in=serious_violations).count()


class InterviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new interviews"""
    
    class Meta:
        model = Interview
        fields = ['title', 'description', 'candidate', 'interviewer', 
                  'scheduled_time', 'duration']
    
    def validate_scheduled_time(self, value):
        """Ensure scheduled time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Scheduled time must be in the future."
            )
        return value
    
    def validate_duration(self, value):
        """Validate duration is reasonable"""
        if value and (value < 5 or value > 480):  # 5 min to 8 hours
            raise serializers.ValidationError(
                "Duration must be between 5 and 480 minutes."
            )
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Ensure candidate and interviewer are different
        if attrs['candidate'] == attrs['interviewer']:
            raise serializers.ValidationError(
                "Candidate and interviewer must be different users."
            )
        
        # Ensure candidate has candidate role
        if attrs['candidate'].role != 'candidate':
            raise serializers.ValidationError({
                "candidate": "Selected user must have 'candidate' role."
            })
        
        # Ensure interviewer has appropriate role
        if attrs['interviewer'].role not in ['interviewer', 'admin']:
            raise serializers.ValidationError({
                "interviewer": "Selected user must have 'interviewer' or 'admin' role."
            })
        
        return attrs


class InterviewUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating interviews"""
    
    class Meta:
        model = Interview
        fields = ['title', 'description', 'scheduled_time', 'duration', 'status']
    
    def validate_status(self, value):
        """Validate status transitions"""
        instance = self.instance
        
        # Define valid transitions
        valid_transitions = {
            'scheduled': ['ongoing', 'cancelled'],
            'ongoing': ['completed', 'cancelled'],
            'completed': [],  # Cannot change from completed
            'cancelled': [],  # Cannot change from cancelled
        }
        
        if instance and instance.status in valid_transitions:
            if value not in valid_transitions[instance.status] and value != instance.status:
                raise serializers.ValidationError(
                    f"Cannot change status from '{instance.status}' to '{value}'."
                )
        
        return value
