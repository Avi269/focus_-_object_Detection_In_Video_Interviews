import logging
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve, reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Middleware to enforce role-based access control across the application.
    
    This middleware checks user roles and restricts access to certain views
    based on predefined rules.
    """
    
    # URLs that don't require authentication
    PUBLIC_URLS = [
        'login',
        'register',
        'password_reset',
        'password_reset_done',
        'password_reset_confirm',
        'password_reset_complete',
        'health_check',
        'about',
        'contact',
    ]
    
    # URLs restricted by role
    ROLE_RESTRICTIONS = {
        'candidate': {
            'denied': [
                'schedule_interview',
                'user_management',
                'user_detail_admin',
                'toggle_user_active',
                'user_statistics',
                'export_user_data',
                'system_settings',
                'audit_log',
                'interviewer_training',
                'interviewer_resources',
            ],
            'allowed': [
                'candidate_dashboard',
                'join_interview',
                'live_interview',
                'candidate_onboarding',
                'candidate_guidelines',
                'profile',
                'profile_edit',
                'change_password',
            ],
        },
        'interviewer': {
            'denied': [
                'candidate_dashboard',
                'user_management',
                'user_detail_admin',
                'toggle_user_active',
                'user_statistics',
                'export_user_data',
                'system_settings',
                'audit_log',
            ],
            'allowed': [
                'interview_list',
                'schedule_interview',
                'start_interview',
                'end_interview',
                'interview_detail',
                'live_interview',
                'detection_dashboard',
                'interviewer_training',
                'interviewer_resources',
                'profile',
                'profile_edit',
                'change_password',
            ],
        },
        'admin': {
            'denied': [],  # Admins have access to everything
            'allowed': '*',  # Wildcard means all URLs
        },
    }
    
    def process_request(self, request):
        """
        Process incoming requests and enforce role-based access control.
        """
        # Skip middleware for static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        # Allow unauthenticated users to access public URLs
        if not request.user.is_authenticated:
            return self._handle_unauthenticated(request)
        
        # Get current URL name
        try:
            current_url = resolve(request.path_info).url_name
        except Exception as e:
            logger.warning(f"Could not resolve URL: {request.path_info} - {e}")
            return None
        
        # Skip check for public URLs
        if current_url in self.PUBLIC_URLS:
            return None
        
        # Check role-based access
        user_role = getattr(request.user, 'role', None)
        
        if not user_role:
            logger.error(f"User {request.user.username} has no role assigned")
            messages.error(request, '❌ Your account has no role assigned. Contact administrator.')
            return redirect('accounts:profile')
        
        # Admin users bypass all restrictions
        if user_role == 'admin' or request.user.is_superuser:
            return None
        
        # Check if URL is restricted for this role
        if user_role in self.ROLE_RESTRICTIONS:
            denied_urls = self.ROLE_RESTRICTIONS[user_role]['denied']
            allowed_urls = self.ROLE_RESTRICTIONS[user_role]['allowed']
            
            # If URL is explicitly denied
            if current_url in denied_urls:
                return self._handle_forbidden_access(request, user_role, current_url)
            
            # If allowed list is not wildcard, check if URL is in allowed list
            if allowed_urls != '*' and current_url not in allowed_urls:
                # Allow if no specific restriction (opt-in security model)
                pass
        
        return None
    
    def _handle_unauthenticated(self, request):
        """Handle unauthenticated user access attempts."""
        try:
            current_url = resolve(request.path_info).url_name
        except:
            current_url = None
        
        if current_url not in self.PUBLIC_URLS:
            logger.info(f"Unauthenticated access attempt to: {request.path}")
            
            # For AJAX requests, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'Authentication required',
                    'redirect': reverse('accounts:login')
                }, status=401)
            
            messages.warning(request, '⚠️ Please login to access this page.')
            return redirect(f"{reverse('accounts:login')}?next={request.path}")
        
        return None
    
    def _handle_forbidden_access(self, request, user_role, current_url):
        """Handle forbidden access attempts."""
        logger.warning(
            f"Access denied: User '{request.user.username}' (role: {user_role}) "
            f"attempted to access '{current_url}'"
        )
        
        # For AJAX requests, return JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Access denied',
                'message': 'You do not have permission to access this resource.'
            }, status=403)
        
        # For regular requests, redirect to appropriate dashboard
        messages.error(request, '❌ You do not have permission to access this page.')
        
        # Redirect based on role
        if user_role == 'candidate':
            return redirect('interviews:candidate_dashboard')
        elif user_role == 'interviewer':
            return redirect('interviews:interview_list')
        else:
            return redirect('accounts:profile')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to all responses.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (adjust based on your needs)
        if not request.path.startswith('/admin/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "font-src 'self' https://cdnjs.cloudflare.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self';"
            )
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all incoming requests (useful for debugging and auditing).
    """
    
    def process_request(self, request):
        """Log incoming request details."""
        # Skip logging for static files and health checks
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        if request.path == '/health/' or request.path.startswith('/admin/jsi18n/'):
            return None
        
        user = request.user.username if request.user.is_authenticated else 'anonymous'
        
        logger.info(
            f"REQUEST: {request.method} {request.path} | "
            f"User: {user} | "
            f"IP: {self._get_client_ip(request)}"
        )
        
        return None
    
    def process_response(self, request, response):
        """Log response status."""
        # Skip logging for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response
        
        if request.path == '/health/' or request.path.startswith('/admin/jsi18n/'):
            return response
        
        if response.status_code >= 400:
            logger.warning(
                f"RESPONSE: {request.method} {request.path} | "
                f"Status: {response.status_code}"
            )
        
        return response
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip