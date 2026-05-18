from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import EventLog, DetectionSession
from interviews.models import Interview
from .detection_engine import (
    get_detection_summary, 
    log_event, 
    start_detection, 
    stop_detection, 
    is_detection_active,
    get_active_detection_count,
    active_detection_threads,
    cleanup_inactive_threads
)
import csv
import json


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def serialize_event_log(event):
    """Simple serializer for EventLog objects"""
    return {
        'id': event.id,
        'event_type': event.event_type,
        'event_type_display': event.get_event_type_display(),
        'timestamp': event.timestamp.isoformat(),
        'description': event.description,
        'confidence_score': event.confidence_score,
        'severity': event.severity,
        'severity_display': event.get_severity_display(),
        'interview_id': event.interview.id if event.interview else None,
        'reviewed': event.reviewed,
    }


# ============================================================================
# DETECTION CONTROL VIEWS
# ============================================================================

@login_required
@csrf_exempt
def run_detection(request, interview_id):
    """Start detection for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions: allow admins, interviewers, and the interview's candidate
    if not (
        request.user.role in ['admin', 'interviewer'] or
        interview.interviewer == request.user or
        interview.candidate == request.user
    ):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    # Check if interview is in correct state
    if interview.status != 'ongoing':
        return JsonResponse({
            'status': 'error', 
            'message': 'Interview must be ongoing to start detection'
        }, status=400)
    
    try:
        duration = interview.duration if interview.duration else 30
        start_detection(interview, duration)
        
        messages.success(request, '✅ Detection started successfully!')
        
        return JsonResponse({
            'status': 'success',
            'message': 'Detection started successfully',
            'interview_id': interview_id,
            'detection_active': True
        })
    except Exception as e:
        messages.error(request, f'❌ Failed to start detection: {str(e)}')
        return JsonResponse({
            'status': 'error', 
            'message': f'Failed to start detection: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def stop_detection_view(request, interview_id):
    """Stop detection for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions  
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    try:
        stop_detection(interview.id)
        messages.success(request, '✅ Detection stopped successfully!')
        
        return JsonResponse({
            'status': 'success',
            'message': 'Detection stopped successfully',
            'interview_id': interview_id,
            'detection_active': False
        })
    except Exception as e:
        messages.error(request, f'❌ Failed to stop detection: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to stop detection: {str(e)}'
        }, status=500)


@login_required
def restart_detection(request, interview_id):
    """Restart detection for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Stop existing detection
        stop_detection(interview.id)
        
        # Wait a moment for cleanup
        import time
        time.sleep(1)
        
        # Start new detection
        duration = interview.duration if interview.duration else 30
        start_detection(interview, duration_minutes=duration)
        
        messages.success(request, '✅ Detection restarted successfully!')
        
        return JsonResponse({
            'success': True, 
            'message': 'Detection restarted successfully',
            'detection_active': True
        })
    except Exception as e:
        messages.error(request, f'❌ Failed to restart detection: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# STATUS & MONITORING VIEWS
# ============================================================================

@login_required
def detection_status(request, interview_id):
    """API endpoint to check detection status"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)
        
        is_active = is_detection_active(interview_id)
        summary = get_detection_summary(interview) if is_active else {}
        
        return JsonResponse({
            'active': is_active,
            'summary': summary,
            'interview_id': interview_id
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'active': False
        }, status=500)


