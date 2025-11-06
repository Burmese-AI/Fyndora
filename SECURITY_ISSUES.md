# Security Hardening Issues - User Management & Authentication

This document contains 4 critical security issues that need to be addressed before production deployment.

---

## Issue #1: Implement Rate Limiting for Authentication Endpoints

### Priority: P0 - CRITICAL (Blocking Production)
### Labels: `security`, `authentication`, `P0-critical`

### Description
The application currently has no rate limiting on authentication endpoints, making it vulnerable to brute force attacks. Attackers can attempt unlimited login attempts without any throttling or account lockout mechanism.

### Current State
- ❌ No rate limiting on `/accounts/login/`
- ❌ No account lockout after failed attempts
- ✅ Failed login attempts are logged in audit trail (good!)
- ❌ No IP-based throttling
- ❌ No protection against credential stuffing attacks

### Security Impact
- **Severity:** CRITICAL
- **Attack Vector:** Brute force password guessing
- **Potential Impact:** Account takeover, data breach
- **OWASP Category:** A07:2021 – Identification and Authentication Failures

### Proposed Solution
Implement `django-axes` for comprehensive login protection.

### Implementation Steps

#### 1. Install django-axes
```bash
pip install django-axes
```

Update `pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies
    "django-axes>=6.1.1",
]
```

#### 2. Update Settings (`config/settings.py`)
```python
# Add to INSTALLED_APPS (before django.contrib.admin)
INSTALLED_APPS = [
    'axes',  # Should be as high as possible
    'django_htmx',
    'django.contrib.sites',
    # ... rest of apps
]

# Add to MIDDLEWARE (after AuthenticationMiddleware)
MIDDLEWARE = [
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',  # Add after AuthenticationMiddleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

# Add to AUTHENTICATION_BACKENDS (before other backends)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # Add first
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
]

# Django-axes Configuration
AXES_FAILURE_LIMIT = 5  # Lock after 5 failed attempts
AXES_COOLOFF_TIME = 1  # Lockout for 1 hour
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True  # More secure
AXES_RESET_ON_SUCCESS = True  # Reset counter on successful login
AXES_LOCKOUT_TEMPLATE = 'account/account_locked.html'
AXES_LOCKOUT_URL = '/accounts/locked/'
AXES_ENABLE_ADMIN = True  # Allow unlocking via admin
AXES_VERBOSE = True  # Detailed logging
AXES_USERNAME_FORM_FIELD = 'login'  # Match allauth form field
AXES_LOCK_OUT_BY_USER_OR_IP = False  # More strict
AXES_ONLY_USER_FAILURES = False  # Track IP failures too
```

#### 3. Create Account Locked Template
Create `templates/account/account_locked.html`:
```html
{% extends "base.html" %}
{% load i18n %}

{% block content %}
<div class="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
    <div class="text-center mb-6">
        <svg class="mx-auto h-12 w-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
    </div>

    <h1 class="text-2xl font-bold text-center mb-4 text-gray-800">Account Temporarily Locked</h1>

    <div class="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
        <p class="text-red-800 text-sm">
            Your account has been temporarily locked due to too many failed login attempts.
        </p>
    </div>

    <div class="space-y-4 text-gray-700">
        <p>
            <strong>Why was my account locked?</strong><br>
            After 5 consecutive failed login attempts, accounts are temporarily locked to protect against unauthorized access.
        </p>

        <p>
            <strong>How long is the lockout?</strong><br>
            Your account will be automatically unlocked after 1 hour.
        </p>

        <p>
            <strong>Need immediate access?</strong><br>
            Please contact support at <a href="mailto:support@fyndora.com" class="text-blue-600 hover:underline">support@fyndora.com</a>
        </p>
    </div>

    <div class="mt-6 text-center">
        <a href="{% url 'account_reset_password' %}" class="text-blue-600 hover:underline">
            Reset your password
        </a>
    </div>
</div>
{% endblock %}
```

#### 4. Add URL Configuration
Update `config/urls.py`:
```python
urlpatterns = [
    # ... existing patterns
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    # Add axes URLs if needed for manual unlocking
]
```

#### 5. Run Migrations
```bash
python manage.py migrate axes
```

#### 6. Integration with Audit Log
Update `apps/auditlog/auth_signals.py` to log lockout events:
```python
from axes.signals import user_locked_out
from django.dispatch import receiver

@receiver(user_locked_out)
@safe_audit_log
def log_user_lockout(sender, request, username, ip_address, **kwargs):
    """Log account lockout events"""
    audit_create_security_event(
        user=None,
        action_type=AuditActionType.ACCOUNT_LOCKED,
        metadata={
            'attempted_username': username,
            'ip_address': ip_address,
            'reason': 'excessive_failed_attempts',
            'automatic_logging': True,
        },
    )
```

Add to `apps/auditlog/constants.py`:
```python
class AuditActionType(models.TextChoices):
    # ... existing types
    ACCOUNT_LOCKED = "account_locked", "Account Locked"
    ACCOUNT_UNLOCKED = "account_unlocked", "Account Unlocked"
```

### Testing Requirements

#### Manual Testing
1. Attempt login with wrong password 5 times
2. Verify account is locked
3. Verify lockout template is displayed
4. Wait 1 hour or manually unlock via admin
5. Verify successful login works after cooldown

#### Automated Tests
Create `tests/security/test_rate_limiting.py`:
```python
import pytest
from django.test import Client
from django.urls import reverse
from axes.models import AccessAttempt

@pytest.mark.django_db
class TestRateLimiting:
    def test_account_locks_after_5_failed_attempts(self):
        client = Client()
        url = reverse('account_login')

        # Attempt 5 failed logins
        for i in range(5):
            response = client.post(url, {
                'login': 'testuser',
                'password': 'wrongpassword'
            })
            assert response.status_code in [200, 302]

        # 6th attempt should be locked
        response = client.post(url, {
            'login': 'testuser',
            'password': 'wrongpassword'
        })
        assert 'locked' in response.content.decode().lower()

    def test_successful_login_resets_counter(self, user_factory):
        user = user_factory(username='testuser')
        user.set_password('correctpassword')
        user.save()

        client = Client()
        url = reverse('account_login')

        # 3 failed attempts
        for i in range(3):
            client.post(url, {
                'login': 'testuser',
                'password': 'wrongpassword'
            })

        # Successful login
        response = client.post(url, {
            'login': 'testuser',
            'password': 'correctpassword'
        })
        assert response.status_code == 302

        # Counter should be reset
        attempts = AccessAttempt.objects.filter(username='testuser').count()
        assert attempts == 0
```

