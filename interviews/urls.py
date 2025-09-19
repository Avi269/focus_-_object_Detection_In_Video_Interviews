from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    # Main interview management URLs
    path('', views.interview_list, name='interview_list'),
    path('schedule/', views.schedule_interview, name='schedule_interview'),
    
    # Interview detail and actions
    path('<int:interview_id>/', views.interview_detail, name='interview_detail'),
    path('<int:interview_id>/start/', views.start_interview, name='start_interview'),
    path('<int:interview_id>/end/', views.end_interview, name='end_interview'),
    
    # Recording management
    path('<int:interview_id>/upload/', views.upload_recording, name='upload_recording'),
    
    # Detection integration
    path('<int:interview_id>/detection-status/', views.detection_status, name='detection_status'),
    path('<int:interview_id>/stop-detection/', views.stop_detection_view, name='stop_detection'),
    
    # Emergency controls
    path('emergency-stop/', views.emergency_stop_all, name='emergency_stop'),
    
    # Candidate-specific URLs
    path('dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    path('<int:interview_id>/join/', views.join_interview, name='join'),
    path('<int:interview_id>/live/', views.live_interview, name='live'),
    
    # Additional management URLs
    path('<int:interview_id>/edit/', views.edit_interview, name='edit_interview'),
    path('<int:interview_id>/delete/', views.delete_interview, name='delete_interview'),
    path('<int:interview_id>/reschedule/', views.reschedule_interview, name='reschedule_interview'),
    
    # Reporting URLs
    path('reports/', views.interview_reports, name='reports'),
    path('<int:interview_id>/report/', views.interview_report, name='interview_report'),
]
