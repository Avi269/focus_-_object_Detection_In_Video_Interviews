from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Interview, VideoRecording
from .forms import InterviewForm, VideoRecordingForm
from detection.detection_engine import start_detection, stop_detection, is_detection_active, analyze_video_file
from datetime import timedelta
from django.db import transaction


@login_required
def schedule_interview(request):
    if request.method == 'POST':
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save()
            messages.success(request, '✅ Interview scheduled successfully!')
            return redirect('interviews:interview_list')
    else:
        form = InterviewForm()
    
    return render(request, 'interviews/schedule_interview.html', {'form': form})

@login_required
def start_interview(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        messages.error(request, '  You are not authorized to start this interview.')
        return redirect('interviews:interview_list')
    
    if request.method == 'POST':
        # Start the interview with database transaction
        with transaction.atomic():
            interview.status = 'ongoing'
            now = timezone.now()
            if not interview.start_time or (now - interview.start_time).total_seconds() > 300:
                interview.start_time = now
            interview.save()
        
        print(f"✅ Interview {interview.id} status updated to 'ongoing'")
        
        # Start detection with proper thread management
        try:
            detection_duration = interview.duration if interview.duration else 30
            start_detection(interview, detection_duration)
            messages.success(request, '✅ Interview started! Detection is now active.')
        except Exception as e:
            print(f"  Detection start failed: {e}")
            messages.warning(request, f'⚠️ Interview started but detection failed: {str(e)}')
        
        return redirect('interviews:interview_detail', interview_id=interview.id)
    
    return render(request, 'interviews/start_interview.html', {'interview': interview})

@login_required
def end_interview(request, interview_id):
    print(f"📩 Request method: {request.method}")
    print(f"👤 User: {request.user}, Role: {getattr(request.user, 'role', None)}")

    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        messages.error(request, '  You are not authorized to end this interview.')
        return redirect('interviews:interview_list')
    
    if request.method == 'POST':
        print(f"  Ending interview {interview.id}")
        
        # CRITICAL FIX: Stop detection FIRST, then update database
        try:
            # Mark interview as completed early so detection thread sees status change
            interview.status = 'completed'
            interview.end_time = timezone.now()
            interview.save()
            print(f"🔁 Interview {interview.id} marked completed before stopping detection")

            stop_detection(interview.id)
            print(f"✅ stop_detection returned for interview {interview.id}")

            # Double-check and run cleanup fallback if necessary
            from detection.detection_engine import is_detection_active, cleanup_inactive_threads, force_stop_all_detection
            if is_detection_active(interview.id):
                print(f"⚠️ Detection still active for {interview.id} after stop_detection(); attempting cleanup")
                cleaned = cleanup_inactive_threads()
                print(f"🧹 cleanup_inactive_threads removed {cleaned} entries")
                if is_detection_active(interview.id):
                    print(f"🚨 Forcing stop for remaining detection threads for interview {interview.id}")
                    force_stop_all_detection()
            else:
                print(f"🔍 Detection inactive for interview {interview.id}")
        except Exception as e:
            print(f"  Error stopping detection: {e}")
        
        # Ensure interview save already performed; show status
        print(f"✅ Interview {interview.id} status now: {interview.status}")
        interview.refresh_from_db()
        print(f"🔍 Interview {interview.id} status after save: {interview.status}")
        
        messages.success(request, '✅ Interview completed successfully!')
        return redirect('interviews:interview_detail', interview_id=interview.id)
    
    # GET request - show end interview page
    from detection.models import EventLog
    recent_events = EventLog.objects.filter(interview=interview).order_by('-timestamp')[:6]
    total_events = EventLog.objects.filter(interview=interview).count()
    
    # Calculate integrity score
    integrity_score = max(0, 100 - (total_events * 5))
    
    context = {
        'interview': interview,
        'recent_events': recent_events,
        'total_events': total_events,
        'integrity_score': integrity_score,
    }
    
    return render(request, 'interviews/end_interview.html', context)


@login_required
def interview_list(request):
    """List all interviews with filtering and pagination"""
    user = request.user
    
    # Get interviews based on user role
    if user.role == 'candidate':
        interviews = Interview.objects.filter(candidate=user)
    elif user.role == 'interviewer':
        interviews = Interview.objects.filter(interviewer=user)
    elif user.role == 'admin':
        interviews = Interview.objects.all()
    else:
        interviews = Interview.objects.none()
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        interviews = interviews.filter(status=status_filter)
    
    search_query = request.GET.get('search')
    if search_query:
        from django.db.models import Q
        interviews = interviews.filter(
            Q(title__icontains=search_query) |
            Q(candidate__username__icontains=search_query) |
            Q(interviewer__username__icontains=search_query)
        )
    
    # Order by scheduled time
    interviews = interviews.order_by('-scheduled_time')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(interviews, 10)  # Show 10 interviews per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 🔧 Calculate statistics properly
    total_interviews = interviews.count()
    scheduled_count = interviews.filter(status='scheduled').count()
    ongoing_count = interviews.filter(status='ongoing').count()
    completed_count = interviews.filter(status='completed').count()
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'stats': {
            'total': total_interviews,
            'scheduled': scheduled_count,
            'ongoing': ongoing_count,
            'completed': completed_count,
        }
    }
    
    return render(request, 'interviews/interview_list.html', context)