### Acceptance Criteria
- [ ] django-axes installed and configured
- [ ] Rate limiting active on all authentication endpoints
- [ ] Account locks after 5 failed attempts
- [ ] Lockout duration is 1 hour
- [ ] Lockout template displays helpful message
- [ ] Successful login resets failure counter
- [ ] Admin can manually unlock accounts
- [ ] Lockout events logged in audit trail
- [ ] Tests pass with 85%+ coverage
- [ ] Documentation updated

### Documentation Updates
- [ ] Update `README.md` with rate limiting information
- [ ] Document admin unlock process
- [ ] Add troubleshooting guide for locked accounts

### Related Issues
- Relates to audit logging improvements
- Depends on audit log constants

### References
- [django-axes Documentation](https://django-axes.readthedocs.io/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST Digital Identity Guidelines](https://pages.nist.gov/800-63-3/)

---

## Issue #2: Configure Session Security Settings

### Priority: P0 - CRITICAL (Blocking Production)
### Labels: `security`, `session-management`, `P0-critical`

### Description
Session security settings are not properly configured, leaving the application vulnerable to session hijacking, fixation, and other session-based attacks. This is critical for a finance and compliance platform.

### Current State
- ✅ Session middleware enabled
- ❌ SESSION_COOKIE_SECURE not set (allows HTTP transmission)
- ❌ SESSION_COOKIE_HTTPONLY not set (vulnerable to XSS)
- ❌ SESSION_COOKIE_SAMESITE not set (vulnerable to CSRF)
- ❌ SESSION_COOKIE_AGE not configured (indefinite sessions)
- ⚠️  ACCOUNT_SESSION_REMEMBER = True (potentially risky)
- ❌ SESSION_SAVE_EVERY_REQUEST not set
- ❌ No session expiration on browser close configuration

### Security Impact
- **Severity:** CRITICAL
- **Attack Vectors:** Session hijacking, session fixation, XSS-based session theft
- **Potential Impact:** Unauthorized access, account takeover
- **OWASP Category:** A01:2021 – Broken Access Control

### Compliance Requirements
- **SOC 2:** Requires secure session management
- **PCI-DSS:** Requires session timeout and secure cookies
- **ISO 27001:** Requires session security controls

### Proposed Solution
Configure comprehensive session security settings in Django.

### Implementation Steps

#### 1. Update Settings (`config/settings.py`)

Add session security configuration:
```python
# Session Configuration
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/5.2/ref/settings/#sessions

# Session cookie security
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_NAME = 'fyndora_sessionid'  # Custom name for obscurity
SESSION_COOKIE_AGE = 1209600  # 2 weeks (in seconds)

# Session behavior
SESSION_SAVE_EVERY_REQUEST = True  # Extend session on activity
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Keep sessions if configured
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'  # Use Redis cache
SESSION_CACHE_ALIAS = 'default'  # Use default Redis cache

# Additional security
SESSION_COOKIE_DOMAIN = None  # Use default domain
SESSION_COOKIE_PATH = '/'  # Entire site

# CSRF cookie security (complement to session security)
CSRF_COOKIE_SECURE = not DEBUG  # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True  # No JavaScript access
CSRF_COOKIE_SAMESITE = 'Strict'  # Additional CSRF protection
CSRF_COOKIE_NAME = 'fyndora_csrftoken'  # Custom name
CSRF_COOKIE_AGE = 31449600  # 1 year
CSRF_USE_SESSIONS = False  # Use cookie, not session storage

# Update allauth settings for consistency
ACCOUNT_SESSION_REMEMBER = False  # Don't remember by default
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5  # Consistent with axes
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 3600  # 1 hour in seconds
```

#### 2. Create Session Management Middleware

Create `apps/core/middleware/session_security.py`:
```python
"""
Session security middleware for additional protection.
"""
import logging
from datetime import datetime, timedelta
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced session security middleware.

    Features:
    - Absolute session timeout (regardless of activity)
    - Session IP binding (optional, can be problematic with mobile)
    - User agent validation
    - Session activity tracking
    """

    # Maximum absolute session lifetime (4 hours)
    ABSOLUTE_TIMEOUT = 14400  # 4 hours in seconds

    # Enable IP validation (disable if users frequently change IPs)
    VALIDATE_IP = False

    # Enable user agent validation
    VALIDATE_USER_AGENT = True

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        # Check absolute session timeout
        session_start = request.session.get('session_start_time')
        if session_start:
            session_age = datetime.now().timestamp() - session_start
            if session_age > self.ABSOLUTE_TIMEOUT:
                logger.warning(
                    f"Session timeout for user {request.user.username}",
                    extra={'user_id': request.user.user_id}
                )
                messages.warning(
                    request,
                    "Your session has expired due to inactivity. Please log in again."
                )
                logout(request)
                return redirect(reverse('account_login'))
        else:
            # First request, set session start time
            request.session['session_start_time'] = datetime.now().timestamp()

        # Validate IP address (optional)
        if self.VALIDATE_IP:
            stored_ip = request.session.get('session_ip')
            current_ip = self.get_client_ip(request)

            if stored_ip and stored_ip != current_ip:
                logger.warning(
                    f"Session IP mismatch for user {request.user.username}",
                    extra={
                        'user_id': request.user.user_id,
                        'stored_ip': stored_ip,
                        'current_ip': current_ip
                    }
                )
                messages.error(
                    request,
                    "Security alert: Your session IP has changed. Please log in again."
                )
                logout(request)
                return redirect(reverse('account_login'))
            elif not stored_ip:
                request.session['session_ip'] = current_ip

        # Validate user agent
        if self.VALIDATE_USER_AGENT:
            stored_ua = request.session.get('session_user_agent')
            current_ua = request.META.get('HTTP_USER_AGENT', '')

            if stored_ua and stored_ua != current_ua:
                logger.warning(
                    f"Session user agent mismatch for user {request.user.username}",
                    extra={'user_id': request.user.user_id}
                )
                messages.error(
                    request,
                    "Security alert: Your browser fingerprint has changed. Please log in again."
                )
                logout(request)
                return redirect(reverse('account_login'))
            elif not stored_ua:
                request.session['session_user_agent'] = current_ua

        # Update last activity timestamp
        request.session['last_activity'] = datetime.now().timestamp()

        return None

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

#### 3. Register Middleware

Update `config/settings.py`:
```python
MIDDLEWARE = [
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',
    'apps.core.middleware.session_security.SessionSecurityMiddleware',  # Add here
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]
```

#### 4. Create Session Management Views

Create `apps/accounts/views.py` (if empty, replace):
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.sessions.models import Session
from django.utils import timezone


@login_required
def active_sessions_view(request):
    """Display user's active sessions."""
    user_sessions = []
    all_sessions = Session.objects.filter(expire_date__gte=timezone.now())

    for session in all_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(request.user.pk):
            user_sessions.append({
                'session_key': session.session_key[:10] + '...',
                'expire_date': session.expire_date,
                'is_current': session.session_key == request.session.session_key,
                'ip_address': session_data.get('session_ip', 'Unknown'),
                'last_activity': session_data.get('last_activity'),
            })

    context = {
        'active_sessions': user_sessions,
        'session_timeout': '2 weeks',
        'absolute_timeout': '4 hours',
    }
    return render(request, 'account/active_sessions.html', context)


@login_required
def revoke_session_view(request, session_key):
    """Revoke a specific session."""
    if request.method == 'POST':
        Session.objects.filter(session_key=session_key).delete()
        messages.success(request, "Session revoked successfully.")
    return redirect('active_sessions')
```

#### 5. Add Session Management URLs

Update `apps/accounts/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.active_sessions_view, name='active_sessions'),
    path('sessions/<str:session_key>/revoke/', views.revoke_session_view, name='revoke_session'),
]
```

#### 6. Create Active Sessions Template

Create `templates/account/active_sessions.html`:
```html
{% extends "base.html" %}

{% block content %}
<div class="max-w-4xl mx-auto mt-8 p-6">
    <h1 class="text-2xl font-bold mb-6">Active Sessions</h1>

    <div class="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
        <p class="text-sm text-blue-800">
            <strong>Session Security:</strong> Sessions expire after {{ session_timeout }} of inactivity
            or {{ absolute_timeout }} absolute timeout. If you see unfamiliar sessions, revoke them immediately.
        </p>
    </div>

    <div class="space-y-4">
        {% for session in active_sessions %}
        <div class="bg-white border rounded-lg p-4 {% if session.is_current %}ring-2 ring-blue-500{% endif %}">
            <div class="flex justify-between items-start">
                <div>
                    <p class="font-semibold">
                        Session: {{ session.session_key }}
                        {% if session.is_current %}
                        <span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">Current</span>
                        {% endif %}
                    </p>
                    <p class="text-sm text-gray-600 mt-1">
                        IP: {{ session.ip_address }}
                    </p>
                    <p class="text-sm text-gray-600">
                        Expires: {{ session.expire_date|date:"Y-m-d H:i:s" }}
                    </p>
                </div>
                {% if not session.is_current %}
                <form method="post" action="{% url 'revoke_session' session.session_key %}">
                    {% csrf_token %}
                    <button type="submit" class="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600">
                        Revoke
                    </button>
                </form>
                {% endif %}
            </div>
        </div>
        {% empty %}
        <p class="text-gray-600">No active sessions found.</p>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

### Testing Requirements

#### Manual Testing
1. Log in and verify session cookie is secure (HTTPS only)
2. Verify cookie has HttpOnly flag set
3. Verify cookie has SameSite=Strict
4. Test session expiration after 2 weeks
5. Test absolute timeout after 4 hours
6. Verify session extends on activity
7. Test session management page displays active sessions
8. Test session revocation works

#### Automated Tests

Create `tests/security/test_session_security.py`:
```python
import pytest
from django.test import Client
from django.urls import reverse
from datetime import datetime, timedelta

@pytest.mark.django_db
class TestSessionSecurity:
    def test_session_cookie_secure_flag(self, settings):
        """Test that session cookie has secure flag in production."""
        settings.DEBUG = False
        client = Client()
        user = UserFactory()

        response = client.post(reverse('account_login'), {
            'login': user.username,
            'password': 'testpass123'
        })

        cookie = response.cookies.get('fyndora_sessionid')
        assert cookie is not None
        assert cookie['secure'] is True

    def test_session_cookie_httponly_flag(self):
        """Test that session cookie has HttpOnly flag."""
        client = Client()
        user = UserFactory()

        response = client.post(reverse('account_login'), {
            'login': user.username,
            'password': 'testpass123'
        })

        cookie = response.cookies.get('fyndora_sessionid')
        assert cookie['httponly'] is True

    def test_session_cookie_samesite_flag(self):
        """Test that session cookie has SameSite flag."""
        client = Client()
        user = UserFactory()

        response = client.post(reverse('account_login'), {
            'login': user.username,
            'password': 'testpass123'
        })

        cookie = response.cookies.get('fyndora_sessionid')
        assert cookie['samesite'] == 'Strict'

    def test_session_absolute_timeout(self, user_factory):
        """Test absolute session timeout."""
        client = Client()
        user = user_factory()

        # Login
        client.force_login(user)

        # Manipulate session start time to be 5 hours ago
        session = client.session
        session['session_start_time'] = (
            datetime.now() - timedelta(hours=5)
        ).timestamp()
        session.save()

        # Access protected page
        response = client.get(reverse('home'))

        # Should redirect to login
        assert response.status_code == 302
        assert 'login' in response.url

    def test_session_activity_extends_timeout(self, user_factory):
        """Test that activity extends session."""
        client = Client()
        user = user_factory()

        # Login
        client.force_login(user)

        # Get initial session age
        initial_age = client.session.get('last_activity')

        # Wait a bit
        import time
        time.sleep(2)

        # Make another request
        client.get(reverse('home'))

        # Session should have been updated
        new_age = client.session.get('last_activity')
        assert new_age > initial_age
```

### Acceptance Criteria
- [ ] All session cookie security flags configured
- [ ] Session timeout set to 2 weeks
- [ ] Absolute session timeout set to 4 hours
- [ ] SESSION_SAVE_EVERY_REQUEST enabled
- [ ] Session security middleware implemented
- [ ] Active sessions management page created
- [ ] Session revocation functionality works
- [ ] Tests pass with 85%+ coverage
- [ ] CSRF cookie security configured
- [ ] Documentation updated

### Documentation Updates
- [ ] Add session security section to README
- [ ] Document session timeout policies
- [ ] Add user guide for session management
- [ ] Document security middleware configuration

### Rollback Plan
If issues arise:
1. Temporarily disable SessionSecurityMiddleware
2. Revert SESSION_COOKIE_SECURE to False if HTTPS issues
3. Increase timeout values if user complaints
4. Monitor session-related support tickets

### References
- [Django Session Security](https://docs.djangoproject.com/en/5.2/topics/http/sessions/#session-security)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)

---

## Issue #3: Configure Security Headers and Transport Security

### Priority: P0 - CRITICAL (Blocking Production)
### Labels: `security`, `infrastructure`, `headers`, `P0-critical`

### Description
The application is missing critical security headers that protect against common web vulnerabilities including XSS, clickjacking, MITM attacks, and content sniffing. This is a critical gap for production deployment, especially for a finance and compliance platform.

### Current State
- ✅ CSRF middleware enabled
- ✅ Clickjacking middleware present
- ❌ No HSTS (HTTP Strict Transport Security)
- ❌ No SSL/TLS redirect configuration
- ❌ No Content-Type nosniff header
- ❌ No XSS protection header
- ❌ No Referrer-Policy header
- ❌ No Permissions-Policy header
- ❌ No Content Security Policy (CSP)
- ❌ X-Frame-Options not explicitly configured

### Security Impact
- **Severity:** CRITICAL
- **Attack Vectors:** MITM attacks, XSS, clickjacking, protocol downgrade
- **Potential Impact:** Data interception, session hijacking, malicious code injection
- **OWASP Category:** A05:2021 – Security Misconfiguration

### Compliance Requirements
- **PCI-DSS:** Requires HTTPS and HSTS
- **SOC 2:** Requires transport security
- **GDPR:** Requires data in transit protection

### Proposed Solution
Implement comprehensive security headers using Django settings and django-csp.

### Implementation Steps

#### 1. Install Dependencies
```bash
pip install django-csp
```

Update `pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies
    "django-csp>=3.8",
]
```

#### 2. Update Settings - Security Headers

Add to `config/settings.py`:
```python
# Security Headers
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/5.2/ref/middleware/#django.middleware.security.SecurityMiddleware

