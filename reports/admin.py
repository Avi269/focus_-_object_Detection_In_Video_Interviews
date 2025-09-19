from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'interview', 'integrity_score', 'focus_loss_count', 'suspicious_events', 'generated_at')
    list_filter = ('integrity_score', 'generated_at', 'focus_loss_count', 'suspicious_events')
    search_fields = ('candidate_name', 'interview__candidate__username', 'interview__interviewer__username')
    ordering = ('-generated_at',)
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('Report Overview', {
            'fields': ('interview', 'candidate_name', 'integrity_score', 'generated_at')
        }),
        ('Event Counts', {
            'fields': ('focus_loss_count', 'suspicious_events', 'focus_lost_events', 'no_face_events', 'multiple_faces_events')
        }),
        ('Additional Events', {
            'fields': ('phone_detected_events', 'notes_detected_events', 'device_detected_events', 'drowsiness_events', 'audio_anomaly_events'),
            'classes': ('collapse',)
        }),
        ('Metrics', {
            'fields': ('total_duration', 'face_detection_accuracy', 'audio_quality_score'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('generated_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('interview__candidate', 'interview__interviewer')
