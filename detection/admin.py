from django.contrib import admin
from .models import EventLog


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ('interview', 'event_type', 'timestamp', 'confidence_score', 'description')
    list_filter = ('event_type', 'timestamp', 'confidence_score')
    search_fields = ('interview__candidate__username', 'interview__interviewer__username', 'description')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Event Details', {
            'fields': ('interview', 'event_type', 'description', 'confidence_score')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('timestamp',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('interview__candidate', 'interview__interviewer')
