import threading
import time
import random
from django.utils import timezone
from .models import EventLog

# Optional imports for computer vision libraries
try:
    import cv2
    import numpy as np
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False
    print("📦 OpenCV not available. Detection will use simulation mode.")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("📦 MediaPipe not available. Detection will use simulation mode.")

# Global dictionary to track active detection threads
active_detection_threads = {}

class DetectionThread(threading.Thread):
    def __init__(self, interview, duration_minutes=30):
        super().__init__()
        self.interview = interview
        self.duration_minutes = duration_minutes
        self._stop_event = threading.Event()
        self.daemon = True

    def run(self):
        """Main detection loop with proper stop control"""
        print(f"🔍 Detection started for interview {self.interview.id}")
        
        start_time = time.time()
        duration_seconds = self.duration_minutes * 60
        
        # State tracking for timing requirements
        focus_lost_start = None
        no_face_start = None
        focus_lost_threshold = 5  # 5 seconds
        no_face_threshold = 10   # 10 seconds
        
        while not self._stop_event.is_set():
            # Check if interview is still ongoing
            try:
                self.interview.refresh_from_db()
                if self.interview.status != 'ongoing':
                    print(f"📋 Interview {self.interview.id} no longer ongoing, stopping detection")
                    break
            except Exception as e:
                print(f"❌ Error refreshing interview: {e}")
                break
            
            # Check duration timeout
            elapsed = time.time() - start_time
            if elapsed > duration_seconds:
                print(f"⏰ Detection duration complete for interview {self.interview.id}")
                break
            
            try:
                # Simulate detection work
                current_time = time.time()
                
                # Focus detection with timing
                focus_maintained = self._detect_focus()
                if not focus_maintained:
                    if focus_lost_start is None:
                        focus_lost_start = current_time
                    elif current_time - focus_lost_start > focus_lost_threshold:
                        self._log_event('focus_loss', 
                                      f'Focus lost for {int(current_time - focus_lost_start)} seconds', 
                                      random.uniform(0.7, 0.9))
                        focus_lost_start = None
                else:
                    focus_lost_start = None
                
                # Face detection
                face_count = self._detect_faces()
                if face_count == 0:
                    if no_face_start is None:
                        no_face_start = current_time
                    elif current_time - no_face_start > no_face_threshold:
                        self._log_event('no_face', 
                                      f'No face detected for {int(current_time - no_face_start)} seconds', 
                                      random.uniform(0.8, 1.0))
                        no_face_start = None
                elif face_count > 1:
                    self._log_event('multiple_faces', 
                                  f'{face_count} faces detected', 
                                  random.uniform(0.8, 1.0))
                    no_face_start = None
                else:
                    no_face_start = None
                
                # Object detection
                objects = self._detect_objects()
                for obj in objects:
                    self._log_event(f'{obj}_detected', f'{obj} detected in frame', 
                                  random.uniform(0.7, 0.9))
                
                # Drowsiness detection
                if self._detect_drowsiness():
                    self._log_event('drowsiness', 'Signs of drowsiness detected', 
                                  random.uniform(0.6, 0.8))
                
            except Exception as e:
                print(f"❌ Detection error: {e}")
            
            # Wait before next cycle (or until stop signal)
            if self._stop_event.wait(timeout=2):  # Check every 2 seconds
                break
        
        print(f"🛑 Detection stopped for interview {self.interview.id}")
        # Clean up from global tracking
        if self.interview.id in active_detection_threads:
            del active_detection_threads[self.interview.id]

    def _detect_focus(self):
        """Simulate focus detection"""
        return random.random() < 0.9  # 90% focused

    def _detect_faces(self):
        """Simulate face detection"""
        rand = random.random()
        if rand < 0.95:
            return 1  # Normal case
        elif rand < 0.99:
            return 0  # No face
        else:
            return 2  # Multiple faces

    def _detect_objects(self):
        """Simulate object detection"""
        objects = []
        if random.random() < 0.05:  # 5% chance
            objects.append(random.choice(['phone', 'notes', 'device']))
        return objects

    def _detect_drowsiness(self):
        """Simulate drowsiness detection"""
        return random.random() < 0.02  # 2% chance

    def _log_event(self, event_type, description, confidence):
        """Log detection event to database"""
        try:
            EventLog.objects.create(
                interview=self.interview,
                event_type=event_type,
                description=description,
                confidence_score=confidence
            )
            print(f"📝 Logged: {event_type} - {description}")
        except Exception as e:
            print(f"❌ Error logging event: {e}")

    def stop(self):
        """Signal the thread to stop"""
        self._stop_event.set()

def start_detection(interview, duration_minutes=30):
    """Start detection for an interview"""
    print(f"🚀 Starting detection for interview {interview.id}")
    
    # Stop any existing detection for this interview
    stop_detection(interview.id)
    
    # Create and start new detection thread
    detection_thread = DetectionThread(interview, duration_minutes)
    active_detection_threads[interview.id] = detection_thread
    detection_thread.start()
    
    print(f"✅ Detection thread started for interview {interview.id}")
    return detection_thread

