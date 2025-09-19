// Detection JavaScript for Proctoring System

class DetectionSystem {
    constructor() {
        this.isActive = false;
        this.events = [];
        this.intervalId = null;
        this.websocket = null;
        this.initializeDetection();
    }

    initializeDetection() {
        console.log('Detection system initialized');
        this.setupWebcam();
        this.setupEventListeners();
    }

    setupWebcam() {
        const videoElement = document.getElementById('videoElement');
        if (videoElement) {
            navigator.mediaDevices.getUserMedia({ video: true, audio: true })
                .then(stream => {
                    videoElement.srcObject = stream;
                    console.log('Webcam access granted');
                })
                .catch(err => {
                    console.error('Error accessing webcam:', err);
                    this.showAlert('Error accessing camera/microphone. Please check permissions.', 'danger');
                });
        }
    }

    setupEventListeners() {
        // Listen for detection status updates
        document.addEventListener('DOMContentLoaded', () => {
            this.startDetectionSimulation();
        });
    }

    startDetectionSimulation() {
        // Simulate detection events for demo purposes
        this.intervalId = setInterval(() => {
            this.simulateDetectionEvent();
        }, 3000);
    }

    simulateDetectionEvent() {
        const events = [
            { type: 'focus_maintained', message: 'Focus maintained', severity: 'success' },
            { type: 'face_detected', message: 'Face detected', severity: 'success' },
            { type: 'no_suspicious_activity', message: 'No suspicious activity', severity: 'success' },
            { type: 'good_posture', message: 'Good posture detected', severity: 'success' },
            { type: 'focus_lost', message: 'Focus lost detected', severity: 'warning' },
            { type: 'multiple_faces', message: 'Multiple faces detected', severity: 'danger' },
            { type: 'phone_detected', message: 'Phone detected', severity: 'danger' },
            { type: 'notes_detected', message: 'Notes detected', severity: 'danger' }
        ];

        // 90% chance of positive events, 10% chance of negative events
        const randomEvent = Math.random() < 0.9 
            ? events.slice(0, 4)[Math.floor(Math.random() * 4)]
            : events.slice(4)[Math.floor(Math.random() * 4)];

        this.logEvent(randomEvent);
    }

    logEvent(event) {
        this.events.unshift(event);
        
        // Keep only last 10 events
        if (this.events.length > 10) {
            this.events = this.events.slice(0, 10);
        }

        this.updateDetectionDisplay();
        this.updateDetectionStatus(event);
    }

    updateDetectionDisplay() {
        const detectionEvents = document.getElementById('detectionEvents');
        if (!detectionEvents) return;

        detectionEvents.innerHTML = '';
        
        this.events.forEach(event => {
            const eventDiv = document.createElement('div');
            eventDiv.className = `alert alert-${event.severity} alert-sm mb-2`;
            eventDiv.innerHTML = `
                <i class="fas fa-${this.getEventIcon(event.type)}"></i> 
                ${event.message}
                <small class="float-end">${new Date().toLocaleTimeString()}</small>
            `;
            detectionEvents.appendChild(eventDiv);
        });
    }

    updateDetectionStatus(event) {
        const statusElement = document.getElementById('detectionStatus');
        if (!statusElement) return;

        const statusIcon = statusElement.querySelector('i');
        const statusText = statusElement.querySelector('span') || statusElement;

        if (event.severity === 'danger') {
            statusIcon.className = 'fas fa-circle text-danger';
            statusText.textContent = 'Detection Alert';
            statusElement.style.background = 'rgba(220, 53, 69, 0.8)';
        } else if (event.severity === 'warning') {
            statusIcon.className = 'fas fa-circle text-warning';
            statusText.textContent = 'Detection Warning';
            statusElement.style.background = 'rgba(255, 193, 7, 0.8)';
        } else {
            statusIcon.className = 'fas fa-circle text-success';
            statusText.textContent = 'Detection Active';
            statusElement.style.background = 'rgba(0, 0, 0, 0.8)';
        }
    }

