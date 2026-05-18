import threading
import time
import logging
import queue
from collections import deque
from datetime import datetime, timedelta
import numpy as np
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import EventLog, DetectionSession

# Initialize logger
logger = logging.getLogger(__name__)

# Import computer vision libraries
try:
    import cv2
    CV2_AVAILABLE = True
    logger.info("✅ OpenCV loaded successfully")
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("⚠️ OpenCV not available - using simulation mode")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    logger.info("✅ MediaPipe loaded successfully")
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning("⚠️ MediaPipe not available - using simulation mode")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logger.info("✅ YOLOv8 loaded successfully")
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("⚠️ YOLO not available - object detection disabled")

# Global dictionary to track active detection threads
active_detection_threads = {}

# Detection configuration
DETECTION_CONFIG = {
    'frame_width': 640,
    'frame_height': 480,
    'fps': 30,
    
    # Thresholds
    'focus_lost_threshold': 5,  # seconds
    'no_face_threshold': 10,  # seconds
    'drowsiness_threshold': 3,  # seconds
    'confidence_threshold': 0.7,
    
    # Detection intervals
    'face_check_interval': 0.5,  # seconds
    'phone_check_interval': 1.0,  # seconds
    'object_check_interval': 2.0,  # seconds (YOLO every 2 seconds)
    'screenshot_on_violation': True,
    
    # Eye aspect ratio for drowsiness
    'ear_threshold': 0.25,
    'ear_consecutive_frames': 20,
    
    # YOLO settings
    'yolo_model': 'yolov8n.pt',  # nano = fastest, s/m/l for better accuracy
    'yolo_confidence': 0.5,  # Minimum confidence for detections
    'yolo_target_classes': [67, 73, 63, 66, 64],  # phone, book, laptop, keyboard, mouse
}

# COCO class names for reference
COCO_CLASSES = {
    0: 'person',
    63: 'laptop',
    64: 'mouse',
    66: 'keyboard',
    67: 'cell phone',
    73: 'book',
    76: 'scissors',
    84: 'book',
}