# HTTPS/SSL Configuration
if not DEBUG:
    # Force HTTPS in production
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # HTTP Strict Transport Security (HSTS)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    # Development settings
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0

# Browser Security Headers (apply in all environments)
SECURE_BROWSER_XSS_FILTER = True  # Enable XSS filter in browsers
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME type sniffing
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# Referrer Policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Additional Security Settings
SECURE_REDIRECT_EXEMPT = []  # Pages exempt from HTTPS redirect
```

#### 3. Configure Content Security Policy (CSP)

Add CSP middleware to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... existing apps
    'csp',
]
```

Add CSP middleware to `MIDDLEWARE`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',  # Add after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... rest of middleware
]
```

Add CSP configuration:
```python
# Content Security Policy (CSP)
# ------------------------------------------------------------------------------
# https://django-csp.readthedocs.io/

# CSP Directives
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",  # Required for some JS frameworks (review and remove if possible)
    "https://cdn.jsdelivr.net",  # For CDN scripts (HTMX, Alpine.js, etc.)
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",  # Required for inline styles (review and remove if possible)
    "https://cdn.jsdelivr.net",  # For CDN styles (Tailwind CSS, etc.)
)
CSP_IMG_SRC = (
    "'self'",
    "data:",  # For inline images
    "https:",  # Allow images from HTTPS sources
)
CSP_FONT_SRC = (
    "'self'",
    "https://fonts.gstatic.com",  # If using Google Fonts
    "data:",
)
CSP_CONNECT_SRC = (
    "'self'",
)
CSP_FRAME_SRC = ("'none'",)  # Disallow framing
CSP_OBJECT_SRC = ("'none'",)  # Disallow plugins
CSP_BASE_URI = ("'self'",)  # Restrict base tag URLs
CSP_FORM_ACTION = ("'self'",)  # Restrict form submissions
CSP_FRAME_ANCESTORS = ("'none'",)  # Disallow being framed
CSP_UPGRADE_INSECURE_REQUESTS = not DEBUG  # Upgrade HTTP to HTTPS

