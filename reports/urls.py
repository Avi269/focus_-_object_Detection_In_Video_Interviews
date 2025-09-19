from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_list, name='report_list'),
    path('generate/<int:interview_id>/', views.generate_report, name='generate_report'),
    path('<int:report_id>/', views.report_detail, name='report_detail'),
    path('<int:report_id>/pdf/', views.export_pdf, name='export_pdf'),
    path('<int:report_id>/csv/', views.export_csv, name='export_csv'),
    path('api/<int:report_id>/', views.report_api, name='report_api'),
    path('api/', views.reports_api, name='reports_api'),
]
