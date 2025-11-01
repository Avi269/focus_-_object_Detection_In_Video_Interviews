from django import forms
from django.core.exceptions import ValidationError
from .models import Report


class ReportForm(forms.ModelForm):
    """Form for manually editing report data (admin use)"""
    
    class Meta:
        model = Report
        fields = [
            'candidate_name', 
            'integrity_score',
            'focus_loss_count', 
            'suspicious_events',
            'face_detection_accuracy',
            'audio_quality_score',
            'focus_lost_events',
            'no_face_events',
            'multiple_faces_events',
            'phone_detected_events',
            'notes_detected_events',
            'device_detected_events',
            'drowsiness_events',
            'audio_anomaly_events',
        ]
        widgets = {
            'candidate_name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'integrity_score': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '0', 
                'max': '100',
                'step': '1'
            }),
            'focus_loss_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'suspicious_events': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'face_detection_accuracy': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '1',
                'step': '0.01'
            }),
            'audio_quality_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '1',
                'step': '0.01'
            }),
            'focus_lost_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'no_face_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'multiple_faces_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'phone_detected_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'notes_detected_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'device_detected_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'drowsiness_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'audio_anomaly_events': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
    
    def clean_integrity_score(self):
        """Validate integrity score range"""
        score = self.cleaned_data.get('integrity_score')
        
        if score is not None:
            if score < 0 or score > 100:
                raise ValidationError('Integrity score must be between 0 and 100.')
        
        return score
    
    def clean_face_detection_accuracy(self):
        """Validate accuracy is between 0 and 1"""
        accuracy = self.cleaned_data.get('face_detection_accuracy')
        
        if accuracy is not None:
            if accuracy < 0 or accuracy > 1:
                raise ValidationError('Face detection accuracy must be between 0 and 1.')
        
        return accuracy
    
    def clean_audio_quality_score(self):
        """Validate score is between 0 and 1"""
        score = self.cleaned_data.get('audio_quality_score')
        
        if score is not None:
            if score < 0 or score > 1:
                raise ValidationError('Audio quality score must be between 0 and 1.')
        
        return score


class ReportFilterForm(forms.Form):
    """Form for filtering reports in list view"""
    
    candidate_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by candidate name...'
        })
    )
    
    min_integrity_score = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min score',
            'min': '0',
            'max': '100'
        })
    )
    
    max_integrity_score = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max score',
            'min': '0',
            'max': '100'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        """Validate filter ranges"""
        cleaned_data = super().clean()
        
        min_score = cleaned_data.get('min_integrity_score')
        max_score = cleaned_data.get('max_integrity_score')
        
        if min_score is not None and max_score is not None:
            if min_score > max_score:
                raise ValidationError('Minimum score cannot be greater than maximum score.')
        
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to:
            if date_from > date_to:
                raise ValidationError('Start date cannot be after end date.')
        
        return cleaned_data
