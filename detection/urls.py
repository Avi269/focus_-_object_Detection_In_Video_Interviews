from django.urls import path
from . import views

app_name = 'detection'

urlpatterns = [
    # General detection dashboard
    path('', views.detection_dashboard, name='general_dashboard'),
    
    # Interview-specific detection control
    path('<int:interview_id>/', views.detection_dashboard, name='dashboard'),
    path('<int:interview_id>/start/', views.run_detection, name='start'),
    path('<int:interview_id>/stop/', views.stop_detection_view, name='stop'),
    path('<int:interview_id>/status/', views.detection_status, name='status'),  # Changed from detection_status_api
    path('<int:interview_id>/restart/', views.restart_detection, name='restart'),
    
    # Event management
    path('<int:interview_id>/events/', views.get_events, name='events'),
    path('<int:interview_id>/events/export/', views.export_events, name='export_events'),
    path('<int:interview_id>/summary/', views.detection_summary, name='summary'),  # This function is missing too
    
    # Event logging
    path('log-event/', views.log_event_api, name='log_event'),
    path('manual-log/', views.manual_event_log, name='manual_log'),  # This function is missing
    
    # General event management
    path('events/', views.event_list, name='event_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    
    # System management
    path('system/status/', views.system_status, name='system_status'),
    path('system/cleanup/', views.cleanup_threads, name='cleanup_threads'),
    path('system/settings/', views.detection_settings, name='settings'),
]
