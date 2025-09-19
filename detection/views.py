from datetime import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # 🔧 FIXED: Correct import
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import EventLog
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
from interviews.models import Interview
import csv
import json

# 🔧 Create a simple serializer since EventLogSerializer might not exist
def serialize_event_log(event):
    """Simple serializer for EventLog objects"""
    return {
        'id': event.id,
        'event_type': event.event_type,
        'timestamp': event.timestamp.isoformat(),
        'description': event.description,
        'confidence_score': event.confidence_score,
        'interview_id': event.interview.id if event.interview else None,
    }

@login_required
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_events(request, interview_id):
    """API endpoint to get all events for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if (request.user.role == 'candidate' and interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and interview.interviewer != request.user):
        if not request.user.is_staff:
            return Response({'error': 'Unauthorized'}, status=403)
    
    # Get events with pagination
    events = EventLog.objects.filter(interview=interview).order_by('-timestamp')
    
    # Apply filters if provided
    event_type = request.GET.get('event_type')
    if event_type:
        events = events.filter(event_type=event_type)
    
    # Serialize events
    events_data = [serialize_event_log(event) for event in events[:100]]  # Limit to 100
    
    return Response({
        'interview_id': interview_id,
        'total_events': EventLog.objects.filter(interview=interview).count(),
        'events': events_data,
        'detection_active': is_detection_active(interview_id)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_event_api(request):
    """API endpoint to log a new event"""
    interview_id = request.data.get('interview_id')
    event_type = request.data.get('event_type')
    description = request.data.get('description', '')
    confidence_score = request.data.get('confidence_score', 0.0)
    
    if not all([interview_id, event_type]):
        return Response({
            'status': 'error', 
            'message': 'Missing required fields: interview_id, event_type'
        }, status=400)
    
    try:
        interview = Interview.objects.get(id=interview_id)
        
        # Check permissions
        if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
            return Response({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
        # Validate confidence score
        try:
            confidence_score = float(confidence_score)
            if not 0 <= confidence_score <= 1:
                confidence_score = confidence_score / 100  # Convert percentage if needed
        except (ValueError, TypeError):
            confidence_score = 0.0
        
        success = log_event(interview, event_type, description, confidence_score)
        
        if success:
            return Response({
                'status': 'success', 
                'message': 'Event logged successfully',
                'event_type': event_type,
                'confidence_score': confidence_score
            })
        else:
            return Response({'status': 'error', 'message': 'Failed to log event'}, status=500)
            
    except Interview.DoesNotExist:
        return Response({'status': 'error', 'message': 'Interview not found'}, status=404)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)

@login_required
def detection_dashboard(request, interview_id=None):
    """Dashboard showing detection status and events"""
    context = {}
    
    if interview_id:
        # Interview-specific dashboard
        interview = get_object_or_404(Interview, id=interview_id)
        
        # Check permissions
        if (request.user.role == 'candidate' and interview.candidate != request.user) or \
           (request.user.role == 'interviewer' and interview.interviewer != request.user):
            if not request.user.is_staff:
                messages.error(request, '❌ Unauthorized access')
                return redirect('interviews:interview_list')
        
        try:
            summary = get_detection_summary(interview)
            recent_events = EventLog.objects.filter(interview=interview).order_by('-timestamp')[:20]
            detection_active = is_detection_active(interview.id)
            
            context = {
                'interview': interview,
                'summary': summary,
                'recent_events': recent_events,
                'detection_active': detection_active,
                'is_interview_specific': True
            }
        except Exception as e:
            messages.error(request, f'❌ Error loading detection data: {str(e)}')
            context = {
                'interview': interview,
                'error': str(e),
                'is_interview_specific': True
            }
    else:
        # General dashboard
        if not request.user.is_staff and request.user.role not in ['admin', 'interviewer']:
            messages.error(request, '❌ Unauthorized access')
            return redirect('interviews:interview_list')
        
        try:
            recent_events = EventLog.objects.order_by('-timestamp')[:20]
            total_events = EventLog.objects.count()
            active_interviews = Interview.objects.filter(status='ongoing').count()
            active_detections = get_active_detection_count()
            
            context = {
                'recent_events': recent_events,
                'total_events': total_events,
                'active_interviews': active_interviews,
                'active_detections': active_detections,
                'is_interview_specific': False
            }
        except Exception as e:
            messages.error(request, f'❌ Error loading dashboard: {str(e)}')
            context = {'error': str(e), 'is_interview_specific': False}
    
    return render(request, 'detection/dashboard.html', context)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detection_summary(request, interview_id):
    """API endpoint to get detection summary"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if (request.user.role == 'candidate' and interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and interview.interviewer != request.user):
        if not request.user.is_staff:
            return Response({'error': 'Unauthorized'}, status=403)
    
    try:
        summary = get_detection_summary(interview)
        summary.update({
            'detection_active': is_detection_active(interview.id),
            'interview_status': interview.status,
            'interview_title': interview.title or 'Interview Session'
        })
        
        return Response(summary)
    except Exception as e:
        return Response({'error': f'Failed to get summary: {str(e)}'}, status=500)

