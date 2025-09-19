from django import forms
from .models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['candidate_name', 'focus_loss_count', 'suspicious_events', 'integrity_score']
        widgets = {
            'candidate_name': forms.TextInput(attrs={'class': 'form-control'}),
            'focus_loss_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'suspicious_events': forms.NumberInput(attrs={'class': 'form-control'}),
            'integrity_score': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
        }