# CSP Reporting
if not DEBUG:
    CSP_REPORT_URI = '/csp-report/'  # Endpoint for CSP violation reports
    CSP_REPORT_ONLY = False  # Set to True for testing, False to enforce

# Permissions Policy (formerly Feature Policy)
PERMISSIONS_POLICY = {
    "accelerometer": [],
    "camera": [],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "payment": [],
    "usb": [],
}
```

#### 4. Create Custom Security Middleware

Create `apps/core/middleware/security_headers.py`:
```python
"""
Custom security headers middleware for additional protection.
"""
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add additional security headers not covered by Django's SecurityMiddleware.
    """

    def process_response(self, request, response):
        # Permissions Policy (Feature Policy)
        permissions_policy = "; ".join([
            "accelerometer=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "magnetometer=()",
            "microphone=()",
            "payment=()",
            "usb=()",
        ])
        response['Permissions-Policy'] = permissions_policy

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'

        # Referrer Policy (if not set by Django)
        if 'Referrer-Policy' not in response:
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Cross-Origin Policies
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'

        return response
```

Register the middleware:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',
    'apps.core.middleware.security_headers.SecurityHeadersMiddleware',  # Add here
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... rest of middleware
]
```

#### 5. Create CSP Violation Report Endpoint

Create `apps/core/views/security.py`:
```python
"""
Security-related views.
"""
import json
import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger('security')


@csrf_exempt
@require_POST
def csp_report_view(request):
    """
    Endpoint to receive CSP violation reports.
    """
    try:
        report = json.loads(request.body.decode('utf-8'))
        csp_report = report.get('csp-report', {})

        logger.warning(
            "CSP Violation",
            extra={
                'document_uri': csp_report.get('document-uri'),
                'violated_directive': csp_report.get('violated-directive'),
                'blocked_uri': csp_report.get('blocked-uri'),
                'source_file': csp_report.get('source-file'),
                'line_number': csp_report.get('line-number'),
            }
        )

        return JsonResponse({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")
        return JsonResponse({'status': 'error'}, status=400)
```

Add URL route in `config/urls.py`:
```python
from apps.core.views.security import csp_report_view

urlpatterns = [
    # ... existing patterns
    path('csp-report/', csp_report_view, name='csp_report'),
]
```

#### 6. Update Nginx/Server Configuration (Production)

Create `nginx-security-headers.conf`:
```nginx
# Security Headers Configuration
# Include this in your Nginx server block

# HSTS (HTTP Strict Transport Security)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# X-Frame-Options (Clickjacking Protection)
add_header X-Frame-Options "DENY" always;

# X-Content-Type-Options (MIME Type Sniffing Protection)
add_header X-Content-Type-Options "nosniff" always;

# X-XSS-Protection (XSS Filter)
add_header X-XSS-Protection "1; mode=block" always;

# Referrer Policy
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Permissions Policy
add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;

# Cross-Origin Policies
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Cross-Origin-Embedder-Policy "require-corp" always;
add_header Cross-Origin-Resource-Policy "same-origin" always;

# Hide Nginx version
server_tokens off;

# SSL Configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;
```

#### 7. Create Security Headers Test Page

Create `templates/security/headers_test.html`:
```html
{% extends "base.html" %}

{% block content %}
<div class="max-w-4xl mx-auto mt-8 p-6">
    <h1 class="text-2xl font-bold mb-6">Security Headers Test</h1>

    <div class="bg-green-50 border border-green-200 rounded-md p-4 mb-6">
        <p class="text-green-800">
            <strong>Security Status:</strong> All security headers are properly configured.
        </p>
    </div>

    <div class="space-y-6">
        <div>
            <h2 class="text-xl font-semibold mb-3">Configured Headers</h2>
            <ul class="list-disc list-inside space-y-2 text-gray-700">
                <li><strong>HSTS:</strong> Enabled (1 year, includeSubDomains, preload)</li>
                <li><strong>X-Frame-Options:</strong> DENY (Clickjacking protection)</li>
                <li><strong>X-Content-Type-Options:</strong> nosniff (MIME sniffing protection)</li>
                <li><strong>X-XSS-Protection:</strong> 1; mode=block</li>
                <li><strong>Referrer-Policy:</strong> strict-origin-when-cross-origin</li>
                <li><strong>Content-Security-Policy:</strong> Configured (see details)</li>
                <li><strong>Permissions-Policy:</strong> Restricted</li>
            </ul>
        </div>

        <div>
            <h2 class="text-xl font-semibold mb-3">Test Your Headers</h2>
            <p class="text-gray-700 mb-4">
                Use these online tools to verify security headers:
            </p>
            <ul class="list-disc list-inside space-y-2 text-blue-600">
                <li><a href="https://securityheaders.com" target="_blank" class="hover:underline">SecurityHeaders.com</a></li>
                <li><a href="https://observatory.mozilla.org" target="_blank" class="hover:underline">Mozilla Observatory</a></li>
                <li><a href="https://hstspreload.org" target="_blank" class="hover:underline">HSTS Preload List</a></li>
            </ul>
        </div>
    </div>
</div>
{% endblock %}
```

### Testing Requirements

#### Manual Testing
1. Deploy to staging environment with HTTPS
2. Test with https://securityheaders.com
3. Test with https://observatory.mozilla.org
4. Verify HSTS header is present
5. Verify CSP doesn't block legitimate resources
6. Test that HTTP redirects to HTTPS
7. Verify all pages load correctly with CSP

#### Automated Tests

Create `tests/security/test_security_headers.py`:
```python
import pytest
from django.test import Client, override_settings
from django.urls import reverse

@pytest.mark.django_db
class TestSecurityHeaders:

    @override_settings(DEBUG=False)
    def test_hsts_header_present_in_production(self):
        """Test that HSTS header is present in production."""
        client = Client()
        response = client.get('/', secure=True)

        assert 'Strict-Transport-Security' in response
        assert 'max-age=31536000' in response['Strict-Transport-Security']
        assert 'includeSubDomains' in response['Strict-Transport-Security']

    def test_x_frame_options_header(self):
        """Test that X-Frame-Options header is set."""
        client = Client()
        response = client.get('/')

        assert 'X-Frame-Options' in response
        assert response['X-Frame-Options'] == 'DENY'

    def test_content_type_nosniff_header(self):
        """Test that X-Content-Type-Options header is set."""
        client = Client()
        response = client.get('/')

        assert 'X-Content-Type-Options' in response
        assert response['X-Content-Type-Options'] == 'nosniff'

    def test_xss_protection_header(self):
        """Test that X-XSS-Protection header is set."""
        client = Client()
        response = client.get('/')

        assert 'X-XSS-Protection' in response
        assert '1' in response['X-XSS-Protection']

    def test_referrer_policy_header(self):
        """Test that Referrer-Policy header is set."""
        client = Client()
        response = client.get('/')

        assert 'Referrer-Policy' in response
        assert 'strict-origin' in response['Referrer-Policy']

    def test_csp_header_present(self):
        """Test that Content-Security-Policy header is present."""
        client = Client()
        response = client.get('/')

        assert 'Content-Security-Policy' in response
        assert "default-src 'self'" in response['Content-Security-Policy']

    def test_permissions_policy_header(self):
        """Test that Permissions-Policy header is set."""
        client = Client()
        response = client.get('/')

        assert 'Permissions-Policy' in response

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True)
    def test_http_redirects_to_https(self):
        """Test that HTTP requests redirect to HTTPS in production."""
        client = Client()
        response = client.get('/', secure=False)

        assert response.status_code == 301
        assert response.url.startswith('https://')
```

#### Security Scanning
```bash
# Test with SecurityHeaders.com
curl -I https://your-domain.com | grep -i "security\|strict\|frame\|xss\|content"

# Test HSTS Preload eligibility
# Visit: https://hstspreload.org/?domain=your-domain.com

# Test with Mozilla Observatory
# Visit: https://observatory.mozilla.org/analyze/your-domain.com
```

### Acceptance Criteria
- [ ] All security headers configured in Django settings
- [ ] HSTS enabled with 1-year max-age
- [ ] CSP configured and not breaking application
- [ ] SSL redirect enabled in production
- [ ] Custom security middleware implemented
- [ ] CSP violation reporting endpoint created
- [ ] Nginx configuration updated
- [ ] SecurityHeaders.com score: A+
- [ ] Mozilla Observatory score: A+
- [ ] Tests pass with 85%+ coverage
- [ ] Documentation updated

### Performance Considerations
- CSP may block some third-party resources - review carefully
- HSTS preload is irreversible - test thoroughly before submitting
- Monitor CSP violation reports for legitimate blocked resources

### Rollback Plan
If issues arise:
1. Set CSP_REPORT_ONLY = True to monitor without blocking
2. Disable SSL redirect temporarily if certificate issues
3. Adjust CSP directives based on violation reports
4. Have Nginx rollback configuration ready

### Documentation Updates
- [ ] Add security headers section to README
- [ ] Document CSP policy and allowed sources
- [ ] Add HSTS preload submission instructions
- [ ] Create security scanning checklist
- [ ] Document CSP violation monitoring

### References
- [Django Security Settings](https://docs.djangoproject.com/en/5.2/ref/settings/#security)
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [Content Security Policy Reference](https://content-security-policy.com/)
- [HSTS Preload List](https://hstspreload.org/)

---

## Issue #4: Improve Input Validation for User Management

### Priority: P1 - HIGH
### Labels: `security`, `validation`, `code-quality`, `P1-high`

### Description
The user creation and management code has several input validation issues that could lead to security vulnerabilities and data integrity problems. While basic validation exists, there are inconsistencies and gaps in the implementation.

### Current State
- ✅ Email normalization in CustomUserManager
- ✅ Duplicate email/username checking
- ✅ Django password validators configured
- ⚠️  Inconsistent exception types (ValueError vs ValidationError)
- ❌ Case-sensitive username checks
- ❌ No reserved username checking
- ❌ No email domain validation
- ❌ No username format validation
- ❌ No input sanitization
- ❌ No rate limiting on user creation

### Security Impact
- **Severity:** HIGH
- **Attack Vectors:** Account enumeration, user impersonation, data integrity issues
- **Potential Impact:** Unauthorized access, confused deputy attacks
- **OWASP Category:** A03:2021 – Injection & A04:2021 – Insecure Design

### Issues Found

#### Issue 1: Inconsistent Exception Types
**File:** `apps/accounts/models.py:14-26`
```python
# Current code:
if not email:
    raise ValueError("The Email field is required")  # ❌ Wrong exception type
if not username:
    raise ValueError("The Username field is required")  # ❌ Wrong exception type

if self.model.objects.filter(email=email).exists():
    raise ValidationError("A user with this email already exists.")  # ✓ Correct
```

#### Issue 2: Case-Sensitive Duplicate Checks
```python
# Current: Case-sensitive
if self.model.objects.filter(email=email).exists():  # user@example.com != USER@EXAMPLE.COM

# Should be: Case-insensitive
if self.model.objects.filter(email__iexact=email).exists():
```

#### Issue 3: No Reserved Username Protection
Currently allows registration of admin-like usernames that could be used for social engineering.

#### Issue 4: No Email Domain Validation
No validation to prevent disposable/temporary email addresses or invalid domains.

### Proposed Solution
Implement comprehensive input validation for user management.

### Implementation Steps

#### 1. Create Custom Validators

Create `apps/accounts/validators.py`:
```python
"""
Custom validators for user account fields.
"""
import re
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _


# Reserved usernames that cannot be registered
RESERVED_USERNAMES = [
    'admin', 'administrator', 'root', 'system', 'sysadmin',
    'superuser', 'webmaster', 'postmaster', 'hostmaster',
    'support', 'help', 'contact', 'info', 'sales', 'billing',
    'api', 'www', 'ftp', 'mail', 'smtp', 'pop', 'imap',
    'security', 'noreply', 'no-reply', 'abuse', 'privacy',
    'legal', 'dmca', 'copyright', 'trademark', 'null', 'undefined',
    'test', 'demo', 'guest', 'anonymous', 'user', 'users',
]

# Common disposable email domains
DISPOSABLE_EMAIL_DOMAINS = [
    'tempmail.com', 'throwaway.email', '10minutemail.com',
    'guerrillamail.com', 'mailinator.com', 'temp-mail.org',
    'getnada.com', 'maildrop.cc', 'trashmail.com',
]


def validate_username(username):
    """
    Validate username format and content.

    Rules:
    - 3-30 characters
    - Alphanumeric, underscores, hyphens only
    - Must start with letter or number
    - Cannot be reserved username
    - Case-insensitive reserved check
    """
    if not username:
        raise ValidationError(_("Username is required."))

    # Length check
    if len(username) < 3:
        raise ValidationError(_("Username must be at least 3 characters long."))
    if len(username) > 30:
        raise ValidationError(_("Username must be at most 30 characters long."))

    # Format check
    if not re.match(r'^[a-zA-Z0-9][\w-]*$', username):
        raise ValidationError(_(
            "Username must start with a letter or number and contain only "
            "letters, numbers, underscores, and hyphens."
        ))

    # Reserved username check (case-insensitive)
    if username.lower() in RESERVED_USERNAMES:
        raise ValidationError(_(
            "This username is reserved and cannot be used. "
            "Please choose a different username."
        ))

    # Check for multiple consecutive special characters
    if re.search(r'[_-]{2,}', username):
        raise ValidationError(_(
            "Username cannot contain consecutive underscores or hyphens."
        ))

    # Check for username that looks like email
    if '@' in username or '.' in username[:3] or '.' in username[-3:]:
        raise ValidationError(_("Username cannot look like an email address."))

    return username


def validate_email_domain(email):
    """
    Validate email domain.

    Rules:
    - Not a disposable email domain
    - Valid domain format
    - Not localhost or IP address
    """
    if not email or '@' not in email:
        raise ValidationError(_("Invalid email format."))

    # Run Django's built-in email validator first
    email_validator = EmailValidator()
    email_validator(email)

    domain = email.split('@')[1].lower()

    # Check for disposable email domains
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        raise ValidationError(_(
            "Disposable email addresses are not allowed. "
            "Please use a permanent email address."
        ))

    # Check for localhost
    if domain in ['localhost', '127.0.0.1', '0.0.0.0']:
        raise ValidationError(_("Email domain cannot be localhost."))

    # Check for IP address domains
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
        raise ValidationError(_("Email domain cannot be an IP address."))

    # Check for valid TLD (at least 2 characters)
    if '.' not in domain or len(domain.split('.')[-1]) < 2:
        raise ValidationError(_("Email domain must have a valid top-level domain."))

    return email


def validate_no_sql_injection(value):
    """
    Basic SQL injection pattern detection.
    While Django ORM protects against SQL injection, this adds defense in depth.
    """
    if not value:
        return value

    # Common SQL injection patterns
    sql_patterns = [
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(--)",
        r"(/\*.*\*/)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(;.*\b(SELECT|INSERT|UPDATE|DELETE)\b)",
    ]

    value_upper = value.upper()
    for pattern in sql_patterns:
        if re.search(pattern, value_upper, re.IGNORECASE):
            raise ValidationError(_("Invalid input detected."))

    return value


def validate_no_xss(value):
    """
    Basic XSS pattern detection.
    While Django templates escape by default, this adds defense in depth.
    """
    if not value:
        return value

    # Common XSS patterns
    xss_patterns = [
        r"<script[^>]*>.*</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
    ]

    for pattern in xss_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError(_("Invalid input detected."))

    return value


def sanitize_input(value):
    """
    Sanitize input by stripping dangerous characters.
    """
    if not value:
        return value

    # Strip leading/trailing whitespace
    value = value.strip()

    # Remove null bytes
    value = value.replace('\x00', '')

    # Remove other control characters
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

    return value
```

#### 2. Update CustomUserManager

Update `apps/accounts/models.py`:
```python
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.db import models
from django.core.exceptions import ValidationError
import uuid
from apps.accounts.constants import StatusChoices
from apps.core.models import baseModel
from apps.accounts.validators import (
    validate_username,
    validate_email_domain,
    validate_no_sql_injection,
    validate_no_xss,
    sanitize_input,
)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        """
        Create and save a regular user with the given email, username, and password.
        """
        # Validate required fields
        if not email:
            raise ValidationError("The Email field is required")
        if not username:
            raise ValidationError("The Username field is required")
        if not password:
            raise ValidationError("The Password field is required")

        # Sanitize inputs
        email = sanitize_input(email)
        username = sanitize_input(username)

        # Normalize email (converts to lowercase)
        email = self.normalize_email(email).lower()
        username = username.strip()

        # Custom validation
        try:
            validate_email_domain(email)
            validate_username(username)
            validate_no_sql_injection(email)
            validate_no_sql_injection(username)
            validate_no_xss(username)
        except ValidationError as e:
            raise ValidationError(str(e))

        # Check for existing users (case-insensitive)
        if self.model.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        if self.model.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with this username already exists.")

        # Create user
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)

        # Full clean for additional model validation
        user.full_clean()

        # Save user
        user.save(using=self._db)

        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """
        Create and save a superuser with the given email, username, and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValidationError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValidationError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin, baseModel):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True,
        validators=[validate_email_domain, validate_no_sql_injection]
    )
    username = models.CharField(
        max_length=30,  # Changed from 150 to match validator
        unique=True,
        validators=[validate_username, validate_no_sql_injection, validate_no_xss]
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return (
            f"{self.email} - {self.username} - {self.status} - Staff: {self.is_staff}"
        )

    def clean(self):
        """Additional model-level validation."""
        super().clean()

        # Normalize fields
        if self.email:
            self.email = self.email.lower().strip()
        if self.username:
            self.username = self.username.strip()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['status']),
        ]
