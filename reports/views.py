from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Report
from .forms import ReportForm
from .serializers import ReportSerializer
from .utils import generate_pdf, generate_csv
from interviews.models import Interview
from detection.models import EventLog
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@login_required
def generate_report(request, interview_id):
    """Generate a report for a completed interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    if interview.status != 'completed':
        messages.error(request, 'Can only generate reports for completed interviews.')
        return redirect('interviews:interview_detail', interview_id=interview.id)
    
    # Check if report already exists
    if hasattr(interview, 'report'):
        messages.info(request, 'Report already exists for this interview.')
        return redirect('reports:report_detail', report_id=interview.report.id)
    
    # Get event logs for this interview
    events = EventLog.objects.filter(interview=interview)
    
    # Calculate metrics
    focus_lost_events = events.filter(event_type='focus_lost').count()
    suspicious_events = events.filter(
        event_type__in=['phone_detected', 'notes_detected', 'device_detected', 'multiple_faces']
    ).count()
    
    # Create report
    report = Report.objects.create(
        interview=interview,
        candidate_name=interview.candidate.get_full_name() or interview.candidate.username,
        focus_loss_count=focus_lost_events,
        suspicious_events=suspicious_events,
        total_duration=interview.duration,
        focus_lost_events=events.filter(event_type='focus_lost').count(),
        no_face_events=events.filter(event_type='no_face').count(),
        multiple_faces_events=events.filter(event_type='multiple_faces').count(),
        phone_detected_events=events.filter(event_type='phone_detected').count(),
        notes_detected_events=events.filter(event_type='notes_detected').count(),
        device_detected_events=events.filter(event_type='device_detected').count(),
        drowsiness_events=events.filter(event_type='drowsiness').count(),
        audio_anomaly_events=events.filter(event_type='audio_anomaly').count(),
    )
    
    # Calculate integrity score
    report.calculate_integrity_score()
    report.save()
    
    messages.success(request, 'Report generated successfully!')
    return redirect('reports:report_detail', report_id=report.id)


@login_required
def report_detail(request, report_id):
    """View detailed report"""
    report = get_object_or_404(Report, id=report_id)
    
    # Check permissions
    if request.user.role == 'candidate' and report.interview.candidate != request.user:
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('reports:report_list')
    elif request.user.role == 'interviewer' and report.interview.interviewer != request.user:
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('reports:report_list')
    
    return render(request, 'reports/report_detail.html', {'report': report})


@login_required
def report_list(request):
    """List all reports"""
    reports = Report.objects.all().order_by('-generated_at')
    
    # Filter based on user role
    if request.user.role == 'candidate':
        reports = reports.filter(interview__candidate=request.user)
    elif request.user.role == 'interviewer':
        reports = reports.filter(interview__interviewer=request.user)
    
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'reports/report_list.html', {'page_obj': page_obj})


@login_required
def export_pdf(request, report_id):
    """Export report as PDF"""
    report = get_object_or_404(Report, id=report_id)
    
    # Check permissions
    if request.user.role == 'candidate' and report.interview.candidate != request.user:
        messages.error(request, 'You do not have permission to export this report.')
        return redirect('reports:report_list')
    elif request.user.role == 'interviewer' and report.interview.interviewer != request.user:
        messages.error(request, 'You do not have permission to export this report.')
        return redirect('reports:report_list')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{report.id}.pdf"'
    
    pdf_content = generate_pdf(report)
    response.write(pdf_content)
    
    return response


@login_required
def export_csv(request, report_id):
    """Export report as CSV"""
    report = get_object_or_404(Report, id=report_id)
    
    # Check permissions
    if request.user.role == 'candidate' and report.interview.candidate != request.user:
        messages.error(request, 'You do not have permission to export this report.')
        return redirect('reports:report_list')
    elif request.user.role == 'interviewer' and report.interview.interviewer != request.user:
        messages.error(request, 'You do not have permission to export this report.')
        return redirect('reports:report_list')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="report_{report.id}.csv"'
    
    csv_content = generate_csv(report)
    response.write(csv_content.decode('utf-8'))
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_api(request, report_id):
    """API endpoint to get report data"""
    report = get_object_or_404(Report, id=report_id)
    
    # Check permissions
    if request.user.role == 'candidate' and report.interview.candidate != request.user:
        return Response({'error': 'Permission denied'}, status=403)
    elif request.user.role == 'interviewer' and report.interview.interviewer != request.user:
        return Response({'error': 'Permission denied'}, status=403)
    
    serializer = ReportSerializer(report)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_api(request):
    """API endpoint to get all reports for the user"""
    reports = Report.objects.all().order_by('-generated_at')
    
    # Filter based on user role
    if request.user.role == 'candidate':
        reports = reports.filter(interview__candidate=request.user)
    elif request.user.role == 'interviewer':
        reports = reports.filter(interview__interviewer=request.user)
    
    serializer = ReportSerializer(reports, many=True)
    return Response(serializer.data)