@login_required
def system_status(request):
    """System status and diagnostics"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        active_count = get_active_detection_count()
        total_threads = len(active_detection_threads)
        
        # Get some system stats
        ongoing_interviews = Interview.objects.filter(status='ongoing').count()
        total_events_today = EventLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).count()
        
        return JsonResponse({
            'active_threads': active_count,
            'total_threads': total_threads,
            'ongoing_interviews': ongoing_interviews,
            'events_today': total_events_today,
            'system_status': 'operational' if active_count <= ongoing_interviews else 'warning'
        })
    except Exception as e:
        return JsonResponse({
            'error': f'Status check failed: {str(e)}',
            'system_status': 'error'
        }, status=500)


@login_required
def cleanup_threads(request):
    """Clean up inactive detection threads"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        cleaned_count = cleanup_inactive_threads()
        messages.success(request, f'✅ Cleaned up {cleaned_count} inactive threads')
        
        return JsonResponse({
            'success': True, 
            'cleaned_threads': cleaned_count,
            'remaining_threads': len(active_detection_threads)
        })
    except Exception as e:
        messages.error(request, f'❌ Cleanup failed: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# DASHBOARD & LIST VIEWS
# ============================================================================

@login_required
def detection_dashboard(request):
    """Dashboard showing detection status and statistics"""
    try:
        # Get all detection sessions
        sessions = DetectionSession.objects.select_related(
            'interview__candidate',
            'interview__interviewer'
        ).order_by('-started_at')[:10]
        
        # Get active detection count
        active_count = get_active_detection_count()
        
        # Get recent events
        recent_events = EventLog.objects.select_related(
            'interview__candidate',
            'interview__interviewer'
        ).order_by('-timestamp')[:20]
        
        # Statistics
        total_events = EventLog.objects.count()
        high_severity_count = EventLog.objects.filter(severity='high').count()
        
        context = {
            'sessions': sessions,
            'active_count': active_count,
            'recent_events': recent_events,
            'total_events': total_events,
            'high_severity_count': high_severity_count,
        }
        
        return render(request, 'detection/dashboard.html', context)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in detection dashboard: {e}", exc_info=True)
        
        # Return minimal context on error
        return render(request, 'detection/dashboard.html', {
            'sessions': [],
            'active_count': 0,
            'recent_events': [],
            'total_events': 0,
            'high_severity_count': 0,
            'error': str(e)
        })


@login_required
def event_list(request):
    """List all detection events with filtering"""
    try:
        events = EventLog.objects.select_related(
            'interview__candidate',
            'interview__interviewer'
        ).order_by('-timestamp')
        
        # Apply filters
        event_type = request.GET.get('event_type')
        severity = request.GET.get('severity')
        interview_id = request.GET.get('interview')
        
        if event_type:
            events = events.filter(event_type=event_type)
        
        if severity:
            events = events.filter(severity=severity)
        
        if interview_id:
            events = events.filter(interview_id=interview_id)
        
        # Pagination
        paginator = Paginator(events, 50)  # Show 50 events per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get filter choices
        event_types = EventLog.EVENT_TYPE_CHOICES
        severities = EventLog.SEVERITY_CHOICES
        
        context = {
            'page_obj': page_obj,
            'events': page_obj.object_list,
            'event_types': event_types,
            'severities': severities,
            'selected_event_type': event_type,
            'selected_severity': severity,
        }
        
        return render(request, 'detection/event_list.html', context)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in event list: {e}", exc_info=True)
        
        return render(request, 'detection/event_list.html', {
            'events': [],
            'event_types': [],
            'severities': [],
            'error': str(e)
        })


@login_required
def event_detail(request, event_id):
    """View detailed information about a detection event"""
    event = get_object_or_404(EventLog, id=event_id)
    
    # Check permissions
    if (request.user.role == 'candidate' and event.interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and event.interview.interviewer != request.user):
        if not request.user.is_staff:
            messages.error(request, '❌ Unauthorized access')
            return redirect('detection:event_list')
    
    context = {
        'event': event,
        'interview': event.interview
    }
    
    return render(request, 'detection/event_detail.html', context)


# ============================================================================
# EVENT API VIEWS (JSON Responses)
# ============================================================================

@login_required
def get_events(request, interview_id):
    """API endpoint to get all events for an interview (JSON response)"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if (request.user.role == 'candidate' and interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and interview.interviewer != request.user):
        if not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get events with pagination
    events = EventLog.objects.filter(interview=interview).order_by('-timestamp')
    
    # Apply filters if provided
    event_type = request.GET.get('event_type')
    if event_type:
        events = events.filter(event_type=event_type)
    
    # Serialize events
    events_data = [serialize_event_log(event) for event in events[:100]]  # Limit to 100
    
    return JsonResponse({
        'interview_id': interview_id,
        'total_events': EventLog.objects.filter(interview=interview).count(),
        'events': events_data,
        'detection_active': is_detection_active(interview_id)
    })


@login_required
@require_http_methods(["POST"])
def log_event_api(request):
    """API endpoint to log a new event"""
    try:
        # Parse JSON body
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        event_type = data.get('event_type')
        description = data.get('description', '')
        confidence_score = data.get('confidence_score', 0.0)
        
        if not all([interview_id, event_type]):
            return JsonResponse({
                'status': 'error', 
                'message': 'Missing required fields: interview_id, event_type'
            }, status=400)
        
        interview = Interview.objects.get(id=interview_id)
        
        # Check permissions
        if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
        # Validate confidence score
        try:
            confidence_score = float(confidence_score)
            if not 0 <= confidence_score <= 1:
                confidence_score = confidence_score / 100  # Convert percentage if needed
        except (ValueError, TypeError):
            confidence_score = 0.0
        
        success = log_event(interview, event_type, description, confidence_score)
        
        if success:
            return JsonResponse({
                'status': 'success', 
                'message': 'Event logged successfully',
                'event_type': event_type,
                'confidence_score': confidence_score
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Failed to log event'}, status=500)
            
    except Interview.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Interview not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ============================================================================
# EXPORT & DATA VIEWS
# ============================================================================

@login_required
def export_events(request, interview_id):
    """Export detection events to CSV"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        messages.error(request, '❌ Unauthorized')
        return redirect('detection:event_list')
    
    try:
        events = EventLog.objects.filter(interview=interview).order_by('-timestamp')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="interview_{interview_id}_events.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Event Type', 'Severity', 'Description', 'Confidence Score'])
        
        for event in events:
            writer.writerow([
                event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                event.get_event_type_display(),
                event.get_severity_display(),
                event.description,
                f"{event.confidence_score:.2f}"
            ])
        
        messages.success(request, '✅ Events exported successfully!')
        return response
        
    except Exception as e:
        messages.error(request, f'❌ Export failed: {str(e)}')
        return redirect('detection:event_list')


# ============================================================================
# ADMIN VIEWS
# ============================================================================

@login_required
def delete_event(request, event_id):
    """Delete a detection event"""
    if not request.user.is_staff:
        messages.error(request, '❌ Unauthorized')
        return redirect('detection:event_list')
    
    event = get_object_or_404(EventLog, id=event_id)
    
    if request.method == 'POST':
        try:
            event.delete()
            messages.success(request, '✅ Event deleted successfully!')
        except Exception as e:
            messages.error(request, f'❌ Failed to delete event: {str(e)}')
        
        return redirect('detection:event_list')
    
    context = {'event': event}
    return render(request, 'detection/confirm_delete_event.html', context)


@login_required
def detection_settings(request):
    """Detection system settings"""
    if not request.user.is_staff:
        messages.error(request, '❌ Unauthorized')
        return redirect('detection:detection_dashboard')
    
    if request.method == 'POST':
        # Handle settings form submission
        messages.info(request, 'ℹ️ Settings functionality coming soon!')
    
    context = {
        'active_detections': get_active_detection_count(),
        'total_events': EventLog.objects.count(),
        'ongoing_interviews': Interview.objects.filter(status='ongoing').count()
    }
    
    return render(request, 'detection/settings.html', context)


# ============================================================================
# ADDITIONAL VIEWS
# ============================================================================

@login_required
def detection_summary(request, interview_id):
    """Get detection summary for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if (request.user.role == 'candidate' and interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and interview.interviewer != request.user):
        if not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        summary = get_detection_summary(interview)
        
        return JsonResponse({
            'interview_id': interview_id,
            'summary': summary,
            'detection_active': is_detection_active(interview_id)
        })
    except Exception as e:
        return JsonResponse({
            'error': f'Failed to get summary: {str(e)}'
        }, status=500)


@login_required
def manual_event_log(request):
    """Manual event logging form (for testing/admin use)"""
    if not request.user.is_staff:
        messages.error(request, '❌ Unauthorized - Admin access required')
        return redirect('detection:general_dashboard')
    
    if request.method == 'POST':
        try:
            interview_id = request.POST.get('interview_id')
            event_type = request.POST.get('event_type')
            description = request.POST.get('description', '')
            confidence_score = float(request.POST.get('confidence_score', 0.5))
            
            interview = Interview.objects.get(id=interview_id)
            
            success = log_event(interview, event_type, description, confidence_score)
            
            if success:
                messages.success(request, f'✅ Event logged: {event_type}')
            else:
                messages.error(request, '❌ Failed to log event')
                
        except Interview.DoesNotExist:
            messages.error(request, '❌ Interview not found')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
        
        return redirect('detection:general_dashboard')
    
    # GET request - show form
    ongoing_interviews = Interview.objects.filter(status='ongoing')
    event_types = EventLog.EVENT_TYPE_CHOICES
    
    context = {
        'ongoing_interviews': ongoing_interviews,
        'event_types': event_types
    }
    
    return render(request, 'detection/manual_event_log.html', context)


# ============================================================================
# ADMIN VIEWS (keep existing code below)
# ============================================================================
