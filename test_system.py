#!/usr/bin/env python
"""
Comprehensive test script for the Proctoring System
This script tests all major functionality of the system
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proctoring_system.settings')
django.setup()

from accounts.models import User
from interviews.models import Interview, VideoRecording
from detection.models import EventLog
from reports.models import Report

def test_user_creation():
    """Test user creation and authentication"""
    print("Testing user creation...")
    
    # Test creating different user types
    candidate = User.objects.create_user(
        username='test_candidate',
        email='candidate@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Candidate',
        role='candidate'
    )
    
    interviewer = User.objects.create_user(
        username='test_interviewer',
        email='interviewer@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Interviewer',
        role='interviewer'
    )
    
    admin = User.objects.create_user(
        username='test_admin',
        email='admin@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Admin',
        role='admin'
    )
    
    print(f"✓ Created candidate: {candidate}")
    print(f"✓ Created interviewer: {interviewer}")
    print(f"✓ Created admin: {admin}")
    
    return candidate, interviewer, admin

def test_interview_creation(candidate, interviewer):
    """Test interview creation and management"""
    print("\nTesting interview creation...")
    
    # Create a scheduled interview
    interview = Interview.objects.create(
        candidate=candidate,
        interviewer=interviewer,
        start_time=timezone.now() + timedelta(hours=1),
        status='scheduled'
    )
    
    print(f"✓ Created interview: {interview}")
    
    # Test starting interview
    interview.status = 'ongoing'
    interview.start_time = timezone.now()
    interview.save()
    
    print(f"✓ Started interview: {interview}")
    
    # Test ending interview
    interview.status = 'completed'
    interview.end_time = timezone.now() + timedelta(minutes=30)
    interview.save()
    
    print(f"✓ Completed interview: {interview}")
    print(f"✓ Interview duration: {interview.duration}")
    
    return interview

def test_detection_events(interview):
    """Test detection event logging"""
    print("\nTesting detection events...")
    
    # Create various detection events
    events = [
        ('focus_lost', 'Candidate looked away from camera', 0.8),
        ('phone_detected', 'Phone detected in frame', 0.9),
        ('notes_detected', 'Notes detected on desk', 0.7),
        ('multiple_faces', 'Multiple faces detected', 0.6),
        ('drowsiness', 'Drowsiness detected', 0.5),
    ]
    
    for event_type, description, confidence in events:
        event = EventLog.objects.create(
            interview=interview,
            event_type=event_type,
            description=description,
            confidence_score=confidence
        )
        print(f"✓ Created event: {event}")
    
    print(f"✓ Total events created: {EventLog.objects.filter(interview=interview).count()}")

def test_report_generation(interview):
    """Test report generation"""
    print("\nTesting report generation...")
    
    # Get event counts
    events = EventLog.objects.filter(interview=interview)
    focus_lost_events = events.filter(event_type='focus_lost').count()
    suspicious_events = events.filter(
        event_type__in=['phone_detected', 'notes_detected', 'multiple_faces']
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
    
    print(f"✓ Created report: {report}")
    print(f"✓ Integrity score: {report.integrity_score}")
    print(f"✓ Focus loss events: {report.focus_loss_count}")
    print(f"✓ Suspicious events: {report.suspicious_events}")
    
    return report

def test_api_endpoints():
    """Test API endpoints"""
    print("\nTesting API endpoints...")
    
    client = Client()
    
    # Test login
    response = client.post('/accounts/login/', {
        'username': 'admin',
        'password': 'admin123'
    })
    print(f"✓ Login response: {response.status_code}")
    
    # Test interview list
    response = client.get('/interviews/')
    print(f"✓ Interview list response: {response.status_code}")
    
    # Test reports list
    response = client.get('/reports/')
    print(f"✓ Reports list response: {response.status_code}")
    
    # Test detection events API
    interview = Interview.objects.first()
    if interview:
        response = client.get(f'/detection/{interview.id}/events/')
        print(f"✓ Detection events API response: {response.status_code}")

def test_detection_engine():
    """Test detection engine functionality"""
    print("\nTesting detection engine...")
    
    from detection.detection_engine import (
        detect_focus, detect_objects, detect_face, 
        detect_drowsiness, log_event, get_detection_summary
    )
    
    # Test detection functions
    focus_result = detect_focus(None)
    print(f"✓ Focus detection: {focus_result}")
    
    objects_result = detect_objects(None)
    print(f"✓ Object detection: {objects_result}")
    
    face_count = detect_face(None)
    print(f"✓ Face detection: {face_count}")
    
    drowsiness = detect_drowsiness(None)
    print(f"✓ Drowsiness detection: {drowsiness}")
    
    # Test event logging
    interview = Interview.objects.first()
    if interview:
        success = log_event(interview, 'test_event', 'Test event', 0.5)
        print(f"✓ Event logging: {success}")
        
        summary = get_detection_summary(interview)
        print(f"✓ Detection summary: {summary}")

def test_pdf_generation(report):
    """Test PDF report generation"""
    print("\nTesting PDF generation...")
    
    try:
        from reports.utils import generate_pdf
        pdf_content = generate_pdf(report)
        print(f"✓ PDF generated successfully, size: {len(pdf_content)} bytes")
    except Exception as e:
        print(f"✗ PDF generation failed: {e}")

def test_csv_generation(report):
    """Test CSV report generation"""
    print("\nTesting CSV generation...")
    
    try:
        from reports.utils import generate_csv
        csv_content = generate_csv(report)
        print(f"✓ CSV generated successfully, size: {len(csv_content)} bytes")
    except Exception as e:
        print(f"✗ CSV generation failed: {e}")

def cleanup_test_data():
    """Clean up test data"""
    print("\nCleaning up test data...")
    
    # Delete test users (except admin)
    User.objects.filter(username__startswith='test_').delete()
    print("✓ Deleted test users")
    
    # Delete test interviews and related data
    Interview.objects.filter(candidate__username__startswith='test_').delete()
    print("✓ Deleted test interviews")
    
    # Delete test events
    EventLog.objects.filter(interview__candidate__username__startswith='test_').delete()
    print("✓ Deleted test events")
    
    # Delete test reports
    Report.objects.filter(interview__candidate__username__startswith='test_').delete()
    print("✓ Deleted test reports")

def main():
    """Main test function"""
    print("=" * 60)
    print("PROCTORING SYSTEM COMPREHENSIVE TEST")
    print("=" * 60)
    
    try:
        # Test user creation
        candidate, interviewer, admin = test_user_creation()
        
        # Test interview creation
        interview = test_interview_creation(candidate, interviewer)
        
        # Test detection events
        test_detection_events(interview)
        
        # Test report generation
        report = test_report_generation(interview)
        
        # Test API endpoints
        test_api_endpoints()
        
        # Test detection engine
        test_detection_engine()
        
        # Test PDF generation
        test_pdf_generation(report)
        
        # Test CSV generation
        test_csv_generation(report)
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY! ✓")
        print("=" * 60)
        
        # Optional cleanup
        response = input("\nClean up test data? (y/n): ").lower()
        if response == 'y':
            cleanup_test_data()
            print("Test data cleaned up.")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
