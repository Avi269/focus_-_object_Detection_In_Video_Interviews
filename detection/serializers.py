from rest_framework import serializers
from .models import EventLog


class EventLogSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = EventLog
        fields = ['id', 'interview', 'event_type', 'event_type_display', 'timestamp', 
                 'description', 'confidence_score']
        read_only_fields = ['id', 'timestamp']
