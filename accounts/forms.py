from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User

class UserRegistrationForm(UserCreationForm):
    """Enhanced user registration form with validation and styling"""
    
    email = forms.EmailField(
        required=True,
        help_text='We will use this email for important notifications.',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        help_text='Enter your first name.',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        help_text='Enter your last name.',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name'
        })
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        help_text='Select your role in the system.',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a unique username',
                'autocomplete': 'username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes and attributes to password fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a unique username',
            'autocomplete': 'username',
            'minlength': '3',
            'maxlength': '150'
        })
        
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        })
        
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
        
        # Add help text
        self.fields['username'].help_text = 'Username must be 3-150 characters long and unique.'
        self.fields['password1'].help_text = 'Your password should be at least 8 characters long and secure.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'

    def clean_username(self):
        """Validate username uniqueness and format"""
        username = self.cleaned_data.get('username')
        
        if not username:
            raise ValidationError('Username is required.')
        
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters long.')
        
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken. Please choose another.')
        
        # Check for invalid characters (optional)
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError('Username can only contain letters, numbers, underscores, dots, and hyphens.')
        
        return username

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        
        if not email:
            raise ValidationError('Email is required.')
        
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already registered. Please use another email or try logging in.')
        
        return email.lower()  # Store emails in lowercase

    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get('first_name', '').strip()
        
        if not first_name:
            raise ValidationError('First name is required.')
        
        if len(first_name) < 2:
            raise ValidationError('First name must be at least 2 characters long.')
        
        return first_name.title()  # Capitalize first letter

    def clean_last_name(self):
        """Validate last name"""
        last_name = self.cleaned_data.get('last_name', '').strip()
        
        if not last_name:
            raise ValidationError('Last name is required.')
        
        if len(last_name) < 2:
            raise ValidationError('Last name must be at least 2 characters long.')
        
        return last_name.title()  # Capitalize first letter

    def save(self, commit=True):
        """Save user with additional fields"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.role = self.cleaned_data['role']
        
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    """User profile edit form"""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name',
                'autocomplete': 'given-name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name',
                'autocomplete': 'family-name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
                'autocomplete': 'email'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['first_name'].help_text = 'Your first name as it should appear on certificates.'
        self.fields['last_name'].help_text = 'Your last name as it should appear on certificates.'
        self.fields['email'].help_text = 'We will use this email for important notifications.'

    def clean_email(self):
        """Validate email uniqueness (excluding current user)"""
        email = self.cleaned_data.get('email')
        
        if not email:
            raise ValidationError('Email is required.')
        
        # Check if email exists for other users
        existing_user = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).first()
        if existing_user:
            raise ValidationError('This email is already in use by another account.')
        
        return email.lower()

    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get('first_name', '').strip()
        
        if not first_name:
            raise ValidationError('First name is required.')
        
        if len(first_name) < 2:
            raise ValidationError('First name must be at least 2 characters long.')
        
        return first_name.title()

    def clean_last_name(self):
        """Validate last name"""
        last_name = self.cleaned_data.get('last_name', '').strip()
        
        if not last_name:
            raise ValidationError('Last name is required.')
        
        if len(last_name) < 2:
            raise ValidationError('Last name must be at least 2 characters long.')
        
        return last_name.title()

class ChangePasswordForm(forms.Form):
    """Custom password change form with better validation"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your current password',
            'autocomplete': 'current-password'
        }),
        help_text='Enter your current password for verification.'
    )
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your new password',
            'autocomplete': 'new-password'
        }),
        help_text='Your password should be at least 8 characters long and secure.'
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your new password',
            'autocomplete': 'new-password'
        }),
        help_text='Enter the same password as before, for verification.'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """Validate current password"""
        current_password = self.cleaned_data.get('current_password')
        
        if not self.user.check_password(current_password):
            raise ValidationError('Your current password is incorrect.')
        
        return current_password

    def clean_new_password2(self):
        """Validate password confirmation"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('The two password fields didn\'t match.')
        
        return password2

    def save(self, commit=True):
        """Save the new password"""
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        
        if commit:
            self.user.save()
        
        return self.user

class ContactForm(forms.Form):
    """Contact form for user inquiries"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter the subject of your message'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your message',
            'rows': 5
        })
    )
    
    def clean_message(self):
        """Validate message length"""
        message = self.cleaned_data.get('message', '').strip()
        
        if len(message) < 10:
            raise ValidationError('Message must be at least 10 characters long.')
        
        if len(message) > 2000:
            raise ValidationError('Message cannot exceed 2000 characters.')
        
        return message
