# interviews/forms.py
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Interview, VideoRecording

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['candidate', 'interviewer', 'title', 'description', 'scheduled_time', 'duration']
        widgets = {
            'scheduled_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local', 
                    'class': 'form-control',
                    'min': timezone.now().strftime('%Y-%m-%dT%H:%M')  # Prevent past dates
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 4, 
                    'class': 'form-control',
                    'placeholder': 'Enter interview description, requirements, or special instructions...'
                }
            ),
            'title': forms.TextInput(
                attrs={
                    'class': 'form-control', 
                    'placeholder': 'e.g., Technical Interview - Software Engineer',
                    'required': True
                }
            ),
            'duration': forms.NumberInput(
                attrs={
                    'class': 'form-control', 
                    'placeholder': 'Duration in minutes (e.g., 60)',
                    'min': '5',
                    'max': '480',
                    'step': '5'
                }
            ),
            'candidate': forms.Select(attrs={'class': 'form-control'}),
            'interviewer': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter candidate choices to only show users with 'candidate' role
        from accounts.models import User
        self.fields['candidate'].queryset = User.objects.filter(role='candidate', is_active=True)
        self.fields['candidate'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.username})"
        
        # Filter interviewer choices to only show users with 'interviewer' or 'admin' role
        self.fields['interviewer'].queryset = User.objects.filter(
            role__in=['interviewer', 'admin'], 
            is_active=True
        )
        self.fields['interviewer'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.username})"
        
        # Add help text
        self.fields['title'].help_text = 'A descriptive title for the interview session.'
        self.fields['scheduled_time'].help_text = 'Select the date and time when the interview should start.'
        self.fields['duration'].help_text = 'Expected duration in minutes (5-480 minutes).'
        self.fields['candidate'].help_text = 'Select the candidate to be interviewed.'
        self.fields['interviewer'].help_text = 'Select the interviewer who will conduct the interview.'
    
    def clean_scheduled_time(self):
        """Ensure scheduled time is in the future"""
        scheduled_time = self.cleaned_data.get('scheduled_time')
        
        if scheduled_time:
            if scheduled_time <= timezone.now():
                raise ValidationError('Scheduled time must be in the future.')
            
            # Check if it's too far in the future (e.g., more than 1 year)
            one_year_later = timezone.now() + timezone.timedelta(days=365)
            if scheduled_time > one_year_later:
                raise ValidationError('Scheduled time cannot be more than 1 year in the future.')
        
        return scheduled_time
    
    def clean_duration(self):
        """Validate duration is reasonable"""
        duration = self.cleaned_data.get('duration')
        
        if duration:
            if duration < 5:
                raise ValidationError('Duration must be at least 5 minutes.')
            if duration > 480:  # 8 hours
                raise ValidationError('Duration cannot exceed 8 hours (480 minutes).')
        
        return duration
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        candidate = cleaned_data.get('candidate')
        interviewer = cleaned_data.get('interviewer')
        
        # Ensure candidate and interviewer are different
        if candidate and interviewer and candidate == interviewer:
            raise ValidationError('Candidate and interviewer must be different users.')
        
        # Validate roles
        if candidate and candidate.role != 'candidate':
            raise ValidationError({'candidate': 'Selected user must have the "candidate" role.'})
        
        if interviewer and interviewer.role not in ['interviewer', 'admin']:
            raise ValidationError({'interviewer': 'Selected user must have "interviewer" or "admin" role.'})
        
        return cleaned_data


class VideoRecordingForm(forms.ModelForm):
    class Meta:
        model = VideoRecording
        fields = ['video_file']
        widgets = {
            'video_file': forms.FileInput(
                attrs={
                    'class': 'form-control', 
                    'accept': 'video/mp4,video/webm,video/avi,video/mov'
                }
            )
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_file'].help_text = 'Upload interview recording (MP4, WebM, AVI, or MOV format). Max size: 500MB.'
    
    def clean_video_file(self):
        """Validate video file"""
        video_file = self.cleaned_data.get('video_file')
        
        if video_file:
            # Check file size (500MB max)
            max_size = 500 * 1024 * 1024  # 500 MB
            if video_file.size > max_size:
                raise ValidationError(f'File size cannot exceed 500MB. Current size: {video_file.size / (1024*1024):.2f}MB')
            
            # Check file extension
            allowed_extensions = ['mp4', 'webm', 'avi', 'mov', 'mkv']
            file_extension = video_file.name.split('.')[-1].lower()
            
            if file_extension not in allowed_extensions:
                raise ValidationError(
                    f'Invalid file format. Allowed formats: {", ".join(allowed_extensions)}'
                )
        
        return video_file


class InterviewRescheduleForm(forms.ModelForm):
    """Form for rescheduling interviews"""
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Provide a reason for rescheduling...'
        }),
        help_text='Explain why the interview needs to be rescheduled.'
    )
    
    class Meta:
        model = Interview
        fields = ['scheduled_time', 'duration']
        widgets = {
            'scheduled_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'duration': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '5',
                    'max': '480',
                    'step': '5'
                }
            ),
        }
    
    def clean_scheduled_time(self):
        """Ensure new scheduled time is in the future"""
        scheduled_time = self.cleaned_data.get('scheduled_time')
        
        if scheduled_time:
            if scheduled_time <= timezone.now():
                raise ValidationError('New scheduled time must be in the future.')
        
        return scheduled_time
    
    def clean_reason(self):
        """Validate reason text"""
        reason = self.cleaned_data.get('reason', '').strip()
        
        if len(reason) < 10:
            raise ValidationError('Reason must be at least 10 characters.')
        
        return reason
