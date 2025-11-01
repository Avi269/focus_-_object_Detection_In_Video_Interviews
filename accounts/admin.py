from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 
        'email', 
        'full_name_display',
        'role_badge', 
        'total_interviews',
        'average_integrity_score',
        'is_active_badge',
        'email_verified_badge',
        'date_joined'
    )
    list_filter = (
        'role', 
        'is_staff', 
        'is_superuser', 
        'is_active', 
        'email_verified',
        'date_joined',
        'last_activity'
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'
    
    # Custom actions
    actions = ['activate_users', 'deactivate_users', 'verify_emails', 'update_stats']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Permissions', {
            'fields': ('role',)
        }),
        ('Profile Information', {
            'fields': ('phone_number', 'profile_picture', 'bio'),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': ('email_verified', 'last_activity'),
        }),
        ('Statistics', {
            'fields': ('total_interviews', 'average_integrity_score'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Additional Info', {
            'fields': ('role', 'email', 'first_name', 'last_name')
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'last_activity', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.annotate(
            _interview_count=Count('candidate_interviews'),
            _avg_score=Avg('candidate_interviews__report__integrity_score')
        )
    
    @admin.display(description='Full Name')
    def full_name_display(self, obj):
        """Display full name or username"""
        return obj.get_full_name() or obj.username
    
    @admin.display(description='Role', ordering='role')
    def role_badge(self, obj):
        """Display role with color badge"""
        colors = {
            'candidate': '#17a2b8',
            'interviewer': '#28a745',
            'admin': '#dc3545'
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_role_display()
        )
    
    @admin.display(boolean=True, description='Active')
    def is_active_badge(self, obj):
        """Display active status"""
        return obj.is_active
    
    @admin.display(boolean=True, description='Email Verified')
    def email_verified_badge(self, obj):
        """Display email verification status"""
        return obj.email_verified
    
    # Custom actions
    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) successfully activated.')
    
    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) successfully deactivated.')
    
    @admin.action(description='Verify email for selected users')
    def verify_emails(self, request, queryset):
        """Verify emails for selected users"""
        updated = queryset.update(email_verified=True)
        self.message_user(request, f'{updated} user(s) email verified.')
    
    @admin.action(description='Update interview statistics')
    def update_stats(self, request, queryset):
        """Update interview statistics for selected users"""
        count = 0
        for user in queryset:
            user.update_interview_stats()
            count += 1
        self.message_user(request, f'Statistics updated for {count} user(s).')