    getEventIcon(eventType) {
        const iconMap = {
            'focus_maintained': 'check-circle',
            'face_detected': 'user-check',
            'no_suspicious_activity': 'shield-check',
            'good_posture': 'user-tie',
            'focus_lost': 'exclamation-triangle',
            'multiple_faces': 'users',
            'phone_detected': 'mobile-alt',
            'notes_detected': 'sticky-note'
        };
        return iconMap[eventType] || 'info-circle';
    }

    showAlert(message, type = 'info') {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert at the top of the main content
        const main = document.querySelector('main');
        if (main) {
            main.insertBefore(alertDiv, main.firstChild);
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    startDetection(interviewId) {
        this.isActive = true;
        console.log(`Starting detection for interview ${interviewId}`);
        
        // In a real implementation, this would connect to a WebSocket
        // or start a background detection process
        this.showAlert('Detection started successfully!', 'success');
    }

    stopDetection() {
        this.isActive = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        console.log('Detection stopped');
        this.showAlert('Detection stopped.', 'info');
    }

    getDetectionSummary() {
        return {
            totalEvents: this.events.length,
            focusLost: this.events.filter(e => e.type === 'focus_lost').length,
            suspiciousEvents: this.events.filter(e => e.severity === 'danger').length,
            warnings: this.events.filter(e => e.severity === 'warning').length
        };
    }
}

// Real-time detection updates
class RealTimeDetection {
    constructor(interviewId) {
        this.interviewId = interviewId;
        this.setupWebSocket();
        this.startPolling();
    }

    setupWebSocket() {
        // In a real implementation, this would connect to a WebSocket server
        // for real-time detection updates
        console.log('WebSocket connection would be established here');
    }

    startPolling() {
        // Poll for detection status updates every 2 seconds
        setInterval(() => {
            this.fetchDetectionStatus();
        }, 2000);
    }

    async fetchDetectionStatus() {
        try {
            const response = await fetch(`/interviews/${this.interviewId}/detection-status/`);
            const data = await response.json();
            
            if (data.recent_events) {
                this.updateEventsDisplay(data.recent_events);
            }
        } catch (error) {
            console.error('Error fetching detection status:', error);
        }
    }

    updateEventsDisplay(events) {
        const detectionEvents = document.getElementById('detectionEvents');
        if (!detectionEvents) return;

        detectionEvents.innerHTML = '';
        
        events.forEach(event => {
            const eventDiv = document.createElement('div');
            eventDiv.className = `alert alert-${this.getSeverityClass(event.event_type)} alert-sm mb-2`;
            eventDiv.innerHTML = `
                <i class="fas fa-${this.getEventIcon(event.event_type)}"></i> 
                ${event.event_type.replace('_', ' ').toUpperCase()}
                <small class="float-end">${new Date(event.timestamp).toLocaleTimeString()}</small>
            `;
            detectionEvents.appendChild(eventDiv);
        });
    }

    getSeverityClass(eventType) {
        const severityMap = {
            'focus_lost': 'warning',
            'no_face': 'warning',
            'multiple_faces': 'danger',
            'phone_detected': 'danger',
            'notes_detected': 'danger',
            'device_detected': 'danger',
            'drowsiness': 'warning',
            'audio_anomaly': 'warning'
        };
        return severityMap[eventType] || 'info';
    }

    getEventIcon(eventType) {
        const iconMap = {
            'focus_lost': 'exclamation-triangle',
            'no_face': 'user-slash',
            'multiple_faces': 'users',
            'phone_detected': 'mobile-alt',
            'notes_detected': 'sticky-note',
            'device_detected': 'laptop',
            'drowsiness': 'bed',
            'audio_anomaly': 'volume-mute'
        };
        return iconMap[eventType] || 'info-circle';
    }
}

// Initialize detection system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the main detection system
    window.detectionSystem = new DetectionSystem();
    
    // Check if we're on an interview page and initialize real-time detection
    const path = window.location.pathname;
    const interviewMatch = path.match(/\/interviews\/(\d+)\//);
    if (interviewMatch) {
        const interviewId = interviewMatch[1];
        window.realTimeDetection = new RealTimeDetection(interviewId);
    }
});

// Utility functions
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

function showNotification(message, type = 'info') {
    // Create a toast notification
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // Add to toast container or create one
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    // Show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}
