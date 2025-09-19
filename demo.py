#!/usr/bin/env python
"""
Demo script for the Proctoring System
This script demonstrates the key features of the system
"""

import os
import sys
import django
from django.utils import timezone
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proctoring_system.settings')
django.setup()

from accounts.models import User
from interviews.models import Interview
from detection.models import EventLog
from reports.models import Report
from detection.detection_engine import run_detection_loop, get_detection_summary

def create_demo_data():
    """Create comprehensive demo data"""
    print("Creating demo data...")
    
    # Create demo users if they don't exist
    candidate, created = User.objects.get_or_create(
        username='demo_candidate',
        defaults={
            'email': 'candidate@demo.com',
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'role': 'candidate'
        }
    )
    if created:
        candidate.set_password('demo123')
        candidate.save()
        print(f"✓ Created candidate: {candidate}")
    else:
        print(f"✓ Using existing candidate: {candidate}")
    
    interviewer, created = User.objects.get_or_create(
        username='demo_interviewer',
        defaults={
            'email': 'interviewer@demo.com',
            'first_name': 'Bob',
            'last_name': 'Smith',
            'role': 'interviewer'
        }
    )
    if created:
        interviewer.set_password('demo123')
        interviewer.save()
        print(f"✓ Created interviewer: {interviewer}")
    else:
        print(f"✓ Using existing interviewer: {interviewer}")
    
    # Create demo interview
    interview, created = Interview.objects.get_or_create(
        candidate=candidate,
        interviewer=interviewer,
        defaults={
            'start_time': timezone.now() + timedelta(hours=1),
            'status': 'scheduled'
        }
    )
    
    if created:
        print(f"✓ Created interview: {interview}")
    else:
        print(f"✓ Using existing interview: {interview}")
    
    return candidate, interviewer, interview

def simulate_interview_session(interview):
    """Simulate a complete interview session"""
    print(f"\nSimulating interview session: {interview}")
    
    # Start the interview
    interview.status = 'ongoing'
    interview.start_time = timezone.now()
    interview.save()
    print("✓ Interview started")
    
    # Simulate detection events during interview
    print("✓ Simulating detection events...")
    
    # Create various detection events
    events_data = [
        ('focus_lost', 'Candidate looked away from camera', 0.8),
        ('focus_lost', 'Candidate looked at second screen', 0.7),
        ('phone_detected', 'Phone detected in frame', 0.9),
        ('notes_detected', 'Notes detected on desk', 0.6),
        ('multiple_faces', 'Multiple faces detected', 0.8),
        ('drowsiness', 'Drowsiness detected - eyes closed', 0.5),
        ('no_face', 'No face detected in frame', 0.9),
        ('device_detected', 'External device detected', 0.7),
    ]
    
    for event_type, description, confidence in events_data:
        EventLog.objects.create(
            interview=interview,
            event_type=event_type,
            description=description,
            confidence_score=confidence
        )
        print(f"  - Logged: {event_type}")
    
    # End the interview
    interview.status = 'completed'
    interview.end_time = timezone.now() + timedelta(minutes=45)
    interview.save()
    print("✓ Interview completed")
    
    return interview

