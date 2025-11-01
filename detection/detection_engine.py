import threading
import time
from django.utils import timezone
from .models import EventLog, DetectionSession

# Import computer vision libraries (currently placeholders)
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV not available - using simulation mode")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️ MediaPipe not available - using simulation mode")

# Global dictionary to track active detection threads
active_detection_threads = {}


class DetectionThread(threading.Thread):
    def __init__(self, interview, duration_minutes=30):
        super().__init__()
        self.interview = interview
        self.duration_minutes = duration_minutes
        self.stop_event = threading.Event()
        self.daemon = True
        
        # Create detection session
        self.session = DetectionSession.objects.create(
            interview=interview,
            status='active'
        )
        
        print(f"🔍 Detection thread initialized for interview {interview.id}")
    
    def run(self):
        """Main detection loop"""
        print(f"🎬 Starting detection for interview {self.interview.id}")
        
        start_time = time.time()
        end_time = start_time + (self.duration_minutes * 60)
        frame_count = 0
        event_count = 0
        
        # Simulation variables (replace with real camera feed)
        simulation_cycle = 0
        
        try:
            while not self.stop_event.is_set() and time.time() < end_time:
                frame_count += 1
                simulation_cycle += 1
                
                # 🔧 PLACEHOLDER: This is where real computer vision would go
                # For now, simulate detection events periodically
                
                # Simulate focus loss every 30 frames
                if simulation_cycle % 30 == 0:
                    self._log_event(
                        'focus_lost',
                        'Simulated: Candidate looked away from screen',
                        0.85
                    )
                    event_count += 1
                
                # Simulate no face detection every 50 frames
                if simulation_cycle % 50 == 0:
                    self._log_event(
                        'no_face',
                        'Simulated: No face detected in frame',
                        0.92
                    )
                    event_count += 1
                
                # Simulate phone detection every 100 frames
                if simulation_cycle % 100 == 0:
                    self._log_event(
                        'phone_detected',
                        'Simulated: Phone detected in frame',
                        0.78
                    )
                    event_count += 1
                
                # Update session statistics
                self.session.total_frames_processed = frame_count
                self.session.total_events_logged = event_count
                self.session.save(update_fields=['total_frames_processed', 'total_events_logged'])
                
                # Sleep to simulate frame processing (simulate ~10 FPS)
                time.sleep(0.1)
            
            # Mark session as stopped
            self.session.status = 'stopped'
            self.session.ended_at = timezone.now()
            self.session.save()
            
            print(f"✅ Detection completed for interview {self.interview.id}")
            print(f"📊 Processed {frame_count} frames, logged {event_count} events")
            
        except Exception as e:
            print(f"❌ Error in detection thread: {e}")
            self.session.status = 'error'
            self.session.error_message = str(e)
            self.session.ended_at = timezone.now()
            self.session.save()
    
    def stop(self):
        """Stop the detection thread"""
        print(f"🛑 Stopping detection thread for interview {self.interview.id}")
        self.stop_event.set()
    
    def _log_event(self, event_type, description, confidence):
        """Log detection event to database"""
        try:
            # Map internal event types to database event types
            event_type_mapping = {
                'focus_loss': 'focus_lost',
                'phone': 'phone_detected',
                'notes': 'notes_detected',
                'device': 'device_detected',
            }
            
            # Use mapped type if exists, otherwise use original
            db_event_type = event_type_mapping.get(event_type, event_type)
            
            EventLog.objects.create(
                interview=self.interview,
                event_type=db_event_type,
                description=description,
                confidence_score=confidence
            )
            print(f"📝 Logged: {db_event_type} - {description} (confidence: {confidence:.2%})")
        except Exception as e:
            print(f"❌ Error logging event: {e}")


def start_detection(interview, duration_minutes=30):
    """Start detection for an interview"""
    interview_id = interview.id
    
    # Stop any existing detection
    stop_detection(interview_id)
    
    # Create and start new thread
    thread = DetectionThread(interview, duration_minutes)
    thread.start()
    
    # Store in global dictionary
    active_detection_threads[interview_id] = thread
    
    print(f"✅ Detection thread started for interview {interview_id}")
    return True


def stop_detection(interview_id):
    """Stop detection for an interview"""
    print(f"🛑 Attempting to stop detection for interview {interview_id}")
    
    if interview_id in active_detection_threads:
        print(f"📋 Found active thread for interview {interview_id}")
        thread = active_detection_threads[interview_id]
        thread.stop()
        thread.join(timeout=2)  # Wait up to 2 seconds
        del active_detection_threads[interview_id]
        print(f"✅ Detection stopped successfully for interview {interview_id}")
        return True
    else:
        print(f"ℹ️ No active detection found for interview {interview_id}")
        return False


def is_detection_active(interview_id):
    """Check if detection is active for an interview"""
    active = interview_id in active_detection_threads and active_detection_threads[interview_id].is_alive()
    print(f"🔍 Detection active for interview {interview_id}: {active}")
    return active


def get_active_detection_count():
    """Get count of active detection threads"""
    active_count = sum(1 for thread in active_detection_threads.values() if thread.is_alive())
    print(f"📊 Active detection threads: {active_count}/{len(active_detection_threads)}")
    return active_count


def get_detection_summary(interview):
    """Get detection summary for an interview"""
    try:
        events = interview.event_logs.all()
        
        summary = {
            'total_events': events.count(),
            'focus_lost': events.filter(event_type='focus_lost').count(),
            'no_face': events.filter(event_type='no_face').count(),
            'multiple_faces': events.filter(event_type='multiple_faces').count(),
            'phone_detected': events.filter(event_type='phone_detected').count(),
            'notes_detected': events.filter(event_type='notes_detected').count(),
            'device_detected': events.filter(event_type='device_detected').count(),
            'drowsiness': events.filter(event_type='drowsiness').count(),
            'audio_anomaly': events.filter(event_type='audio_anomaly').count(),
        }
        
        return summary
        
    except Exception as e:
        print(f"❌ Error getting detection summary: {e}")
        return {}


def log_event(interview, event_type, description="", confidence_score=0.0):
    """Legacy function - log a detection event"""
    try:
        EventLog.objects.create(
            interview=interview,
            event_type=event_type,
            description=description,
            confidence_score=confidence_score
        )
        return True
    except Exception as e:
        print(f"❌ Error logging event: {e}")
        return False


def cleanup_inactive_threads():
    """Remove inactive threads from tracking dictionary"""
    inactive_ids = [
        interview_id for interview_id, thread in active_detection_threads.items()
        if not thread.is_alive()
    ]
    
    for interview_id in inactive_ids:
        del active_detection_threads[interview_id]
        print(f"🧹 Cleaned up inactive thread for interview {interview_id}")
    
    return len(inactive_ids)


# Legacy function for backward compatibility
def run_detection_loop(interview, duration_minutes=30):
    """Legacy function - use start_detection instead"""
    return start_detection(interview, duration_minutes)
