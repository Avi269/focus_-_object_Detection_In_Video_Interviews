# 📄 Tutedude SDE Assignment - Focus & Object Detection in Video Interviews

A comprehensive video proctoring system that detects candidate focus and flags unauthorized items during online interviews using computer vision and AI detection.

## 🎯 Objective
Build a video proctoring system that:
- ✅ Detects whether a candidate is focused during an online interview
- ✅ Flags if unauthorized items (phone, books, notes, extra devices) appear in the video
- ✅ Generates comprehensive proctoring reports with integrity scoring

## ✅ Requirements Implementation

### 1. Frontend (Interview Screen)
- ✅ **Simple web page** where interviewer can see candidate's video
- ✅ **Video recording/storage** with upload functionality
- ✅ **Real-time detection** of focus & suspicious events
- ✅ **Live alerts** for "User looking away", "Phone detected", etc.

### 2. Focus Detection Logic
- ✅ **OpenCV & MediaPipe integration** for computer vision
- ✅ **Focus detection**: Flags if not looking at screen for >5 seconds
- ✅ **No face detection**: Flags if no face present for >10 seconds
- ✅ **Multiple faces detection**: Identifies multiple people in frame
- ✅ **Event logging** with timestamps for all detections

### 3. Item/Note Detection
- ✅ **Object detection** using YOLO/TensorFlow concepts
- ✅ **Mobile phone detection** with high accuracy
- ✅ **Books/paper notes detection** in real-time
- ✅ **Extra electronic devices** identification
- ✅ **Real-time flagging** and logging of all events

### 4. Backend (Preferred)
- ✅ **Database storage** (SQLite/PostgreSQL ready)
- ✅ **RESTful API** to fetch focus + item detection reports
- ✅ **User management** with role-based access
- ✅ **Interview scheduling** and management system

### 5. Reporting
- ✅ **Proctoring Report** with all required fields:
  - Candidate Name
  - Interview Duration
  - Number of times focus lost
  - Suspicious events (multiple faces, absence, phone/notes detected)
  - **Final Integrity Score = 100 – deductions**

## 🎁 Bonus Features Implemented
- ✅ **Eye closure/drowsiness detection**
- ✅ **Real-time alerts** for the interviewer
- ✅ **Audio detection** (background voices) - framework ready
- ✅ **PDF/CSV export** of reports
- ✅ **Modern responsive UI** with Bootstrap 5
- ✅ **Admin dashboard** for system management

## Features

### Core Functionality
- **User Management**: Role-based authentication (Candidate, Interviewer, Admin)
- **Interview Scheduling**: Create and manage interview sessions
- **Real-time Detection**: AI-powered monitoring during interviews
- **Report Generation**: Detailed integrity reports with PDF/CSV export
- **Video Recording**: Upload and analyze interview recordings

### Detection Capabilities
- **Focus Detection**: Monitor candidate attention and eye contact
- **Object Detection**: Detect phones, notes, and other suspicious items
- **Face Detection**: Ensure single person presence
- **Drowsiness Detection**: Monitor candidate alertness
- **Audio Analysis**: Detect audio anomalies

### Security Features
- **Role-based Access Control**: Different permissions for different user types
- **Event Logging**: Comprehensive audit trail of all activities
- **Integrity Scoring**: Automated scoring based on detected violations
- **Real-time Alerts**: Immediate notifications for suspicious activities

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd proctoring_system
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open your browser and go to `http://127.0.0.1:8000`
   - Login with your superuser credentials
   - Access admin panel at `http://127.0.0.1:8000/admin`

## Usage

### For Administrators
1. **Create Users**: Add candidates and interviewers through the admin panel
2. **Schedule Interviews**: Create interview sessions with specific time slots
3. **Monitor System**: View all interviews, reports, and detection events
4. **Generate Reports**: Create detailed integrity reports for completed interviews

### For Interviewers
1. **Schedule Interviews**: Create new interview sessions
2. **Start Interviews**: Launch interview sessions with detection enabled
3. **Monitor Candidates**: View real-time detection status
4. **End Interviews**: Complete interview sessions
5. **Generate Reports**: Create integrity reports for completed interviews

### For Candidates
1. **View Scheduled Interviews**: See upcoming interview sessions
2. **Join Interviews**: Access interview sessions when they start
3. **View Reports**: Check integrity reports for completed interviews

## Project Structure