def stop_detection(interview_id):
    """Stop detection for an interview"""
    print(f"🛑 Attempting to stop detection for interview {interview_id}")
    
    if interview_id in active_detection_threads:
        thread = active_detection_threads[interview_id]
        print(f"📋 Found active thread for interview {interview_id}")
        
        # Signal thread to stop
        thread.stop()
        
        # Wait for thread to finish
        thread.join(timeout=10)  # Wait up to 10 seconds
        
        if thread.is_alive():
            print(f"⚠️ WARNING: Detection thread for interview {interview_id} did not stop cleanly")
            # Force remove from tracking even if thread didn't stop
            del active_detection_threads[interview_id]
        else:
            print(f"✅ Detection stopped successfully for interview {interview_id}")
            
        # Remove from tracking
        if interview_id in active_detection_threads:
            del active_detection_threads[interview_id]
            
    else:
        print(f"ℹ️ No active detection found for interview {interview_id}")
    
    # Double-check removal
    if interview_id in active_detection_threads:
        del active_detection_threads[interview_id]
        print(f"🧹 Force-removed thread tracking for interview {interview_id}")

def is_detection_active(interview_id):
    """Check if detection is active for an interview"""
    active = interview_id in active_detection_threads and active_detection_threads[interview_id].is_alive()
    print(f"🔍 Detection active for interview {interview_id}: {active}")
    return active

def get_active_detection_count():
    """Get count of currently active detection threads"""
    alive_count = len([t for t in active_detection_threads.values() if t.is_alive()])
    total_count = len(active_detection_threads)
    print(f"📊 Active detection threads: {alive_count}/{total_count}")
    return alive_count

def get_detection_summary(interview):
    """Get a summary of all detection events for an interview"""
    events = EventLog.objects.filter(interview=interview)
    
    summary = {
        'total_events': events.count(),
        'focus_loss': events.filter(event_type='focus_loss').count(),
        'no_face': events.filter(event_type='no_face').count(),
        'multiple_faces': events.filter(event_type='multiple_faces').count(),
        'phone_detected': events.filter(event_type='phone_detected').count(),
        'notes_detected': events.filter(event_type='notes_detected').count(),
        'device_detected': events.filter(event_type='device_detected').count(),
        'drowsiness': events.filter(event_type='drowsiness').count(),
        'integrity_score': max(0, 100 - (events.count() * 5)),
        'latest_event': events.first().timestamp if events.exists() else None,
    }
    
    return summary

def log_event(interview, event_type, description="", confidence_score=0.0):
    """Log an event to the database (standalone function)"""
    try:
        EventLog.objects.create(
            interview=interview,
            event_type=event_type,
            description=description,
            confidence_score=confidence_score
        )
        print(f"📝 Event logged: {event_type} - {description}")
        return True
    except Exception as e:
        print(f"❌ Error logging event: {e}")
        return False

# 🔧 ADDED: Missing cleanup function
def cleanup_inactive_threads():
    """Clean up any inactive threads from the global dictionary"""
    inactive_threads = []
    
    for interview_id, thread in list(active_detection_threads.items()):
        if not thread.is_alive():
            inactive_threads.append(interview_id)
            del active_detection_threads[interview_id]
            print(f"🧹 Cleaned up inactive thread for interview {interview_id}")
    
    print(f"🧹 Cleanup complete: {len(inactive_threads)} threads removed")
    return len(inactive_threads)

# Legacy function for backward compatibility
def run_detection_loop(interview, duration_minutes=30):
    """Legacy function - use start_detection instead"""
    return start_detection(interview, duration_minutes)

def analyze_video_file(video_path, interview):
    """Analyze uploaded video file for suspicious activities"""
    try:
        print(f"📹 Analyzing video file: {video_path}")
        
        # Simulate video analysis with random events
        events_created = 0
        for i in range(random.randint(0, 3)):
            event_type = random.choice(['focus_loss', 'phone_detected', 'notes_detected'])
            description = f"Video analysis detection {i+1}: {event_type}"
            confidence = random.uniform(0.7, 0.9)
            
            if log_event(interview, event_type, description, confidence):
                events_created += 1
        
        print(f"📹 Video analysis complete. {events_created} events detected.")
        return events_created
        
    except Exception as e:
        print(f"❌ Video analysis failed: {e}")
        raise

def force_stop_all_detection():
    """Emergency function to stop all detection threads"""
    print("🚨 FORCE STOPPING ALL DETECTION THREADS")
    
    for interview_id, thread in list(active_detection_threads.items()):
        print(f"🛑 Force stopping detection for interview {interview_id}")
        thread.stop()
        thread.join(timeout=2)
        if interview_id in active_detection_threads:
            del active_detection_threads[interview_id]
    
    print("✅ All detection threads force stopped")

# Optional: Add periodic cleanup
def start_periodic_cleanup():
    """Start periodic cleanup of inactive threads"""
    def cleanup_worker():
        while True:
            time.sleep(300)  # Run every 5 minutes
            try:
                cleanup_inactive_threads()
            except Exception as e:
                print(f"❌ Periodic cleanup error: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    print("🔄 Periodic cleanup thread started")
