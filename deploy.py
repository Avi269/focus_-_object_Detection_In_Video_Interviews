#!/usr/bin/env python
"""
Deployment script for Tutedude SDE Assignment
Focus & Object Detection in Video Interviews
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def setup_project():
    """Setup the project for deployment"""
    print("🚀 Setting up Proctoring System for Deployment...")
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proctoring_system.settings')
    django.setup()
    
    print("✅ Django setup complete")

def run_migrations():
    """Run database migrations"""
    print("📊 Running database migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("✅ Migrations complete")

def create_superuser():
    """Create superuser if not exists"""
    print("👤 Creating superuser...")
    from accounts.models import User
    
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123', role='admin')
        print("✅ Superuser created: admin / admin123")
    else:
        print("✅ Superuser already exists")

def create_demo_users():
    """Create demo users for testing"""
    print("👥 Creating demo users...")
    from accounts.models import User
    
    # Create candidate
    candidate, created = User.objects.get_or_create(
        username='candidate',
        defaults={
            'email': 'candidate@demo.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'candidate'
        }
    )
    if created:
        candidate.set_password('candidate123')
        candidate.save()
        print("✅ Demo candidate created: candidate / candidate123")
    else:
        print("✅ Demo candidate already exists")
    
    # Create interviewer
    interviewer, created = User.objects.get_or_create(
        username='interviewer',
        defaults={
            'email': 'interviewer@demo.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'role': 'interviewer'
        }
    )
    if created:
        interviewer.set_password('interviewer123')
        interviewer.save()
        print("✅ Demo interviewer created: interviewer / interviewer123")
    else:
        print("✅ Demo interviewer already exists")

def create_sample_data():
    """Create sample interview and events"""
    print("📝 Creating sample data...")
    from accounts.models import User
    from interviews.models import Interview
    from detection.models import EventLog
    from reports.models import Report
    from django.utils import timezone
    from datetime import timedelta
    
    # Get users
    candidate = User.objects.get(username='candidate')
    interviewer = User.objects.get(username='interviewer')
    
    # Create sample interview
    interview, created = Interview.objects.get_or_create(
        candidate=candidate,
        interviewer=interviewer,
        defaults={
            'start_time': timezone.now() - timedelta(hours=1),
            'end_time': timezone.now() - timedelta(minutes=30),
            'status': 'completed'
        }
    )
    
    if created:
        print("✅ Sample interview created")
        
        # Create sample events
        events_data = [
            ('focus_lost', 'Candidate looked away for 6 seconds', 0.8),
            ('focus_lost', 'Candidate looked at second screen for 7 seconds', 0.7),
            ('phone_detected', 'Mobile phone detected in frame', 0.9),
            ('notes_detected', 'Books detected on desk', 0.6),
            ('multiple_faces', '2 faces detected in frame', 0.8),
            ('no_face', 'No face detected for 12 seconds', 0.9),
            ('drowsiness', 'Drowsiness detected - eyes closed', 0.5),
            ('device_detected', 'Laptop detected in background', 0.7),
        ]
        
        for event_type, description, confidence in events_data:
            EventLog.objects.create(
                interview=interview,
                event_type=event_type,
                description=description,
                confidence_score=confidence
            )
        
        print("✅ Sample events created")
        
        # Create sample report
        events = EventLog.objects.filter(interview=interview)
        report = Report.objects.create(
            interview=interview,
            candidate_name=candidate.get_full_name() or candidate.username,
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
        
        print(f"✅ Sample report created with integrity score: {report.integrity_score}")
    else:
        print("✅ Sample data already exists")

def show_access_info():
    """Show access information"""
    print("\n" + "="*60)
    print("🎉 DEPLOYMENT COMPLETE!")
    print("="*60)
    print("\n📱 Access Information:")
    print("🌐 Web Interface: http://127.0.0.1:8000")
    print("🔧 Admin Panel: http://127.0.0.1:8000/admin")
    print("\n👤 Login Credentials:")
    print("   Admin: admin / admin123")
    print("   Candidate: candidate / candidate123")
    print("   Interviewer: interviewer / interviewer123")
    print("\n🚀 To start the server:")
    print("   python manage.py runserver")
    print("\n📊 Features Available:")
    print("   ✅ Real-time focus detection")
    print("   ✅ Object detection (phone, notes, devices)")
    print("   ✅ Multiple face detection")
    print("   ✅ Drowsiness detection")
    print("   ✅ Proctoring reports with integrity scoring")
    print("   ✅ PDF/CSV export")
    print("   ✅ Modern responsive UI")
    print("\n📄 Sample Report Generated:")
    print("   - Check Reports section in web interface")
    print("   - Download PDF/CSV formats")
    print("   - View detailed integrity analysis")

def main():
    """Main deployment function"""
    try:
        setup_project()
        run_migrations()
        create_superuser()
        create_demo_users()
        create_sample_data()
        show_access_info()
        
        print("\n✅ All systems ready for Tutedude SDE Assignment!")
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