@login_required
def interview_detail(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    recordings = interview.recordings.all()
    
    # Check access permissions
    if (request.user.role == 'candidate' and interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and interview.interviewer != request.user):
        if not request.user.is_staff:
            messages.error(request, '  You do not have permission to view this interview.')
            return redirect('interviews:interview_list')
    
    return render(request, 'interviews/interview_detail.html', {
        'interview': interview,
        'recordings': recordings
    })


@login_required
def upload_recording(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        messages.error(request, '  You are not authorized to upload recordings for this interview.')
        return redirect('interviews:interview_list')
    
    if request.method == 'POST':
        form = VideoRecordingForm(request.POST, request.FILES)
        if form.is_valid():
            recording = form.save(commit=False)
            recording.interview = interview
            recording.save()
            
            # Analyze the video for suspicious activities
            try:
                analyze_video_file(recording.video_file.path, interview)
                messages.success(request, '✅ Video uploaded and analyzed successfully!')
            except Exception as e:
                messages.warning(request, f'⚠️ Video uploaded but analysis failed: {str(e)}')
            
            return redirect('interviews:interview_detail', interview_id=interview.id)
    else:
        form = VideoRecordingForm()
    
    return render(request, 'interviews/upload_recording.html', {
        'form': form,
        'interview': interview
    })


@login_required
def detection_status(request, interview_id):
    """API endpoint to get real-time detection status"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    if (request.user.role == 'candidate' and interview.candidate != request.user) or \
       (request.user.role == 'interviewer' and interview.interviewer != request.user):
        if not request.user.is_staff:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get recent events
    from detection.models import EventLog
    recent_events = EventLog.objects.filter(interview=interview).order_by('-timestamp')[:10]
    
    events_data = []
    for event in recent_events:
        events_data.append({
            'event_type': event.get_event_type_display() if hasattr(event, 'get_event_type_display') else event.event_type,
            'timestamp': event.timestamp.isoformat(),
            'description': event.description or '',
            'confidence_score': getattr(event, 'confidence_score', 0)
        })
    
    return JsonResponse({
        'interview_id': interview.id,
        'status': interview.status,
        'detection_active': is_detection_active(interview.id),
        'recent_events': events_data
    })


@login_required
def join_interview(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check if user is the assigned candidate
    if interview.candidate != request.user:
        messages.error(request, '  You are not authorized to join this interview.')
        return redirect('interviews:interview_list')
    
    # Check if interview is scheduled and ready to start
    if interview.status != 'scheduled':
        if interview.status == 'ongoing':
            return redirect('interviews:live', interview_id=interview.id)
        messages.error(request, '  This interview is not available to join.')
        return redirect('interviews:candidate_dashboard')
    
    # Check if it's time for the interview (within 15 minutes window)
    now = timezone.now()
    interview_time = interview.scheduled_time  # 🔧 FIXED: Use scheduled_time
    window_start = interview_time - timedelta(minutes=15)
    window_end = interview_time + timedelta(minutes=60)  # 1 hour late allowed
    
    if not (window_start <= now <= window_end):
        messages.error(request, f'  Interview is not available at this time. Scheduled for {interview_time.strftime("%B %d, %Y at %I:%M %p")}')
        return redirect('interviews:candidate_dashboard')
    
    return render(request, 'interviews/join_interview.html', {
        'interview': interview
    })


@login_required 
def candidate_dashboard(request):
    """Dashboard specifically for candidates"""
    if request.user.role != 'candidate':
        return redirect('interviews:interview_list')
    
    from detection.models import EventLog
    
    now = timezone.now()
    
    # Get candidate's interviews - 🔧 FIXED: Use scheduled_time
    upcoming_interviews = Interview.objects.filter(
        candidate=request.user,
        status='scheduled',
        scheduled_time__gte=now
    ).order_by('scheduled_time')
    
    ongoing_interviews = Interview.objects.filter(
        candidate=request.user,
        status='ongoing'
    )
    
    completed_interviews = Interview.objects.filter(
        candidate=request.user,
        status='completed'
    ).order_by('-end_time')[:5]
    
    # Get recent events for completed interviews
    recent_events = EventLog.objects.filter(
        interview__candidate=request.user,
        interview__status='completed'
    ).order_by('-timestamp')[:5]
    
    context = {
        'upcoming_interviews': upcoming_interviews,
        'ongoing_interviews': ongoing_interviews,
        'completed_interviews': completed_interviews,
        'recent_events': recent_events,
        'total_interviews': Interview.objects.filter(candidate=request.user).count(),
    }
    
    return render(request, 'interviews/candidate_dashboard.html', context)


@login_required
@ensure_csrf_cookie
def live_interview(request, interview_id):
    """Live interview interface for candidates"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check authorization
    if interview.candidate != request.user:
        messages.error(request, '  Unauthorized access.')
        return redirect('interviews:interview_list')
    
    if interview.status != 'ongoing':
        if interview.status == 'scheduled':
            messages.info(request, 'ℹ️ Interview has not started yet.')
            return redirect('interviews:join', interview_id=interview.id)
        elif interview.status == 'completed':
            messages.info(request, 'ℹ️ This interview has already been completed.')
            return redirect('interviews:interview_detail', interview_id=interview.id)
        else:
            messages.error(request, '  Interview is not currently active.')
            return redirect('interviews:candidate_dashboard')
    
    return render(request, 'interviews/live_interview.html', {
        'interview': interview
    })


@login_required
def stop_detection_view(request, interview_id):
    """Manual endpoint to stop detection"""
    interview = get_object_or_404(Interview, id=interview_id)
    
    # Check permissions
    # Allow admins, interviewers, and the interview's candidate to stop detection
    if not (
        request.user.role in ['admin', 'interviewer'] or
        interview.interviewer == request.user or
        interview.candidate == request.user
    ):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        stop_detection(interview.id)
        return JsonResponse({'success': True, 'message': 'Detection stopped successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# Add emergency stop function
@login_required
def emergency_stop_all(request):
    """Emergency function to stop all detection threads"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        from detection.detection_engine import force_stop_all_detection
        force_stop_all_detection()
        
        # Also end all ongoing interviews
        ongoing = Interview.objects.filter(status='ongoing')
        count = ongoing.count()
        
        for interview in ongoing:
            interview.status = 'completed'
            interview.end_time = timezone.now()
            interview.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Stopped all detection and ended {count} ongoing interviews'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

@login_required
def edit_interview(request, interview_id):
    """Edit interview details"""
    interview = get_object_or_404(Interview, id=interview_id)
    # Check permissions
    if request.user.role not in ['admin', 'interviewer'] and interview.interviewer != request.user:
        messages.error(request, '  You are not authorized to edit this interview.')
        return redirect('interviews:interview_list')
    
    # Placeholder - implement edit functionality
    messages.info(request, 'Edit functionality coming soon!')
    return redirect('interviews:interview_detail', interview_id=interview.id)

@login_required
def delete_interview(request, interview_id):
    """Delete interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    # Check permissions
    if request.user.role not in ['admin'] and interview.interviewer != request.user:
        messages.error(request, '  You are not authorized to delete this interview.')
        return redirect('interviews:interview_list')
    
    if request.method == 'POST':
        try:
            stop_detection(interview.id)  # Stop any running detection
            interview.delete()
            messages.success(request, '✅ Interview deleted successfully!')
        except Exception as e:
            messages.error(request, f'  Error deleting interview: {str(e)}')
        return redirect('interviews:interview_list')
    
    return render(request, 'interviews/confirm_delete.html', {'interview': interview})

@login_required
def reschedule_interview(request, interview_id):
    """Reschedule interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    # Placeholder - implement reschedule functionality
    messages.info(request, 'Reschedule functionality coming soon!')
    return redirect('interviews:interview_detail', interview_id=interview.id)

@login_required
def interview_reports(request):
    """Interview reports dashboard"""
    # Placeholder - implement reports functionality
    interviews = Interview.objects.filter(status='completed')[:10]
    return render(request, 'interviews/reports.html', {'interviews': interviews})

@login_required
def interview_report(request, interview_id):
    """Individual interview report"""
    interview = get_object_or_404(Interview, id=interview_id)
    # Placeholder - implement detailed report
    return render(request, 'interviews/interview_report.html', {'interview': interview})