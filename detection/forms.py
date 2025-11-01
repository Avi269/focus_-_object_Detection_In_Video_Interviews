from django import forms


class DetectionSettingsForm(forms.Form):
    """Form for configuring detection settings"""
    
    detection_duration = forms.IntegerField(
        initial=30,
        min_value=5,
        max_value=480,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '30'
        }),
        help_text='Duration in minutes (5-480)'
    )
    
    focus_lost_threshold = forms.IntegerField(
        initial=5,
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '5'
        }),
        help_text='Seconds before logging focus lost event (1-30)'
    )
    
    no_face_threshold = forms.IntegerField(
        initial=10,
        min_value=5,
        max_value=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '10'
        }),
        help_text='Seconds before logging no face event (5-60)'
    )
    
    enable_phone_detection = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    enable_notes_detection = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    enable_drowsiness_detection = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    confidence_threshold = forms.FloatField(
        initial=0.7,
        min_value=0.1,
        max_value=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '0.7'
        }),
        help_text='Minimum confidence for logging events (0.1-1.0)'
    )