```

#### 3. Create Migration
```bash
python manage.py makemigrations accounts
python manage.py migrate accounts
```

#### 4. Update Allauth Configuration

Add to `config/settings.py`:
```python
# allauth settings
ACCOUNT_ADAPTER = "apps.emails.adapters.CustomAccountAdapter"
ACCOUNT_LOGIN_METHODS = ("email",)
ACCOUNT_SIGNUP_FIELDS = ("email*", "username*", "password1*", "password2*")
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_USERNAME_BLACKLIST = RESERVED_USERNAMES  # From validators.py
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_VALIDATORS = [
    'apps.accounts.validators.validate_username'
]
```

#### 5. Create Custom Allauth Forms

Create `apps/accounts/forms.py`:
```python
"""
Custom forms for user account management.
"""
from django import forms
from allauth.account.forms import SignupForm
from apps.accounts.validators import (
    validate_username,
    validate_email_domain,
    sanitize_input,
)


class CustomSignupForm(SignupForm):
    """
    Custom signup form with additional validation.
    """

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = sanitize_input(email).lower()
            validate_email_domain(email)
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            username = sanitize_input(username)
            validate_username(username)
        return username

    def save(self, request):
        user = super().save(request)
        # Additional processing if needed
        return user
```

Update settings to use custom form:
```python
ACCOUNT_FORMS = {
    'signup': 'apps.accounts.forms.CustomSignupForm'
}
```

### Testing Requirements

#### Manual Testing
1. Try to register with disposable email
2. Try to register with reserved username
3. Try to register with invalid username format
4. Try SQL injection in username/email fields
5. Try XSS payloads in username/email fields
6. Test case-insensitive duplicate checking
7. Test username length limits

#### Automated Tests

Create `tests/unit/test_user_validators.py`:
```python
import pytest
from django.core.exceptions import ValidationError
from apps.accounts.validators import (
    validate_username,
    validate_email_domain,
    validate_no_sql_injection,
    validate_no_xss,
    sanitize_input,
)

