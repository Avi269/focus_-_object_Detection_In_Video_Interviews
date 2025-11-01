from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import Interview, VideoRecording


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'candidate_link',
        'interviewer_link',
        'scheduled_time',
        'status_badge',
        'duration_display',
        'event_count',
        'has_report',
        'created_at'
    )
    list_filter = (
        'status', 
        'is_remote',
        'scheduled_time', 
        'created_at',
        'reschedule_count'
    )
    search_fields = (
        'title',
        'candidate__username', 
        'interviewer__username', 
        'candidate__first_name', 
        'candidate__last_name',
        'interviewer__first_name',
        'interviewer__last_name',
        'description'
    )
    ordering = ('-scheduled_time',)
    date_hierarchy = 'scheduled_time'
    
    # Custom actions
    actions = ['mark_completed', 'mark_cancelled', 'generate_reports']
    
    fieldsets = (
        ('Interview Details', {
            'fields': ('title', 'description', 'candidate', 'interviewer', 'created_by')
        }),
        ('Scheduling', {
            'fields': ('scheduled_time', 'duration', 'is_remote', 'location', 'meeting_link')
        }),
        ('Status & Timing', {
            'fields': ('status', 'start_time', 'end_time')
        }),
        ('Cancellation Details', {
            'fields': ('cancelled_at', 'cancelled_by', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Rescheduling', {
            'fields': ('rescheduled_from', 'reschedule_count'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'cancelled_at')
    
    autocomplete_fields = ['candidate', 'interviewer', 'created_by', 'cancelled_by', 'rescheduled_from']
    
    def get_queryset(self, request):
        """Optimize queries with prefetch"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'candidate', 
            'interviewer', 
            'created_by',
            'cancelled_by'
        ).prefetch_related('event_logs', 'recordings').annotate(
            _event_count=Count('event_logs')
        )
    
    @admin.display(description='Candidate')
    def candidate_link(self, obj):
        """Clickable link to candidate"""
        url = reverse('admin:accounts_user_change', args=[obj.candidate.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.candidate.get_full_name() or obj.candidate.username
        )
    
    @admin.display(description='Interviewer')
    def interviewer_link(self, obj):
        """Clickable link to interviewer"""
        url = reverse('admin:accounts_user_change', args=[obj.interviewer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.interviewer.get_full_name() or obj.interviewer.username
        )
    
    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'scheduled': '#ffc107',
            'ongoing': '#17a2b8',
            'completed': '#28a745',
            'cancelled': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        icon = {
            'scheduled': '📅',
            'ongoing': '▶️',
            'completed': '✅',
            'cancelled': '❌'
        }.get(obj.status, '⚪')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display()
        )
    
    @admin.display(description='Duration')
    def duration_display(self, obj):
        """Display duration"""
        return obj.get_duration_display
    
    @admin.display(description='Events', ordering='_event_count')
    def event_count(self, obj):
        """Display event count with severity indicator"""
        count = obj._event_count if hasattr(obj, '_event_count') else obj.event_logs.count()
        
        if count == 0:
            color = '#28a745'
        elif count < 5:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            count
        )
    
    @admin.display(boolean=True, description='Report')
    def has_report(self, obj):
        """Check if report exists"""
        return hasattr(obj, 'report')
    
    # Custom actions
    @admin.action(description='Mark as completed')
    def mark_completed(self, request, queryset):
        """Mark selected interviews as completed"""
        from django.utils import timezone
        updated = 0
        for interview in queryset.filter(status='ongoing'):
            interview.status = 'completed'
            if not interview.end_time:
                interview.end_time = timezone.now()
            interview.save()
            updated += 1
        self.message_user(request, f'{updated} interview(s) marked as completed.')
    
    @admin.action(description='Mark as cancelled')
    def mark_cancelled(self, request, queryset):
        """Mark selected interviews as cancelled"""
        from django.utils import timezone
        updated = 0
        for interview in queryset.filter(status__in=['scheduled', 'ongoing']):
            interview.status = 'cancelled'
            if not interview.cancelled_at:
                interview.cancelled_at = timezone.now()
                interview.cancelled_by = request.user
            interview.save()
            updated += 1
        self.message_user(request, f'{updated} interview(s) marked as cancelled.')
    
    @admin.action(description='Generate reports')
    def generate_reports(self, request, queryset):
        """Generate reports for completed interviews"""
        from reports.models import Report
        generated = 0
        
        for interview in queryset.filter(status='completed'):
            if hasattr(interview, 'report'):
                continue  # Skip if report exists
            
            report = Report(interview=interview)
            report.candidate_name = interview.candidate.get_full_name()
            
            # Calculate metrics
            events = interview.event_logs.all()
            report.focus_lost_events = events.filter(event_type='focus_lost').count()
            report.no_face_events = events.filter(event_type='no_face').count()
            report.multiple_faces_events = events.filter(event_type='multiple_faces').count()
            report.phone_detected_events = events.filter(event_type='phone_detected').count()
            report.notes_detected_events = events.filter(event_type='notes_detected').count()
            report.device_detected_events = events.filter(event_type='device_detected').count()
            report.drowsiness_events = events.filter(event_type='drowsiness').count()
            report.audio_anomaly_events = events.filter(event_type='audio_anomaly').count()
            
            report.calculate_integrity_score()
            report.save()
            generated += 1
        
        self.message_user(request, f'{generated} report(s) generated successfully.')


@admin.register(VideoRecording)
class VideoRecordingAdmin(admin.ModelAdmin):
    list_display = (
        'interview_link',
        'uploaded_at',
        'file_size_display',
        'processing_status_badge',
        'analyzed_badge',
        'uploaded_by_link'
    )
    list_filter = (
        'processing_status',
        'analyzed',
        'uploaded_at'
    )
    search_fields = (
        'interview__title',
        'interview__candidate__username', 
        'interview__interviewer__username'
    )
    ordering = ('-uploaded_at',)
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        ('Recording Details', {
            'fields': ('interview', 'video_file', 'uploaded_by')
        }),
        ('File Information', {
            'fields': ('file_size', 'duration')
        }),
        ('Processing', {
            'fields': ('processing_status', 'processing_error', 'analyzed', 'analysis_completed_at')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('uploaded_at', 'file_size')
    
    autocomplete_fields = ['interview', 'uploaded_by']
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('interview__candidate', 'interview__interviewer', 'uploaded_by')
    
    @admin.display(description='Interview')
    def interview_link(self, obj):
        """Clickable link to interview"""
        url = reverse('admin:interviews_interview_change', args=[obj.interview.id])
        return format_html('<a href="{}">{}</a>', url, obj.interview.title)
    
    @admin.display(description='File Size')
    def file_size_display(self, obj):
        """Display file size"""
        return obj.file_size_display
    
    @admin.display(description='Status', ordering='processing_status')
    def processing_status_badge(self, obj):
        """Display processing status with badge"""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545'
        }
        color = colors.get(obj.processing_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_processing_status_display()
        )
    
    @admin.display(boolean=True, description='Analyzed')
    def analyzed_badge(self, obj):
        """Display analyzed status"""
        return obj.analyzed
    
    @admin.display(description='Uploaded By')
    def uploaded_by_link(self, obj):
        """Link to user who uploaded"""
        if obj.uploaded_by:
            url = reverse('admin:accounts_user_change', args=[obj.uploaded_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.uploaded_by.username)
        return '-'
