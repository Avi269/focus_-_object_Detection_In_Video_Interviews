from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import EventLog, DetectionSession


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = (
        'interview_link',
        'event_type_badge',
        'severity_badge',
        'timestamp',
        'confidence_display',
        'reviewed_badge',
        'false_positive_badge'
    )
    list_filter = (
        'event_type',
        'severity',
        'reviewed',
        'is_false_positive',
        'timestamp'
    )
    search_fields = (
        'interview__title',
        'interview__candidate__username', 
        'interview__interviewer__username', 
        'description'
    )
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    # Custom actions
    actions = ['mark_reviewed', 'mark_false_positive', 'mark_legitimate']
    
    fieldsets = (
        ('Event Details', {
            'fields': ('interview', 'event_type', 'severity', 'description', 'confidence_score')
        }),
        ('Context', {
            'fields': ('frame_number', 'screenshot'),
            'classes': ('collapse',)
        }),
        ('Review', {
            'fields': ('reviewed', 'reviewed_by', 'reviewed_at', 'review_notes', 'is_false_positive')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('timestamp', 'severity', 'reviewed_at')
    
    autocomplete_fields = ['interview', 'reviewed_by']
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'interview__candidate', 
            'interview__interviewer',
            'reviewed_by'
        )
    
    @admin.display(description='Interview')
    def interview_link(self, obj):
        """Clickable link to interview"""
        url = reverse('admin:interviews_interview_change', args=[obj.interview.id])
        return format_html('<a href="{}">{}</a>', url, obj.interview.title)
    
    @admin.display(description='Event Type', ordering='event_type')
    def event_type_badge(self, obj):
        """Display event type with icon"""
        icons = {
            'focus_lost': '👀',
            'no_face': '❌',
            'multiple_faces': '👥',
            'phone_detected': '📱',
            'notes_detected': '📝',
            'device_detected': '💻',
            'drowsiness': '😴',
            'audio_anomaly': '🔊'
        }
        icon = icons.get(obj.event_type, '⚠️')
        return format_html('{} {}', icon, obj.get_event_type_display())
    
    @admin.display(description='Severity', ordering='severity')
    def severity_badge(self, obj):
        """Display severity with color badge"""
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#dc3545'
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_severity_display().upper()
        )
    
    @admin.display(description='Confidence')
    def confidence_display(self, obj):
        """Display confidence score with visual indicator"""
        percentage = obj.confidence_score * 100
        
        if percentage >= 80:
            color = '#28a745'
        elif percentage >= 50:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            percentage
        )
    
    @admin.display(boolean=True, description='Reviewed')
    def reviewed_badge(self, obj):
        """Display reviewed status"""
        return obj.reviewed
    
    @admin.display(boolean=True, description='False Positive')
    def false_positive_badge(self, obj):
        """Display false positive flag"""
        return obj.is_false_positive
    
    # Custom actions
    @admin.action(description='Mark as reviewed')
    def mark_reviewed(self, request, queryset):
        """Mark selected events as reviewed"""
        from django.utils import timezone
        updated = queryset.update(
            reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} event(s) marked as reviewed.')
    
    @admin.action(description='Mark as false positive')
    def mark_false_positive(self, request, queryset):
        """Mark selected events as false positives"""
        from django.utils import timezone
        updated = queryset.update(
            is_false_positive=True,
            reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} event(s) marked as false positive.')
    
    @admin.action(description='Mark as legitimate')
    def mark_legitimate(self, request, queryset):
        """Mark selected events as legitimate (not false positive)"""
        from django.utils import timezone
        updated = queryset.update(
            is_false_positive=False,
            reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} event(s) marked as legitimate.')


@admin.register(DetectionSession)
class DetectionSessionAdmin(admin.ModelAdmin):
    list_display = (
        'interview_link',
        'started_at',
        'duration_display',
        'status_badge',
        'frames_processed',
        'events_logged'
    )
    list_filter = ('status', 'started_at')
    search_fields = ('interview__title', 'interview__candidate__username')
    ordering = ('-started_at',)
    date_hierarchy = 'started_at'
    
    fieldsets = (
        ('Session Info', {
            'fields': ('interview', 'status', 'started_at', 'ended_at')
        }),
        ('Statistics', {
            'fields': ('total_frames_processed', 'total_events_logged')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('started_at',)
    
    autocomplete_fields = ['interview']
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('interview__candidate', 'interview__interviewer')
    
    @admin.display(description='Interview')
    def interview_link(self, obj):
        """Clickable link to interview"""
        url = reverse('admin:interviews_interview_change', args=[obj.interview.id])
        return format_html('<a href="{}">{}</a>', url, obj.interview.title)
    
    @admin.display(description='Duration')
    def duration_display(self, obj):
        """Display session duration"""
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return "Ongoing" if obj.status == 'active' else "-"
    
    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        """Display status with badge"""
        colors = {
            'active': '#17a2b8',
            'stopped': '#6c757d',
            'error': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    @admin.display(description='Frames', ordering='total_frames_processed')
    def frames_processed(self, obj):
        """Display frames processed"""
        return f"{obj.total_frames_processed:,}"
    
    @admin.display(description='Events', ordering='total_events_logged')
    def events_logged(self, obj):
        """Display events logged"""
        return f"{obj.total_events_logged:,}"
