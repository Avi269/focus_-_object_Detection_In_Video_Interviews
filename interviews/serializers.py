from rest_framework import serializers
from .models import Interview, VideoRecording


class VideoRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoRecording
        fields = ['id', 'video_file', 'uploaded_at']


class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.username', read_only=True)
    interviewer_name = serializers.CharField(source='interviewer.username', read_only=True)
    recordings = VideoRecordingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Interview
        fields = ['id', 'candidate', 'candidate_name', 'interviewer', 'interviewer_name', 
                 'start_time', 'end_time', 'status', 'created_at', 'duration', 'recordings']
        read_only_fields = ['id', 'created_at', 'duration']