class TestUsernameValidation:
    def test_valid_username(self):
        """Test that valid usernames pass."""
        valid_usernames = ['john_doe', 'user123', 'test-user', 'a1b2c3']
        for username in valid_usernames:
            assert validate_username(username) == username

    def test_username_too_short(self):
        """Test that short usernames are rejected."""
        with pytest.raises(ValidationError, match="at least 3 characters"):
            validate_username('ab')

    def test_username_too_long(self):
        """Test that long usernames are rejected."""
        with pytest.raises(ValidationError, match="at most 30 characters"):
            validate_username('a' * 31)

    def test_reserved_username(self):
        """Test that reserved usernames are rejected."""
        with pytest.raises(ValidationError, match="reserved"):
            validate_username('admin')
        with pytest.raises(ValidationError, match="reserved"):
            validate_username('ADMIN')  # Case-insensitive

    def test_invalid_username_format(self):
        """Test that invalid username formats are rejected."""
        invalid_usernames = [
            'user@example',  # Contains @
            'user name',  # Contains space
            'user!name',  # Contains !
            '-username',  # Starts with dash
            '_username',  # Starts with underscore
            'user__name',  # Consecutive underscores
        ]
        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                validate_username(username)


class TestEmailValidation:
    def test_valid_email(self):
        """Test that valid emails pass."""
        valid_emails = [
            'user@example.com',
            'test.user@company.org',
            'info@sub.domain.com'
        ]
        for email in valid_emails:
            assert validate_email_domain(email) == email

    def test_disposable_email(self):
        """Test that disposable emails are rejected."""
        with pytest.raises(ValidationError, match="Disposable"):
            validate_email_domain('test@tempmail.com')

    def test_localhost_email(self):
        """Test that localhost emails are rejected."""
        with pytest.raises(ValidationError, match="localhost"):
            validate_email_domain('user@localhost')

    def test_ip_address_email(self):
        """Test that IP address emails are rejected."""
        with pytest.raises(ValidationError, match="IP address"):
            validate_email_domain('user@192.168.1.1')


