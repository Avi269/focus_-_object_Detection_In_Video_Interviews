from django.contrib import admin
from .models import Interview, VideoRecording


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'interviewer', 'start_time', 'status', 'duration', 'created_at')
    list_filter = ('status', 'start_time', 'created_at')
    search_fields = ('candidate__username', 'interviewer__username', 'candidate__first_name', 'candidate__last_name')
    ordering = ('-created_at',)
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Interview Details', {
            'fields': ('candidate', 'interviewer', 'start_time', 'end_time', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'duration')


@admin.register(VideoRecording)
class VideoRecordingAdmin(admin.ModelAdmin):
    list_display = ('interview', 'uploaded_at', 'video_file')
    list_filter = ('uploaded_at',)
    search_fields = ('interview__candidate__username', 'interview__interviewer__username')
    ordering = ('-uploaded_at',)
    date_hierarchy = 'uploaded_at'