class DetectionThread(threading.Thread):
    """
    Real-time detection thread using computer vision
    """
    
    def __init__(self, interview, duration_minutes=30, camera_index=0):
        super().__init__()
        self.interview = interview
        self.duration_minutes = duration_minutes
        self.camera_index = camera_index
        self.stop_event = threading.Event()
        self.daemon = True
        
        # Detection state
        self.frame_count = 0
        self.event_count = 0
        self.last_face_time = time.time()
        self.last_focus_time = time.time()
        self.last_object_check = 0
        self.drowsy_frame_count = 0
        
        # Object detection tracking
        self.phone_detected_frames = deque(maxlen=30)  # Last 1 second
        self.book_detected_frames = deque(maxlen=30)
        
        # Frame history for temporal analysis
        self.face_history = deque(maxlen=30)  # Last 1 second @ 30fps
        self.focus_history = deque(maxlen=90)  # Last 3 seconds @ 30fps
        
        # Initialize MediaPipe components
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_detection = mp.solutions.face_detection
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_drawing = mp.solutions.drawing_utils
            
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.5
            )
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=2,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            # Fallback to OpenCV Haar Cascades
            if CV2_AVAILABLE:
                self.face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                self.eye_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_eye.xml'
                )
        
        # Initialize YOLO model
        self.yolo_model = None
        if YOLO_AVAILABLE:
            try:
                logger.info(f"🔄 Loading YOLO model: {DETECTION_CONFIG['yolo_model']}")
                self.yolo_model = YOLO(DETECTION_CONFIG['yolo_model'])
                logger.info("✅ YOLO model loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load YOLO model: {e}")
                YOLO_AVAILABLE = False
        
        # Create detection session
        self.session = DetectionSession.objects.create(
            interview=interview,
            status='active'
        )
        
        logger.info(f"🔍 Detection thread initialized for interview {interview.id}")
    
    def run(self):
        """Main detection loop"""
        logger.info(f"🎬 Starting real-time detection for interview {self.interview.id}")
        
        # Open camera
        cap = cv2.VideoCapture(self.camera_index) if CV2_AVAILABLE else None
        
        if cap and not cap.isOpened():
            logger.error("❌ Failed to open camera")
            self._mark_session_error("Failed to open camera")
            return
        
        if cap:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, DETECTION_CONFIG['frame_width'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DETECTION_CONFIG['frame_height'])
            cap.set(cv2.CAP_PROP_FPS, DETECTION_CONFIG['fps'])
        
        start_time = time.time()
        end_time = start_time + (self.duration_minutes * 60)
        
        try:
            while not self.stop_event.is_set() and time.time() < end_time:
                if not CV2_AVAILABLE:
                    # Fallback to simulation
                    self._run_simulation_mode()
                    time.sleep(0.1)
                    continue
                
                ret, frame = cap.read()
                if not ret:
                    logger.warning("⚠️ Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                self.frame_count += 1
                current_time = time.time()
                
                # Convert to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Run detection pipeline
                self._detect_faces(rgb_frame, frame)
                self._detect_focus(rgb_frame, frame)
                self._detect_drowsiness(rgb_frame, frame)
                
                # Run YOLO detection every N seconds (expensive operation)
                if current_time - self.last_object_check >= DETECTION_CONFIG['object_check_interval']:
                    self._detect_objects_yolo(frame)
                    self.last_object_check = current_time
                
                # Update session statistics
                if self.frame_count % 30 == 0:  # Every second
                    self._update_session_stats()
                
                # Control frame rate
                time.sleep(1.0 / DETECTION_CONFIG['fps'])
            
            # Clean shutdown
            if cap:
                cap.release()
            
            self.session.status = 'stopped'
            self.session.ended_at = timezone.now()
            self.session.save()
            
            logger.info(f"✅ Detection completed for interview {self.interview.id}")
            logger.info(f"📊 Processed {self.frame_count} frames, logged {self.event_count} events")
            
        except Exception as e:
            logger.error(f"❌ Error in detection thread: {e}", exc_info=True)
            self._mark_session_error(str(e))
        finally:
            if cap:
                cap.release()
            if MEDIAPIPE_AVAILABLE:
                self.face_detection.close()
                self.face_mesh.close()
    
    def _detect_faces(self, rgb_frame, bgr_frame):
        """Detect faces and count them"""
        try:
            current_time = time.time()
            
            if MEDIAPIPE_AVAILABLE:
                results = self.face_detection.process(rgb_frame)
                
                if results.detections:
                    num_faces = len(results.detections)
                    self.face_history.append(num_faces)
                    self.last_face_time = current_time
                    
                    # Multiple faces detected
                    if num_faces > 1:
                        avg_faces = sum(self.face_history) / len(self.face_history)
                        if avg_faces > 1.5:  # Consistent multiple faces
                            self._log_event(
                                'multiple_faces',
                                f'Multiple faces detected: {num_faces} faces in frame',
                                0.85,
                                bgr_frame
                            )
                else:
                    self.face_history.append(0)
                    
                    # No face detected for too long
                    no_face_duration = current_time - self.last_face_time
                    if no_face_duration > DETECTION_CONFIG['no_face_threshold']:
                        self._log_event(
                            'no_face',
                            f'No face detected for {no_face_duration:.1f} seconds',
                            0.90,
                            bgr_frame
                        )
                        self.last_face_time = current_time  # Reset to avoid spam
            
            else:
                # Fallback to OpenCV Haar Cascades
                gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                num_faces = len(faces)
                self.face_history.append(num_faces)
                
                if num_faces == 0:
                    no_face_duration = current_time - self.last_face_time
                    if no_face_duration > DETECTION_CONFIG['no_face_threshold']:
                        self._log_event(
                            'no_face',
                            f'No face detected for {no_face_duration:.1f} seconds',
                            0.80,
                            bgr_frame
                        )
                        self.last_face_time = current_time
                elif num_faces > 1:
                    self._log_event(
                        'multiple_faces',
                        f'Multiple faces detected: {num_faces} faces',
                        0.75,
                        bgr_frame
                    )
                else:
                    self.last_face_time = current_time
        
        except Exception as e:
            logger.error(f"Face detection error: {e}")
    
    def _detect_focus(self, rgb_frame, bgr_frame):
        """Detect if candidate is looking at screen using head pose estimation"""
        try:
            if not MEDIAPIPE_AVAILABLE:
                return
            
            results = self.face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # Get key facial landmarks for head pose
                    landmarks = face_landmarks.landmark
                    
                    # Nose tip (1), Chin (152), Left eye (33), Right eye (263)
                    nose = landmarks[1]
                    chin = landmarks[152]
                    left_eye = landmarks[33]
                    right_eye = landmarks[263]
                    
                    # Calculate head orientation
                    h, w = rgb_frame.shape[:2]
                    
                    # Horizontal deviation (left/right)
                    eye_center_x = (left_eye.x + right_eye.x) / 2
                    nose_x = nose.x
                    horizontal_deviation = abs(nose_x - eye_center_x) * w
                    
                    # Vertical deviation (up/down)
                    vertical_deviation = abs(nose.y - chin.y) * h
                    
                    # Check if looking away
                    looking_away = (
                        horizontal_deviation > 50 or  # 50 pixels deviation
                        vertical_deviation < 80  # Head tilted significantly
                    )
                    
                    self.focus_history.append(1 if not looking_away else 0)
                    
                    # Check focus over time window
                    if len(self.focus_history) >= 60:  # 2 seconds
                        focus_ratio = sum(self.focus_history) / len(self.focus_history)
                        
                        if focus_ratio < 0.3:  # Less than 30% focused
                            focus_lost_duration = time.time() - self.last_focus_time
                            if focus_lost_duration > DETECTION_CONFIG['focus_lost_threshold']:
                                self._log_event(
                                    'focus_lost',
                                    f'Candidate looking away from screen (focus ratio: {focus_ratio:.2%})',
                                    0.75 + (1 - focus_ratio) * 0.2,
                                    bgr_frame
                                )
                                self.last_focus_time = time.time()
                        else:
                            self.last_focus_time = time.time()
            
        except Exception as e:
            logger.error(f"Focus detection error: {e}")
    
    def _detect_drowsiness(self, rgb_frame, bgr_frame):
        """Detect drowsiness using Eye Aspect Ratio (EAR)"""
        try:
            if not MEDIAPIPE_AVAILABLE:
                return
            
            results = self.face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # Eye landmarks (MediaPipe Face Mesh)
                    left_eye_indices = [33, 160, 158, 133, 153, 144]
                    right_eye_indices = [362, 385, 387, 263, 373, 380]
                    
                    landmarks = face_landmarks.landmark
                    h, w = rgb_frame.shape[:2]
                    
                    # Calculate EAR for both eyes
                    left_ear = self._calculate_ear(landmarks, left_eye_indices, w, h)
                    right_ear = self._calculate_ear(landmarks, right_eye_indices, w, h)
                    
                    avg_ear = (left_ear + right_ear) / 2
                    
                    # Check if eyes are closed
                    if avg_ear < DETECTION_CONFIG['ear_threshold']:
                        self.drowsy_frame_count += 1
                        
                        if self.drowsy_frame_count >= DETECTION_CONFIG['ear_consecutive_frames']:
                            self._log_event(
                                'drowsiness',
                                f'Drowsiness detected (EAR: {avg_ear:.3f}, frames: {self.drowsy_frame_count})',
                                0.80,
                                bgr_frame
                            )
                            self.drowsy_frame_count = 0  # Reset
                    else:
                        self.drowsy_frame_count = max(0, self.drowsy_frame_count - 1)
        
        except Exception as e:
            logger.error(f"Drowsiness detection error: {e}")
    
    def _calculate_ear(self, landmarks, eye_indices, w, h):
        """Calculate Eye Aspect Ratio"""
        try:
            # Get eye coordinates
            coords = []
            for idx in eye_indices:
                landmark = landmarks[idx]
                coords.append((landmark.x * w, landmark.y * h))
            
            # Calculate vertical distances
            v1 = np.linalg.norm(np.array(coords[1]) - np.array(coords[5]))
            v2 = np.linalg.norm(np.array(coords[2]) - np.array(coords[4]))
            
            # Calculate horizontal distance
            h_dist = np.linalg.norm(np.array(coords[0]) - np.array(coords[3]))
            
            # Calculate EAR
            ear = (v1 + v2) / (2.0 * h_dist)
            return ear
        except:
            return 0.3  # Default value
    
    def _detect_objects_yolo(self, frame):
        """
        Detect objects like phones, books, laptops using YOLO
        
        This is the REAL implementation using YOLOv8!
        """
        try:
            if not YOLO_AVAILABLE or self.yolo_model is None:
                return
            
            # Run YOLO inference
            results = self.yolo_model(
                frame,
                classes=DETECTION_CONFIG['yolo_target_classes'],
                conf=DETECTION_CONFIG['yolo_confidence'],
                verbose=False  # Suppress console output
            )
            
            # Process detections
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get detection details
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = COCO_CLASSES.get(class_id, f'Class {class_id}')
                    
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # Draw bounding box on frame (optional)
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, f'{class_name} {confidence:.2f}', 
                               (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.5, (0, 255, 0), 2)
                    
                    # Log specific object types
                    if class_id == 67:  # Cell phone
                        self.phone_detected_frames.append(1)
                        
                        # Only log if consistently detected
                        if sum(self.phone_detected_frames) > 15:  # More than 50% of last second
                            self._log_event(
                                'phone_detected',
                                f'Mobile phone detected in frame (confidence: {confidence:.2%})',
                                confidence,
                                frame
                            )
                            self.phone_detected_frames.clear()  # Reset to avoid spam
                    
                    elif class_id == 73:  # Book
                        self.book_detected_frames.append(1)
                        
                        if sum(self.book_detected_frames) > 15:
                            self._log_event(
                                'notes_detected',
                                f'Book/notes detected in frame (confidence: {confidence:.2%})',
                                confidence,
                                frame
                            )
                            self.book_detected_frames.clear()
                    
                    elif class_id in [63, 66, 64]:  # Laptop, keyboard, mouse
                        # These are common in interviews, only log if suspicious placement
                        self._log_event(
                            'device_detected',
                            f'{class_name} detected (confidence: {confidence:.2%})',
                            confidence * 0.6,  # Lower confidence - may be legitimate
                            frame
                        )
            
            # Clear buffers if nothing detected
            if len(results[0].boxes) == 0:
                if self.phone_detected_frames:
                    self.phone_detected_frames.append(0)
                if self.book_detected_frames:
                    self.book_detected_frames.append(0)
        
        except Exception as e:
            logger.error(f"YOLO object detection error: {e}")
    
    def _log_event(self, event_type, description, confidence, frame=None):
        """Log detection event to database with optional screenshot"""
        try:
            # Create event log
            event = EventLog.objects.create(
                interview=self.interview,
                event_type=event_type,
                description=description,
                confidence_score=confidence,
                frame_number=self.frame_count
            )
            
            # Save screenshot if enabled and frame provided
            if DETECTION_CONFIG['screenshot_on_violation'] and frame is not None:
                try:
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    # Save to model
                    filename = f"event_{event.id}_{event_type}_{self.frame_count}.jpg"
                    event.screenshot.save(
                        filename,
                        ContentFile(buffer.tobytes()),
                        save=True
                    )
                except Exception as e:
                    logger.error(f"Failed to save screenshot: {e}")
            
            self.event_count += 1
            logger.info(f"📝 Logged: {event_type} - {description} (confidence: {confidence:.2%})")
            
        except Exception as e:
            logger.error(f"❌ Error logging event: {e}")
    
    def _update_session_stats(self):
        """Update session statistics"""
        try:
            self.session.total_frames_processed = self.frame_count
            self.session.total_events_logged = self.event_count
            self.session.save(update_fields=['total_frames_processed', 'total_events_logged'])
        except Exception as e:
            logger.error(f"Error updating session stats: {e}")
    
    def _mark_session_error(self, error_message):
        """Mark session as error"""
        self.session.status = 'error'
        self.session.error_message = error_message
        self.session.ended_at = timezone.now()
        self.session.save()
    
    def _run_simulation_mode(self):
        """Fallback simulation when CV libraries unavailable"""
        self.frame_count += 1
        simulation_cycle = self.frame_count
        
        # Simulate events periodically
        if simulation_cycle % 300 == 0:  # Every 30 seconds
            self._log_event(
                'focus_lost',
                'Simulated: Candidate looked away from screen',
                0.85,
                None
            )
        
        if simulation_cycle % 500 == 0:  # Every 50 seconds
            self._log_event(
                'no_face',
                'Simulated: No face detected in frame',
                0.92,
                None
            )
        
        if simulation_cycle % 700 == 0:  # Every 70 seconds
            self._log_event(
                'phone_detected',
                'Simulated: Phone detected in frame',
                0.88,
                None
            )
        
        self._update_session_stats()
    
    def stop(self):
        """Stop the detection thread"""
        logger.info(f"🛑 Stopping detection thread for interview {self.interview.id}")
        self.stop_event.set()


# ============================================================================
# PUBLIC API FUNCTIONS
# ============================================================================

def start_detection(interview, duration_minutes=30, camera_index=0):
    """
    Start real-time detection for an interview
    
    Args:
        interview: Interview instance
        duration_minutes: Detection duration in minutes
        camera_index: Camera device index (0 for default)
    
    Returns:
        bool: True if started successfully
    """
    interview_id = interview.id
    
    # Stop any existing detection
    stop_detection(interview_id)
    
    # Create and start new thread
    thread = DetectionThread(interview, duration_minutes, camera_index)
    thread.start()
    
    # Store in global dictionary
    active_detection_threads[interview_id] = thread
    
    logger.info(f"✅ Detection thread started for interview {interview_id}")
    return True


def stop_detection(interview_id):
    """
    Stop detection for an interview
    
    Args:
        interview_id: Interview ID
    
    Returns:
        bool: True if stopped successfully
    """
    logger.info(f"🛑 Attempting to stop detection for interview {interview_id}")
    
    if interview_id in active_detection_threads:
        thread = active_detection_threads[interview_id]
        thread.stop()
        thread.join(timeout=5)  # Wait up to 5 seconds
        del active_detection_threads[interview_id]
        logger.info(f"✅ Detection stopped successfully for interview {interview_id}")
        return True
    else:
        logger.info(f"ℹ️ No active detection found for interview {interview_id}")
        return False


def is_detection_active(interview_id):
    """Check if detection is active for an interview"""
    active = interview_id in active_detection_threads and active_detection_threads[interview_id].is_alive()
    return active


def get_active_detection_count():
    """Get count of active detection threads"""
    active_count = sum(1 for thread in active_detection_threads.values() if thread.is_alive())
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
        logger.error(f"❌ Error getting detection summary: {e}")
        return {}


def log_event(interview, event_type, description="", confidence_score=0.0):
    """Manual event logging"""
    try:
        EventLog.objects.create(
            interview=interview,
            event_type=event_type,
            description=description,
            confidence_score=confidence_score
        )
        return True
    except Exception as e:
        logger.error(f"❌ Error logging event: {e}")
        return False


def cleanup_inactive_threads():
    """Remove inactive threads from tracking dictionary"""
    inactive_ids = [
        interview_id for interview_id, thread in active_detection_threads.items()
        if not thread.is_alive()
    ]
    
    for interview_id in inactive_ids:
        del active_detection_threads[interview_id]
        logger.info(f"🧹 Cleaned up inactive thread for interview {interview_id}")
    
    return len(inactive_ids)


def analyze_video_file(video_file):
    """
    Analyze uploaded video file for violations
    
    Args:
        video_file: VideoRecording instance
    
    Returns:
        dict: Analysis results
    """
    try:
        logger.info(f"📹 Analyzing video file: {video_file.video_file.name}")
        
        if not CV2_AVAILABLE:
            return {
                'status': 'failed',
                'error': 'OpenCV not available'
            }
        
        # Open video file
        cap = cv2.VideoCapture(video_file.video_file.path)
        
        if not cap.isOpened():
            return {
                'status': 'failed',
                'error': 'Failed to open video file'
            }
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Process every Nth frame to speed up analysis
        frame_skip = max(1, int(fps / 2))  # Process 2 frames per second
        
        events_detected = 0
        frames_analyzed = 0
        
        # Load YOLO model for video analysis (create new instance)
        yolo_model = None
        if YOLO_AVAILABLE:
            try:
                yolo_model = YOLO(DETECTION_CONFIG['yolo_model'])
                logger.info("📦 YOLO model loaded for video analysis")
            except Exception as e:
                logger.warning(f"⚠️ Could not load YOLO for video analysis: {e}")
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Skip frames
            if frame_idx % frame_skip != 0:
                frame_idx += 1
                continue
            
            frames_analyzed += 1
            
            # Run YOLO detection
            if yolo_model is not None:  # Changed from YOLO_AVAILABLE and self.yolo_model
                results = yolo_model(  # Changed from self.yolo_model
                    frame,
                    classes=DETECTION_CONFIG['yolo_target_classes'], 
                    conf=0.6, 
                    verbose=False
                )
                for result in results:
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        
                        if class_id == 67:
                            log_event(video_file.interview, 'phone_detected', 
                                    f'Phone detected at frame {frame_idx}', confidence)
                            events_detected += 1
                        elif class_id == 73:
                            log_event(video_file.interview, 'notes_detected',
                                    f'Book detected at frame {frame_idx}', confidence)
                            events_detected += 1
            
            frame_idx += 1
            
            # Update progress
            if frames_analyzed % 100 == 0:
                progress = (frame_idx / total_frames) * 100
                logger.info(f"Progress: {progress:.1f}% ({frames_analyzed} frames analyzed)")
        
        cap.release()
        
        # Update video recording status
        video_file.analyzed = True
        video_file.analysis_completed_at = timezone.now()
        video_file.save()
        
        logger.info(f"✅ Video analysis completed: {frames_analyzed} frames, {events_detected} events")
        
        return {
            'status': 'completed',
            'frames_analyzed': frames_analyzed,
            'events_detected': events_detected,
            'total_frames': total_frames,
            'message': f'Analysis completed successfully'
        }
        
    except Exception as e:
        logger.error(f"❌ Video analysis failed: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


def configure_detection(config_dict):
    """
    Update detection configuration
    
    Args:
        config_dict: Dictionary with configuration parameters
    """
    global DETECTION_CONFIG
    DETECTION_CONFIG.update(config_dict)
    logger.info(f"🔧 Detection configuration updated: {config_dict}")


def get_detection_config():
    """Get current detection configuration"""
    return DETECTION_CONFIG.copy()