class TestSQLInjectionValidation:
    def test_sql_injection_patterns(self):
        """Test that SQL injection patterns are detected."""
        malicious_inputs = [
            "admin' OR '1'='1",
            "user'; DROP TABLE users--",
            "admin' UNION SELECT * FROM passwords--",
        ]
        for input_value in malicious_inputs:
            with pytest.raises(ValidationError, match="Invalid input"):
                validate_no_sql_injection(input_value)


class TestXSSValidation:
    def test_xss_patterns(self):
        """Test that XSS patterns are detected."""
        malicious_inputs = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
        ]
        for input_value in malicious_inputs:
            with pytest.raises(ValidationError, match="Invalid input"):
                validate_no_xss(input_value)


class TestInputSanitization:
    def test_sanitize_removes_nullbytes(self):
        """Test that null bytes are removed."""
        assert sanitize_input('test\x00user') == 'testuser'

    def test_sanitize_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert sanitize_input('  test  ') == 'test'

    def test_sanitize_removes_control_characters(self):
        """Test that control characters are removed."""
        result = sanitize_input('test\x01\x02user')
        assert '\x01' not in result
        assert '\x02' not in result
```

Create `tests/integration/test_user_creation.py`:
```python
import pytest
from django.core.exceptions import ValidationError
from apps.accounts.models import CustomUser