@login_required
def event_list(request):
    """Display list of detection events"""
    if not request.user.is_staff and request.user.role not in ['admin', 'interviewer']:
        messages.error(request, '❌ Unauthorized access')
        return redirect('interviews:interview_list')
    
    events = EventLog.objects.all().order_by('-timestamp')
    
    # Apply filters
    interview_id = request.GET.get('interview_id')
    event_type = request.GET.get('event_type')
    search = request.GET.get('search')
    
    if interview_id:
        events = events.filter(interview_id=interview_id)
    
    if event_type:
        events = events.filter(event_type=event_type)
    
    if search:
        events = events.filter(
            Q(description__icontains=search) | 
            Q(event_type__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(events, 50)  # Show 50 events per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available event types for filter
    event_types = EventLog.objects.values_list('event_type', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'events': page_obj,  # For backward compatibility
        'interview_id': interview_id,
        'event_type': event_type,
        'search': search,
        'event_types': event_types,
        'total_events': events.count()
    }
    
    return render(request, 'detection/event_list.html', context)

@require_http_methods(["GET", "POST"])
@login_required
def manual_event_log(request):
    """Manually log a detection event (for testing)"""
    if request.method == 'GET':
        # Show form
        interviews = Interview.objects.filter(status__in=['ongoing', 'scheduled'])
        context = {
            'interviews': interviews,
            'event_types': [choice[0] for choice in EventLog.EVENT_TYPE_CHOICES]
        }
        return render(request, 'detection/manual_event_log.html', context)
    
    # POST request
    interview_id = request.POST.get('interview_id')
    event_type = request.POST.get('event_type', 'manual_test')
    description = request.POST.get('description', 'Manually logged event')
    
    try:
        confidence = float(request.POST.get('confidence', 0.8))
    except (ValueError, TypeError):
        confidence = 0.8
    
    if not interview_id:
        messages.error(request, '❌ Missing interview ID')
        return redirect('detection:manual_log')
    
    try:
        interview = Interview.objects.get(id=interview_id)
        
        # Check permissions
        if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
            messages.error(request, '❌ Unauthorized')
            return redirect('detection:manual_log')
        
        success = log_event(interview, event_type, description, confidence)
        
        if success:
            messages.success(request, '✅ Event logged successfully!')
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': True, 
                    'message': 'Event logged successfully',
                    'event_type': event_type
                })
        else:
            messages.error(request, '❌ Failed to log event')
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({'success': False, 'error': 'Failed to log event'})
            
    except Interview.DoesNotExist:
        messages.error(request, '❌ Interview not found')
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': False, 'error': 'Interview not found'})
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'success': False, 'error': str(e)})
    
    return redirect('detection:manual_log')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detection_status_api(request, interview_id):
    """API endpoint to check if detection is active"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if (request.user.role == 'candidate' and interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and interview.interviewer != request.user):
        if not request.user.is_staff:
            return Response({'error': 'Unauthorized'}, status=403)
    
    try:
        recent_events = EventLog.objects.filter(interview=interview).order_by('-timestamp')[:5]
        events_data = [serialize_event_log(event) for event in recent_events]
        
        return Response({
            'interview_id': interview_id,
            'detection_active': is_detection_active(interview_id),
            'interview_status': interview.status,
            'total_events': EventLog.objects.filter(interview=interview).count(),
            'recent_events': events_data
        })
    except Exception as e:
        return Response({'error': f'Status check failed: {str(e)}'}, status=500)

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

@login_required
def export_events(request, interview_id):
    """Export detection events to CSV"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        messages.error(request, '❌ Unauthorized')
        return redirect('detection:events', interview_id=interview.id)
    
    try:
        events = EventLog.objects.filter(interview=interview).order_by('-timestamp')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="interview_{interview_id}_events.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Event Type', 'Description', 'Confidence Score'])
        
        for event in events:
            writer.writerow([
                event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                event.get_event_type_display(),
                event.description,
                f"{event.confidence_score:.2f}"
            ])
        
        messages.success(request, '✅ Events exported successfully!')
        return response
        
    except Exception as e:
        messages.error(request, f'❌ Export failed: {str(e)}')
        return redirect('detection:events', interview_id=interview.id)

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

@login_required
def detection_settings(request):
    """Detection system settings"""
    if not request.user.is_staff:
        messages.error(request, '❌ Unauthorized')
        return redirect('detection:general_dashboard')
    
    if request.method == 'POST':
        # Handle settings form submission
        messages.info(request, 'ℹ️ Settings functionality coming soon!')
    
    context = {
        'active_detections': get_active_detection_count(),
        'total_events': EventLog.objects.count(),
        'ongoing_interviews': Interview.objects.filter(status='ongoing').count()
    }
    
    return render(request, 'detection/settings.html', context)