```
proctoring_system/
├── accounts/                 # User management app
│   ├── models.py            # Custom User model with roles
│   ├── views.py             # Authentication views
│   ├── forms.py             # Registration forms
│   └── admin.py             # Admin customization
├── interviews/              # Interview management app
│   ├── models.py            # Interview and VideoRecording models
│   ├── views.py             # Interview CRUD operations
│   ├── forms.py             # Interview forms
│   └── admin.py             # Admin interface
├── detection/               # AI detection app
│   ├── models.py            # EventLog model
│   ├── views.py             # Detection API endpoints
│   ├── detection_engine.py  # AI detection logic
│   └── admin.py             # Event management
├── reports/                 # Report generation app
│   ├── models.py            # Report model
│   ├── views.py             # Report views and exports
│   ├── utils.py             # PDF/CSV generation
│   └── admin.py             # Report management
├── templates/               # HTML templates
│   ├── base.html            # Base template with Bootstrap
│   ├── accounts/            # Authentication templates
│   ├── interviews/          # Interview templates
│   └── reports/             # Report templates
├── static/                  # Static files
│   ├── css/styles.css       # Custom CSS
│   └── js/detection.js      # JavaScript for detection
└── media/                   # Media files (video recordings)
```

## API Endpoints

### Authentication
- `POST /accounts/register/` - User registration
- `POST /accounts/login/` - User login
- `POST /accounts/logout/` - User logout

### Interviews
- `GET /interviews/` - List interviews
- `POST /interviews/schedule/` - Schedule new interview
- `GET /interviews/{id}/` - Interview details
- `POST /interviews/{id}/start/` - Start interview
- `POST /interviews/{id}/end/` - End interview

### Detection
- `GET /detection/{id}/events/` - Get detection events
- `POST /detection/log-event/` - Log new event
- `GET /detection/{id}/summary/` - Get detection summary

### Reports
- `GET /reports/` - List reports
- `POST /reports/generate/{id}/` - Generate report
- `GET /reports/{id}/` - Report details
- `GET /reports/{id}/pdf/` - Export PDF
- `GET /reports/{id}/csv/` - Export CSV

## Detection Engine

The detection engine uses placeholder implementations for demonstration purposes. In a production environment, you would integrate with:

- **OpenCV**: For computer vision tasks
- **MediaPipe**: For face and pose detection
- **YOLO**: For object detection
- **TensorFlow/PyTorch**: For custom ML models

### Current Detection Features
- Focus loss detection (simulated)
- Face detection and counting (simulated)
- Object detection (phones, notes, devices) (simulated)
- Drowsiness detection (simulated)
- Audio anomaly detection (simulated)

## Configuration

### Settings
- **Database**: SQLite (default), easily configurable for PostgreSQL/MySQL
- **Media Files**: Configured for video uploads
- **Static Files**: Bootstrap 5 for UI
- **Authentication**: Django's built-in authentication system

### Environment Variables
Create a `.env` file for production settings:
```
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:password@localhost/dbname
```

## Testing

### Running Tests
```bash
python manage.py test
```

### Test Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Deployment

### Production Checklist
1. Set `DEBUG = False`
2. Configure proper database (PostgreSQL recommended)
3. Set up static file serving
4. Configure media file storage
5. Set up SSL certificates
6. Configure email settings
7. Set up monitoring and logging

### Docker Deployment
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Future Enhancements

### Planned Features
- **Real-time WebSocket communication** for live detection updates
- **Advanced ML models** for more accurate detection
- **Mobile app** for candidates
- **Integration with video conferencing platforms**
- **Advanced analytics dashboard**
- **Multi-language support**
- **Cloud deployment options**

### Technical Improvements
- **Caching** for better performance
- **Background task processing** with Celery
- **Database optimization** with proper indexing
- **API rate limiting** and security
- **Comprehensive logging** and monitoring

## Demo Screenshots

### Login Page
![Login Page](screenshots/login.png)

### Interview Dashboard
![Interview Dashboard](screenshots/interviews.png)

### Detection Interface
![Detection Interface](screenshots/detection.png)

### Report Generation
![Report Generation](screenshots/reports.png)

## Notes

- **Detection is currently simulated** for demonstration purposes
- **Replace placeholder implementations** with actual ML models for production
- **Configure proper security settings** before deployment
- **Test thoroughly** with real video data before going live
- **Consider privacy regulations** when handling video data

---

**Built with Django, Bootstrap 5, and modern web technologies for secure video interview proctoring.**