@pytest.mark.django_db
class TestUserCreation:
    def test_create_user_with_valid_data(self):
        """Test user creation with valid data."""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='SecurePass123!'
        )
        assert user.email == 'test@example.com'
        assert user.username == 'testuser'
        assert user.check_password('SecurePass123!')

    def test_create_user_normalizes_email(self):
        """Test that email is normalized to lowercase."""
        user = CustomUser.objects.create_user(
            email='Test@EXAMPLE.COM',
            username='testuser',
            password='SecurePass123!'
        )
        assert user.email == 'test@example.com'

    def test_create_user_rejects_duplicate_email_case_insensitive(self):
        """Test that duplicate emails are rejected (case-insensitive)."""
        CustomUser.objects.create_user(
            email='test@example.com',
            username='user1',
            password='SecurePass123!'
        )

        with pytest.raises(ValidationError, match="already exists"):
            CustomUser.objects.create_user(
                email='TEST@EXAMPLE.COM',
                username='user2',
                password='SecurePass123!'
            )

    def test_create_user_rejects_reserved_username(self):
        """Test that reserved usernames are rejected."""
        with pytest.raises(ValidationError, match="reserved"):
            CustomUser.objects.create_user(
                email='test@example.com',
                username='admin',
                password='SecurePass123!'
            )

    def test_create_user_rejects_disposable_email(self):
        """Test that disposable emails are rejected."""
        with pytest.raises(ValidationError, match="Disposable"):
            CustomUser.objects.create_user(
                email='test@tempmail.com',
                username='testuser',
                password='SecurePass123!'
            )
```

### Acceptance Criteria
- [ ] All validators implemented and tested
- [ ] CustomUserManager updated with validation
- [ ] Case-insensitive duplicate checking works
- [ ] Reserved usernames are blocked
- [ ] Disposable emails are blocked
- [ ] SQL injection patterns are detected
- [ ] XSS patterns are detected
- [ ] Input sanitization works correctly
- [ ] Custom allauth forms implemented
- [ ] Tests pass with 85%+ coverage
- [ ] Migration applied successfully
- [ ] Documentation updated

### Performance Considerations
- Validators add minimal overhead (~1-2ms per validation)
- Database queries use indexes for duplicate checks
- Consider caching disposable domain list if it grows large

### Documentation Updates
- [ ] Document validation rules for username
- [ ] Document validation rules for email
- [ ] Add examples of valid/invalid inputs
- [ ] Document reserved username list
- [ ] Add troubleshooting guide for validation errors

### References
- [Django Validators](https://docs.djangoproject.com/en/5.2/ref/validators/)
- [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [Username Best Practices](https://www.nngroup.com/articles/username-policies/)
- [Email Validation Best Practices](https://tools.ietf.org/html/rfc5321)

---

## Summary

These 4 issues cover the critical security improvements needed for the User Management & Authentication feature:

1. **Issue #1 - Rate Limiting**: Prevents brute force attacks (P0)
2. **Issue #2 - Session Security**: Protects against session hijacking (P0)
3. **Issue #3 - Security Headers**: Protects against multiple web attacks (P0)
4. **Issue #4 - Input Validation**: Prevents injection and ensures data integrity (P1)

**Total Estimated Effort:** 1-2 weeks
**Priority:** All must be completed before production deployment
**Compliance Impact:** Required for SOC2, PCI-DSS, ISO 27001

Please review and prioritize based on your deployment timeline.
