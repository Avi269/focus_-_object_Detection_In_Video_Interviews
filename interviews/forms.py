# interviews/forms.py
from django import forms
from .models import Interview, VideoRecording

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['candidate', 'interviewer', 'title', 'description', 'scheduled_time', 'duration']
        widgets = {
            'scheduled_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'description': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
            'title': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Interview Session'}
            ),
            'duration': forms.NumberInput(
                attrs={'class': 'form-control', 'placeholder': 'Duration in minutes'}
            )
        }

class VideoRecordingForm(forms.ModelForm):
    class Meta:
        model = VideoRecording
        fields = ['video_file']
        widgets = {
            'video_file': forms.FileInput(
                attrs={'class': 'form-control', 'accept': 'video/*'}
            )
        }
