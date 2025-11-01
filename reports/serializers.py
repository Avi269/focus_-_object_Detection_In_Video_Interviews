from rest_framework import serializers
from .models import Report
from interviews.serializers import InterviewListSerializer


class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for report lists"""
    interview_title = serializers.CharField(source='interview.title', read_only=True)
    interview_status = serializers.CharField(source='interview.get_status_display', read_only=True)
    integrity_grade = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = ['id', 'interview', 'interview_title', 'interview_status',
                  'candidate_name', 'integrity_score', 'integrity_grade',
                  'suspicious_events', 'generated_at']
        read_only_fields = ['id', 'generated_at']
    
    def get_integrity_grade(self, obj):
        """Convert integrity score to letter grade"""
        score = obj.integrity_score
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'


class ReportDetailSerializer(serializers.ModelSerializer):
    """Detailed report serializer with all metrics"""
    interview_details = InterviewListSerializer(source='interview', read_only=True)
    integrity_grade = serializers.SerializerMethodField()
    total_violations = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()
    assessment = serializers.SerializerMethodField()
    
    # Breakdown by severity
    high_severity_events = serializers.SerializerMethodField()
    medium_severity_events = serializers.SerializerMethodField()
    low_severity_events = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'interview', 'interview_details', 'candidate_name',
            'integrity_score', 'integrity_grade', 'assessment',
            'total_violations', 'suspicious_events',
            
            # Time metrics
            'total_duration', 'duration_formatted', 'generated_at',
            
            # Quality scores
            'face_detection_accuracy', 'audio_quality_score',
            
            # Event breakdown
            'focus_lost_events', 'no_face_events', 'multiple_faces_events',
            'phone_detected_events', 'notes_detected_events', 'device_detected_events',
            'drowsiness_events', 'audio_anomaly_events',
            
            # Severity breakdown
            'high_severity_events', 'medium_severity_events', 'low_severity_events'
        ]
        read_only_fields = ['id', 'generated_at']
    
    def get_integrity_grade(self, obj):
        """Convert integrity score to letter grade"""
        score = obj.integrity_score
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def get_total_violations(self, obj):
        """Calculate total violations"""
        return (
            obj.focus_lost_events + obj.no_face_events + obj.multiple_faces_events +
            obj.phone_detected_events + obj.notes_detected_events + 
            obj.device_detected_events + obj.drowsiness_events + obj.audio_anomaly_events
        )
    
    def get_duration_formatted(self, obj):
        """Format duration as human-readable string"""
        if obj.total_duration:
            total_seconds = int(obj.total_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "N/A"
    
    def get_assessment(self, obj):
        """Provide overall assessment based on integrity score"""
        score = obj.integrity_score
        if score >= 90:
            return "Excellent - No major concerns"
        elif score >= 80:
            return "Good - Minor violations detected"
        elif score >= 70:
            return "Fair - Some concerns present"
        elif score >= 60:
            return "Poor - Multiple violations detected"
        else:
            return "Critical - Serious integrity issues"
    
    def get_high_severity_events(self, obj):
        """Count high severity events"""
        return (
            obj.multiple_faces_events + obj.phone_detected_events + 
            obj.notes_detected_events + obj.device_detected_events
        )
    
    def get_medium_severity_events(self, obj):
        """Count medium severity events"""
        return obj.focus_lost_events + obj.no_face_events + obj.drowsiness_events
    
    def get_low_severity_events(self, obj):
        """Count low severity events"""
        return obj.audio_anomaly_events


class ReportSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for dashboard/analytics"""
    integrity_grade = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = ['id', 'candidate_name', 'integrity_score', 'integrity_grade',
                  'suspicious_events', 'generated_at']
        read_only_fields = ['id', 'generated_at']
    
    def get_integrity_grade(self, obj):
        """Convert integrity score to letter grade"""
        score = obj.integrity_score
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