def generate_demo_report(interview):
    """Generate a comprehensive demo report"""
    print(f"\nGenerating report for: {interview}")
    
    # Check if report already exists
    if hasattr(interview, 'report'):
        print(f"✓ Using existing report: {interview.report}")
        return interview.report
    
    # Get event counts
    events = EventLog.objects.filter(interview=interview)
    
    # Create comprehensive report
    report = Report.objects.create(
        interview=interview,
        candidate_name=interview.candidate.get_full_name() or interview.candidate.username,
        focus_loss_count=events.filter(event_type='focus_lost').count(),
        suspicious_events=events.filter(
            event_type__in=['phone_detected', 'notes_detected', 'device_detected', 'multiple_faces']
        ).count(),
        total_duration=interview.duration,
        face_detection_accuracy=0.85,
        audio_quality_score=0.92,
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
    
    print(f"✓ Report generated: {report}")
    print(f"  - Integrity Score: {report.integrity_score}/100")
    print(f"  - Focus Loss Events: {report.focus_loss_count}")
    print(f"  - Suspicious Events: {report.suspicious_events}")
    print(f"  - Interview Duration: {report.total_duration}")
    
    return report

def demonstrate_detection_engine():
    """Demonstrate detection engine capabilities"""
    print("\nDemonstrating detection engine...")
    
    from detection.detection_engine import (
        detect_focus, detect_objects, detect_face, 
        detect_drowsiness, log_event
    )
    
    # Simulate detection on sample frames
    print("✓ Testing focus detection...")
    for i in range(3):
        focus = detect_focus(None)
        print(f"  Frame {i+1}: Focus {'maintained' if focus else 'lost'}")
    
    print("✓ Testing object detection...")
    for i in range(3):
        objects = detect_objects(None)
        print(f"  Frame {i+1}: Detected {objects if objects else 'nothing'}")
    
    print("✓ Testing face detection...")
    for i in range(3):
        faces = detect_face(None)
        print(f"  Frame {i+1}: {faces} face(s) detected")
    
    print("✓ Testing drowsiness detection...")
    for i in range(3):
        drowsy = detect_drowsiness(None)
        print(f"  Frame {i+1}: {'Drowsy' if drowsy else 'Alert'}")

def demonstrate_report_export(report):
    """Demonstrate report export functionality"""
    print(f"\nDemonstrating report export for: {report}")
    
    try:
        from reports.utils import generate_pdf, generate_csv
        
        # Generate PDF
        pdf_content = generate_pdf(report)
        print(f"✓ PDF generated: {len(pdf_content)} bytes")
        
        # Generate CSV
        csv_content = generate_csv(report)
        print(f"✓ CSV generated: {len(csv_content)} bytes")
        
        # Save demo files
        with open('demo_report.pdf', 'wb') as f:
            f.write(pdf_content)
        print("✓ PDF saved as demo_report.pdf")
        
        with open('demo_report.csv', 'wb') as f:
            f.write(csv_content)
        print("✓ CSV saved as demo_report.csv")
        
    except Exception as e:
        print(f"✗ Export failed: {e}")

def show_system_summary():
    """Show system summary"""
    print("\n" + "="*60)
    print("SYSTEM SUMMARY")
    print("="*60)
    
    print(f"Total Users: {User.objects.count()}")
    print(f"  - Candidates: {User.objects.filter(role='candidate').count()}")
    print(f"  - Interviewers: {User.objects.filter(role='interviewer').count()}")
    print(f"  - Admins: {User.objects.filter(role='admin').count()}")
    
    print(f"Total Interviews: {Interview.objects.count()}")
    print(f"  - Scheduled: {Interview.objects.filter(status='scheduled').count()}")
    print(f"  - Ongoing: {Interview.objects.filter(status='ongoing').count()}")
    print(f"  - Completed: {Interview.objects.filter(status='completed').count()}")
    
    print(f"Total Detection Events: {EventLog.objects.count()}")
    print(f"Total Reports: {Report.objects.count()}")
    
    # Show recent events
    recent_events = EventLog.objects.order_by('-timestamp')[:5]
    print(f"\nRecent Detection Events:")
    for event in recent_events:
        print(f"  - {event.get_event_type_display()}: {event.description}")

def main():
    """Main demo function"""
    print("="*60)
    print("PROCTORING SYSTEM DEMONSTRATION")
    print("="*60)
    
    try:
        # Create demo data
        candidate, interviewer, interview = create_demo_data()
        
        # Simulate interview session
        interview = simulate_interview_session(interview)
        
        # Generate report
        report = generate_demo_report(interview)
        
        # Demonstrate detection engine
        demonstrate_detection_engine()
        
        # Demonstrate report export
        demonstrate_report_export(report)
        
        # Show system summary
        show_system_summary()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY! ✓")
        print("="*60)
        print("\nTo access the web interface:")
        print("1. Start the server: python manage.py runserver")
        print("2. Open browser: http://127.0.0.1:8000")
        print("3. Login with:")
        print("   - Admin: admin / admin123")
        print("   - Candidate: demo_candidate / demo123")
        print("   - Interviewer: demo_interviewer / demo123")
        
    except Exception as e:
        print(f"\n✗ DEMONSTRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
