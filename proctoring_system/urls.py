"""
URL configuration for proctoring_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponseRedirect


def dashboard_redirect(request):
    """Redirect users to appropriate dashboard based on their role"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'role'):
            if request.user.role == 'candidate':
                return HttpResponseRedirect('/interviews/dashboard/')
            elif request.user.role == 'interviewer':
                return HttpResponseRedirect('/interviews/')
            elif request.user.role == 'admin':
                return HttpResponseRedirect('/admin/')
        return HttpResponseRedirect('/interviews/')
    return HttpResponseRedirect('/accounts/login/')


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Homepage redirect
    path('', dashboard_redirect, name='home'),
    
    # App URLs
    path('accounts/', include('accounts.urls')),
    path('interviews/', include('interviews.urls')),
    path('detection/', include('detection.urls')),
    path('reports/', include('reports.urls')),
    
    # API endpoints (if you plan to add them)
    path('api/v1/', include([
        path('interviews/', include('interviews.urls', namespace='api-interviews')),
        path('detection/', include('detection.urls', namespace='api-detection')),
    ])),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers (optional but recommended)
handler404 = 'accounts.views.custom_404'
handler500 = 'accounts.views.custom_500'
handler403 = 'accounts.views.custom_403'
