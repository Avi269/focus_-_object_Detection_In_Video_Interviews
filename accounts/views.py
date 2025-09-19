from datetime import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import UserRegistrationForm, UserProfileForm
from .models import User
from interviews.models import Interview
import json

def register_view(request):
    """User registration view with role-based redirect"""
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, f'✅ Registration successful! Welcome, {user.get_full_name() or user.username}!')
                
                # Redirect based on user role
                if user.role == 'candidate':
                    return redirect('interviews:candidate_dashboard')
                elif user.role == 'interviewer':
                    return redirect('interviews:interview_list')
                elif user.role == 'admin':
                    return redirect('admin:index')
                else:
                    return redirect('accounts:profile')
                    
            except Exception as e:
                messages.error(request, f'❌ Registration failed: {str(e)}')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CustomLoginView(LoginView):
    """Custom login view with role-based redirect"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redirect based on user role after successful login"""
        user = self.request.user
        
        # Check for next parameter first
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
            
        # Role-based redirect
        if hasattr(user, 'role'):
            if user.role == 'candidate':
                return reverse('interviews:candidate_dashboard')
            elif user.role == 'interviewer':
                return reverse('interviews:interview_list')
            elif user.role == 'admin':
                return reverse('admin:index')
        
        # Default fallback
        return reverse('accounts:profile')
    
    def form_valid(self, form):
        """Add success message on login"""
        response = super().form_valid(form)
        user = form.get_user()
        messages.success(
            self.request, 
            f'✅ Welcome back, {user.get_full_name() or user.username}!'
        )
        return response
    
    def form_invalid(self, form):
        """Add error message on failed login"""
        messages.error(self.request, '❌ Invalid username or password. Please try again.')
        return super().form_invalid(form)

class CustomLogoutView(LogoutView):
    """Custom logout view with confirmation message"""
    next_page = reverse_lazy('accounts:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Add logout message"""
        if request.user.is_authenticated:
            messages.info(request, f'👋 You have been logged out successfully. See you soon!')
        return super().dispatch(request, *args, **kwargs)

@login_required
def profile_view(request):
    """Enhanced user profile view"""
    user = request.user
    
    # Get user's interview statistics
    if user.role == 'candidate':
        interviews = user.candidate_interviews.all()
        upcoming_interviews = interviews.filter(status='scheduled').order_by('scheduled_time')[:3]
        completed_interviews = interviews.filter(status='completed').order_by('-end_time')[:5]
        ongoing_interviews = interviews.filter(status='ongoing')
        
        stats = {
            'total_interviews': interviews.count(),
            'completed': interviews.filter(status='completed').count(),
            'upcoming': interviews.filter(status='scheduled').count(),
            'ongoing': interviews.filter(status='ongoing').count(),
        }
        
    elif user.role == 'interviewer':
        interviews = user.interviewer_interviews.all()
        upcoming_interviews = interviews.filter(status='scheduled').order_by('scheduled_time')[:3]
        completed_interviews = interviews.filter(status='completed').order_by('-end_time')[:5]
        ongoing_interviews = interviews.filter(status='ongoing')
        
        stats = {
            'total_interviews': interviews.count(),
            'completed': interviews.filter(status='completed').count(),
            'upcoming': interviews.filter(status='scheduled').count(),
            'ongoing': interviews.filter(status='ongoing').count(),
        }
        
    else:  # admin or other roles
        interviews = Interview.objects.all()
        upcoming_interviews = interviews.filter(status='scheduled').order_by('scheduled_time')[:3]
        completed_interviews = interviews.filter(status='completed').order_by('-end_time')[:5]
        ongoing_interviews = interviews.filter(status='ongoing')
        
        stats = {
            'total_interviews': interviews.count(),
            'completed': interviews.filter(status='completed').count(),
            'upcoming': interviews.filter(status='scheduled').count(),
            'ongoing': interviews.filter(status='ongoing').count(),
        }
    
    context = {
        'user': user,
        'upcoming_interviews': upcoming_interviews,
        'completed_interviews': completed_interviews,
        'ongoing_interviews': ongoing_interviews,
        'stats': stats,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def edit_profile_view(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Profile updated successfully!')
                return redirect('accounts:profile')
            except Exception as e:
                messages.error(request, f'❌ Failed to update profile: {str(e)}')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})

@login_required
def change_password_view(request):
    """Change user password"""
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            try:
                user = form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, '✅ Password changed successfully!')
                return redirect('accounts:profile')
            except Exception as e:
                messages.error(request, f'❌ Failed to change password: {str(e)}')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def user_activity_log(request):
    """View user activity log"""
    user = request.user
    
    # Get user's interviews as activity
    if user.role == 'candidate':
        interviews = user.candidate_interviews.all().order_by('-created_at')
    elif user.role == 'interviewer':
        interviews = user.interviewer_interviews.all().order_by('-created_at')
    else:
        from interviews.models import Interview
        interviews = Interview.objects.all().order_by('-created_at')
    
    # Simple pagination
    from django.core.paginator import Paginator
    paginator = Paginator(interviews, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'interviews': page_obj,
        'total_count': interviews.count()
    }
    
    return render(request, 'accounts/activity_log.html', context)

