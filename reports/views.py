from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import Report
from .serializers import ReportListSerializer, ReportDetailSerializer  # FIX: Updated import
from .utils import generate_pdf, generate_csv
from interviews.models import Interview
from detection.models import EventLog
import logging

logger = logging.getLogger(__name__)


@login_required
def report_list(request):
    """Display list of all reports with filtering"""
    reports = Report.objects.select_related('interview__candidate', 'interview__interviewer').all()
    
    # Apply filters
    candidate_name = request.GET.get('candidate_name', '')
    min_score = request.GET.get('min_integrity_score', '')
    max_score = request.GET.get('max_integrity_score', '')
    
    if candidate_name:
        reports = reports.filter(candidate_name__icontains=candidate_name)
    
    if min_score:
        try:
            reports = reports.filter(integrity_score__gte=int(min_score))
        except ValueError:
            pass
    
    if max_score:
        try:
            reports = reports.filter(integrity_score__lte=int(max_score))
        except ValueError:
            pass
    
    context = {
        'reports': reports,
        'candidate_name': candidate_name,
        'min_score': min_score,
        'max_score': max_score,
    }
    
    return render(request, 'reports/report_list.html', context)


@login_required
def report_detail(request, report_id):
    """Display detailed report view"""
    report = get_object_or_404(
        Report.objects.select_related('interview__candidate', 'interview__interviewer'),
        id=report_id
    )
    
    # Get event breakdown
    events = report.interview.event_logs.all()
    event_timeline = events.order_by('timestamp')[:50]  # Last 50 events
    
    context = {
        'report': report,
        'event_timeline': event_timeline,
        'total_events': events.count(),
    }
    
    return render(request, 'reports/report_detail.html', context)


@login_required
def generate_report(request, interview_id):
    """Generate or regenerate report for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check if interview is completed
    if interview.status != 'completed':
        messages.error(request, 'Cannot generate report for incomplete interview.')
        return redirect('interviews:interview_detail', interview_id=interview_id)
    
    # Check if report already exists
    try:
        report = interview.report
        messages.info(request, 'Report already exists. Regenerating with updated data...')
    except Report.DoesNotExist:
        report = Report(interview=interview)
    
    # Calculate metrics
    report.candidate_name = interview.candidate.get_full_name() or interview.candidate.username
    
    # Calculate duration
    if interview.start_time and interview.end_time:
        report.total_duration = interview.end_time - interview.start_time
    
    # Get event counts
    events = interview.event_logs.all()
    report.focus_lost_events = events.filter(event_type='focus_lost').count()
    report.no_face_events = events.filter(event_type='no_face').count()
    report.multiple_faces_events = events.filter(event_type='multiple_faces').count()
    report.phone_detected_events = events.filter(event_type='phone_detected').count()
    report.notes_detected_events = events.filter(event_type='notes_detected').count()
    report.device_detected_events = events.filter(event_type='device_detected').count()
    report.drowsiness_events = events.filter(event_type='drowsiness').count()
    report.audio_anomaly_events = events.filter(event_type='audio_anomaly').count()
    
    # Calculate legacy fields
    report.focus_loss_count = report.focus_lost_events
    report.suspicious_events = (
        report.phone_detected_events + report.notes_detected_events + 
        report.device_detected_events + report.multiple_faces_events
    )
    
    # Calculate quality scores (placeholder - replace with actual calculations)
    total_events = events.count()
    if total_events > 0:
        face_events = report.no_face_events + report.multiple_faces_events
        report.face_detection_accuracy = max(0.0, 1.0 - (face_events / max(total_events, 1)))
        report.audio_quality_score = max(0.0, 1.0 - (report.audio_anomaly_events / max(total_events, 1)))
    else:
        report.face_detection_accuracy = 1.0
        report.audio_quality_score = 1.0
    
    # Calculate integrity score
    report.calculate_integrity_score()
    
    # Generate recommendations
    report.generate_recommendations()
    
    # Save report
    report.save()
    
    messages.success(request, f'Report generated successfully with integrity score: {report.integrity_score}')
    return redirect('reports:report_detail', report_id=report.id)


@login_required
def export_pdf(request, report_id):
    """Export report as PDF"""
    report = get_object_or_404(Report, id=report_id)
    
    try:
        pdf_data = generate_pdf(report)
        
        # Update export tracking
        report.pdf_generated = True
        report.last_exported_at = timezone.now()
        report.save(update_fields=['pdf_generated', 'last_exported_at'])
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{report.id}_{report.candidate_name}.pdf"'
        
        logger.info(f"PDF exported for report {report.id}")
        return response
        
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}", exc_info=True)
        messages.error(request, 'Failed to generate PDF. Please try again.')
        return redirect('reports:report_detail', report_id=report_id)


@login_required
def export_csv(request, report_id):
    """Export report as CSV"""
    report = get_object_or_404(Report, id=report_id)
    
    try:
        csv_data = generate_csv(report)
        
        # Update export tracking
        report.csv_generated = True
        report.last_exported_at = timezone.now()
        report.save(update_fields=['csv_generated', 'last_exported_at'])
        
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="report_{report.id}_{report.candidate_name}.csv"'
        
        logger.info(f"CSV exported for report {report.id}")
        return response
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}", exc_info=True)
        messages.error(request, 'Failed to generate CSV. Please try again.')
        return redirect('reports:report_detail', report_id=report_id)


# API Views
@login_required
def report_api(request, report_id):
    """API endpoint for single report"""
    report = get_object_or_404(Report, id=report_id)
    serializer = ReportDetailSerializer(report, context={'request': request})
    return JsonResponse(serializer.data)


@login_required
def reports_api(request):
    """API endpoint for report list"""
    reports = Report.objects.select_related('interview__candidate', 'interview__interviewer').all()
    
    # Apply filters
    candidate_name = request.GET.get('candidate_name', '')
    min_score = request.GET.get('min_score', '')
    
    if candidate_name:
        reports = reports.filter(candidate_name__icontains=candidate_name)
    
    if min_score:
        try:
            reports = reports.filter(integrity_score__gte=int(min_score))
        except ValueError:
            pass
    
    serializer = ReportListSerializer(reports, many=True, context={'request': request})
    return JsonResponse({'results': serializer.data})
