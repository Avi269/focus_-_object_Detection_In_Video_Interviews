from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'candidate_name',
        'interview_link',
        'integrity_badge',
        'grade_badge',
        'total_violations_display',
        'status_badge',
        'reviewed_badge',
        'generated_at'
    )
    list_filter = (
        'status',
        'reviewed',
        'integrity_score',
        'generated_at',
        'pdf_generated',
        'csv_generated'
    )
    search_fields = (
        'candidate_name', 
        'interview__candidate__username', 
        'interview__interviewer__username',
        'interview__title'
    )
    ordering = ('-generated_at',)
    date_hierarchy = 'generated_at'
    
    # Custom actions
    actions = ['regenerate_reports', 'mark_as_reviewed', 'export_to_pdf', 'export_to_csv']
    
    fieldsets = (
        ('Report Overview', {
            'fields': ('interview', 'candidate_name', 'status', 'integrity_score', 'generated_at', 'version')
        }),
        ('Basic Metrics', {
            'fields': ('focus_loss_count', 'suspicious_events', 'total_duration')
        }),
        ('Detailed Event Breakdown', {
            'fields': (
                'focus_lost_events', 
                'no_face_events', 
                'multiple_faces_events',
                'phone_detected_events',
                'notes_detected_events',
                'device_detected_events',
                'drowsiness_events',
                'audio_anomaly_events'
            ),
            'classes': ('collapse',)
        }),
        ('Quality Metrics', {
            'fields': ('face_detection_accuracy', 'audio_quality_score'),
            'classes': ('collapse',)
        }),
        ('Assessment', {
            'fields': ('overall_assessment', 'recommendations'),
        }),
        ('Review Status', {
            'fields': ('reviewed', 'reviewed_by', 'reviewed_at'),
            'classes': ('collapse',)
        }),
        ('Export Tracking', {
            'fields': ('pdf_generated', 'csv_generated', 'last_exported_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('generated_at', 'reviewed_at', 'last_exported_at', 'updated_at', 'version')
    
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
    
    @admin.display(description='Integrity Score', ordering='integrity_score')
    def integrity_badge(self, obj):
        """Display integrity score with color"""
        score = obj.integrity_score
        
        if score >= 90:
            color = '#28a745'
        elif score >= 80:
            color = '#17a2b8'
        elif score >= 70:
            color = '#ffc107'
        elif score >= 60:
            color = '#fd7e14'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; '
            'border-radius: 3px; font-weight: bold; font-size: 14px;">{}/100</span>',
            color,
            score
        )
    
    @admin.display(description='Grade', ordering='integrity_score')
    def grade_badge(self, obj):
        """Display letter grade"""
        grade = obj.integrity_grade
        
        colors = {
            'A': '#28a745',
            'B': '#17a2b8',
            'C': '#ffc107',
            'D': '#fd7e14',
            'F': '#dc3545'
        }
        color = colors.get(grade, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 15px; '
            'border-radius: 50%; font-weight: bold; font-size: 16px;">{}</span>',
            color,
            grade
        )
    
    @admin.display(description='Violations')
    def total_violations_display(self, obj):
        """Display total violations with breakdown"""
        total = obj.total_violations
        high = obj.high_severity_count
        
        if high > 0:
            color = '#dc3545'
            icon = '🔴'
        elif total > 5:
            color = '#ffc107'
            icon = '🟡'
        else:
            color = '#28a745'
            icon = '🟢'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} total</span>',
            color,
            icon,
            total
        )
    
    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        """Display report status"""
        colors = {
            'draft': '#6c757d',
            'final': '#28a745',
            'disputed': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    @admin.display(boolean=True, description='Reviewed')
    def reviewed_badge(self, obj):
        """Display reviewed status"""
        return obj.reviewed
    
    # Custom actions
    @admin.action(description='Regenerate selected reports')
    def regenerate_reports(self, request, queryset):
        """Regenerate integrity scores and recommendations"""
        updated = 0
        for report in queryset:
            report.calculate_integrity_score()
            report.generate_recommendations()
            report.version += 1
            report.save()
            updated += 1
        self.message_user(request, f'{updated} report(s) regenerated successfully.')
    
    @admin.action(description='Mark as reviewed')
    def mark_as_reviewed(self, request, queryset):
        """Mark selected reports as reviewed"""
        from django.utils import timezone
        updated = queryset.update(
            reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} report(s) marked as reviewed.')
    
    @admin.action(description='Export to PDF')
    def export_to_pdf(self, request, queryset):
        """Mark reports as exported to PDF"""
        from django.utils import timezone
        updated = queryset.update(
            pdf_generated=True,
            last_exported_at=timezone.now()
        )
        self.message_user(request, f'{updated} report(s) marked as PDF exported.')
    
    @admin.action(description='Export to CSV')
    def export_to_csv(self, request, queryset):
        """Mark reports as exported to CSV"""
        from django.utils import timezone
        updated = queryset.update(
            csv_generated=True,
            last_exported_at=timezone.now()
        )
        self.message_user(request, f'{updated} report(s) marked as CSV exported.')