@login_required
@require_http_methods(["POST"])
def deactivate_account_view(request):
    """Deactivate user account"""
    # Check if user has ongoing interviews
    if request.user.role == 'candidate':
        ongoing = request.user.candidate_interviews.filter(status='ongoing').exists()
    elif request.user.role == 'interviewer':
        ongoing = request.user.interviewer_interviews.filter(status='ongoing').exists()
    else:
        ongoing = False
    
    if ongoing:
        messages.error(request, '❌ Cannot deactivate account with ongoing interviews.')
        return redirect('accounts:profile')
    
    try:
        request.user.is_active = False
        request.user.save()
        logout(request)
        messages.info(request, 'ℹ️ Your account has been deactivated.')
        return redirect('accounts:login')
    except Exception as e:
        messages.error(request, f'❌ Failed to deactivate account: {str(e)}')
        return redirect('accounts:profile')

@require_http_methods(["GET"])
def check_username_availability(request):
    """AJAX endpoint to check username availability"""
    username = request.GET.get('username', '').strip()
    
    if not username:
        return JsonResponse({'available': False, 'message': 'Username is required'})
    
    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters'})
    
    exists = User.objects.filter(username__iexact=username).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Username is available' if not exists else 'Username is already taken'
    })

@require_http_methods(["GET"])
def check_email_availability(request):
    """AJAX endpoint to check email availability"""
    email = request.GET.get('email', '').strip()
    
    if not email:
        return JsonResponse({'available': False, 'message': 'Email is required'})
    
    exists = User.objects.filter(email__iexact=email).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Email is available' if not exists else 'Email is already registered'
    })

@login_required
def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user role"""
    user = request.user
    
    if user.role == 'candidate':
        return redirect('interviews:candidate_dashboard')
    elif user.role == 'interviewer':
        return redirect('interviews:interview_list')
    elif user.role == 'admin':
        return redirect('admin:index')
    else:
        return redirect('accounts:profile')

def health_check(request):
    """Simple health check endpoint"""
    from django.utils import timezone
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'proctoring_system'
    })

def contact_view(request):
    pass

def about_view(request):
    pass
def user_management(request):
    pass
def user_detail_admin(request):
    pass
def user_detail_admin(request):
    pass
def toggle_user_active(request):
    pass
def user_statistics(request):
    pass

def export_user_data(request):
    pass

def mobile_login(request):
    pass
def mobile_profile(request):
    pass
def candidate_onboarding(request):
    pass
def candidate_guidelines(request):
    pass
def interviewer_training(request):
    pass
def interviewer_resources(request):
    pass

def system_settings(request):
    pass
def audit_log(request):
    pass

# @login_required
# def dashboard_redirect(request):
#     """Redirect to appropriate dashboard based on user role"""
#     user = request.user
    
#     if user.role == 'candidate':
#         return redirect('interviews:candidate_dashboard')
#     elif user.role == 'interviewer':
#         return redirect('interviews:interview_list')
#     elif user.role == 'admin':
#         return redirect('admin:index')
#     else:
#         return redirect('accounts:profile')

# Error handlers
def custom_404(request, exception):
    """Custom 404 error page"""
    context = {
        'error_code': '404',
        'error_title': 'Page Not Found',
        'error_message': 'The page you are looking for does not exist.',
        'show_home_link': True
    }
    return render(request, 'errors/404.html', context, status=404)

def custom_500(request):
    """Custom 500 error page"""
    context = {
        'error_code': '500',
        'error_title': 'Internal Server Error',
        'error_message': 'Something went wrong on our end. Please try again later.',
        'show_home_link': True
    }
    return render(request, 'errors/500.html', context, status=500)

def custom_403(request, exception):
    """Custom 403 error page"""
    context = {
        'error_code': '403',
        'error_title': 'Access Forbidden',
        'error_message': 'You do not have permission to access this resource.',
        'show_home_link': True,
        'show_login_link': not request.user.is_authenticated
    }
    return render(request, 'errors/403.html', context, status=403)

def custom_400(request, exception):
    """Custom 400 error page"""
    context = {
        'error_code': '400',
        'error_title': 'Bad Request',
        'error_message': 'Your request could not be processed.',
        'show_home_link': True
    }
    return render(request, 'errors/400.html', context, status=400)

# Health check endpoint
def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'proctoring_system'
    })
