# Email Setup Guide for Fyndora

This document provides a comprehensive guide to understanding and setting up the email system in the Fyndora project. The email system is built using Django, Celery, Redis, and Gmail's OAuth2 authentication with round-robin load balancing across multiple Gmail accounts.

## Table of Contents

1. [Quick Start with Docker](#quick-start-with-docker)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Gmail OAuth2 Setup](#gmail-oauth2-setup)
5. [Environment Configuration](#environment-configuration)
6. [Django Settings Configuration](#django-settings-configuration)
7. [Email Templates](#email-templates)
8. [Email Services](#email-services)
9. [Celery Tasks](#celery-tasks)
10. [Custom Account Adapter](#custom-account-adapter)
11. [Testing the Email System](#testing-the-email-system)
12. [Monitoring and Logging](#monitoring-and-logging)
13. [Troubleshooting](#troubleshooting)

## Quick Start with Docker

For developers who want to get the email system running quickly:

### 1. Initial Setup

```bash
# Clone the repository and navigate to the project
cd Fyndora

# Copy environment template
cp .env.example .env

# Generate a Django secret key
./scripts/docker-dev.sh generate-secret

# Edit .env file with your values (at minimum set POSTGRES_PASSWORD and DJANGO_SECRET_KEY)
```

### 2. Gmail Setup (Required)

```bash
# Create credentials directory
mkdir -p credentials

# Place your Gmail OAuth2 JSON files in the credentials directory
# Follow the detailed Gmail OAuth2 Setup section below for complete instructions
```

### 3. Start Services

```bash
# Start all services (Django, PostgreSQL, Redis, Celery)
./scripts/docker-dev.sh up

# The application will be available at http://localhost:8000
```

### 4. Test Email System

```bash
# Open Django shell
./scripts/docker-dev.sh shell

# Test email sending (in Django shell)
from apps.emails.tasks import send_email_task
send_email_task.delay(
    to="test@example.com",
    subject="Test Email",
    contents="Hello from Fyndora!"
)
```

### 5. Monitor

```bash
# Watch logs
./scripts/docker-dev.sh logs

# Check Celery worker
docker compose logs celery_worker
```

> **Next Steps**: For detailed configuration and troubleshooting, continue reading the sections below.

## Architecture Overview

The Fyndora email system consists of several components working together:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Django App    │───▶│   Celery Task    │───▶│  Gmail SMTP     │
│   (Email Trigger)│    │   (Async Send)   │    │  (OAuth2)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Custom Adapter  │    │   Redis Cache    │    │ Multiple Gmail  │
│ (Allauth)       │    │ (Round Robin)    │    │   Accounts      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Features:
- **Asynchronous email sending** using Celery
- **Round-robin load balancing** across multiple Gmail accounts
- **OAuth2 authentication** for secure Gmail access
- **Template-based emails** with HTML and text versions
- **Custom Django Allauth adapter** for seamless integration
- **Comprehensive logging** and error handling

## Prerequisites

Before setting up the email system, ensure you have:

1. **Docker** and **Docker Compose** installed
2. **Gmail account(s)** with OAuth2 credentials
3. **Google Cloud Console** access for OAuth2 setup

> **Note**: This project uses Docker for development and production. All services (Django, PostgreSQL, Redis, Celery) run in containers.

## Gmail OAuth2 Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### Step 2: Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Configure the consent screen if prompted
4. Choose "Desktop application" as the application type
5. Download the JSON credentials file

### Step 3: Generate OAuth2 Token

You can generate the OAuth2 token either locally or using Docker:

**Option A: Using Docker (Recommended)**
```bash
# First, ensure your containers are running
./scripts/docker-dev.sh up

# Generate token
docker compose exec web python -c "
import yagmail
yag = yagmail.SMTP('your_gmail@gmail.com', oauth2_file='/usr/src/app/credentials/credentials.json')
print('OAuth2 setup complete!')
"
```

**Option B: Local Setup**
```bash
# Install yagmail locally
pip install yagmail

# Run this Python script to generate the OAuth2 token
python -c "
import yagmail
yag = yagmail.SMTP('your_gmail@gmail.com', oauth2_file='./credentials/credentials.json')
print('OAuth2 setup complete!')
"
```

This will open a browser window for authentication and create the necessary token files.

### Step 4: Organize Credential Files

Create a `credentials` directory in your project root:

```
credentials/
├── account1_oauth2.json
├── account2_oauth2.json
└── account3_oauth2.json
```

> **Important**: The `credentials` directory is mounted as `/usr/src/app/credentials` in Docker containers and should contain your OAuth2 credential files.

## Environment Configuration

### Step 1: Copy Environment Template

```bash
cp .env.example .env
```

### Step 2: Configure Gmail Accounts

Edit your `.env` file and set the `GMAIL_ACCOUNTS` variable with Docker container paths:

```bash
# Single Gmail account (Docker paths)
GMAIL_ACCOUNTS=[{"user": "your_email@gmail.com", "oauth2_file": "/usr/src/app/credentials/oauth2_creds.json"}]

# Multiple Gmail accounts (recommended for load balancing)
GMAIL_ACCOUNTS=[
  {"user": "account1@gmail.com", "oauth2_file": "/usr/src/app/credentials/account1_oauth2.json"},
  {"user": "account2@gmail.com", "oauth2_file": "/usr/src/app/credentials/account2_oauth2.json"},
  {"user": "account3@gmail.com", "oauth2_file": "/usr/src/app/credentials/account3_oauth2.json"}
]
```

### Step 3: Configure Other Required Variables

```bash
# Redis Configuration (Docker service name)
REDIS_URL=redis://redis:6379/0

# Database Configuration (Docker service name)
POSTGRES_DB=fyndora
POSTGRES_USER=fyndora
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Django Configuration
DEBUG=1
DJANGO_SECRET_KEY=your_secret_key_here
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
```

## Django Settings Configuration

The email system is configured in `config/settings.py`:

### Email-Specific Settings

```python
# Gmail accounts configuration
GMAIL_ACCOUNTS = env.json("GMAIL_ACCOUNTS", default=[])

# Use dummy backend since we handle emails through Celery tasks
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

# Allauth configuration
ACCOUNT_ADAPTER = "apps.emails.adapters.CustomAccountAdapter"
ACCOUNT_EMAIL_VERIFICATION = "none"  # or "mandatory" if you want email verification
```

### Celery Configuration

```python
CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
```

### Logging Configuration

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "email_log_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR("logs/emails.log"),
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 2,
        },
    },
    "loggers": {
        "emails": {
            "handlers": ["console", "email_log_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

## Email Templates

Email templates are located in `templates/account/email/` and follow Django Allauth conventions.

### Template Structure

For each email type, you need three files:
- `{template_name}_subject.txt` - Email subject
- `{template_name}_message.txt` - Plain text version
- `{template_name}_message.html` - HTML version (optional)

### Example: Email Confirmation Templates

**Subject Template** (`email_confirmation_signup_subject.txt`):
```
Confirm your email address
```

**Text Template** (`email_confirmation_signup_message.txt`):
```
Hello {{ user.get_full_name|default:user.username }},

Please confirm your email address by clicking the link below:

{{ activate_url }}

Thank you!
```

**HTML Template** (`email_confirmation_signup_message.html`):
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Confirm your email address</title>
</head>
<body>
    <h2>Hello {{ user.get_full_name|default:user.username }},</h2>
    
    <p>Please confirm your email address by clicking the link below:</p>
    
    <p><a href="{{ activate_url }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Confirm Email Address</a></p>
    
    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
    <p>{{ activate_url }}</p>
    
    <p>Thank you!</p>
</body>
</html>
```

### Available Template Variables

Common variables available in email templates:
- `{{ user }}` - User object
- `{{ user.get_full_name }}` - User's full name
- `{{ user.username }}` - Username
- `{{ user.email }}` - User's email
- `{{ activate_url }}` - Email confirmation URL
- `{{ password_reset_url }}` - Password reset URL

## Email Services

The `apps/emails/services.py` file contains high-level email functions:

```python
def send_signup_confirmation_email(user):
    """Sends a signup confirmation email to the user."""
    send_email_task.delay(
        to=user.email,
        subject="Confirm your email address",
        contents=f"Please confirm your email address by clicking this link: {user.get_confirmation_url()}",
    )

def send_password_reset_email(user):
    """Sends a password reset email to the user."""
    send_email_task.delay(
        to=user.email,
        subject="Reset your password",
        contents=f"Please reset your password by clicking this link: {user.get_password_reset_url()}",
    )
```

### Usage in Views

```python
from apps.emails.services import send_signup_confirmation_email

def signup_view(request):
    # ... user creation logic ...
    send_signup_confirmation_email(user)
    # ... rest of the view ...
```

## Celery Tasks

The core email sending logic is in `apps/emails/tasks.py`:

### Key Features:
- **Round-robin account selection** for load balancing
- **Atomic counter** using Redis cache
- **Comprehensive error handling** and logging
- **Yagmail integration** for Gmail SMTP

### Task Function

```python
@shared_task
def send_email_task(to, subject, contents):
    """
    A Celery task to send an email using one of the configured Gmail accounts,
    rotating between them for load balancing.
    """
    # Get configured Gmail accounts
    accounts = getattr(settings, "GMAIL_ACCOUNTS")
    
    # Round-robin selection using Redis cache
    account_index = cache.incr("last_gmail_account_index")
    selected_account_index = (account_index - 1) % len(accounts)
    selected_account = accounts[selected_account_index]
    
    # Send email using yagmail
    yag = yagmail.SMTP(
        selected_account["user"], 
        oauth2_file=selected_account["oauth2_file"]
    )
    yag.send(to=to, subject=subject, contents=contents)
```

## Custom Account Adapter

The `apps/emails/adapters.py` file contains a custom Django Allauth adapter:

### Key Features:
- **Template rendering** with context isolation
- **HTML and text email support**
- **Fallback mechanism** for missing templates
- **Integration with Celery tasks**

### Adapter Class

```python
class CustomAccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        """
        Overrides the default send_mail to use our custom email service
        and correctly render HTML and text templates.
        """
        # Render subject (required)
        subject = render_to_string(f"{template_prefix}_subject.txt", context)
        subject = "".join(subject.splitlines())
        
        # Try to render HTML template
        try:
            html_body = render_to_string(f"{template_prefix}_message.html", context)
        except TemplateDoesNotExist:
            html_body = None
        
        # Try to render text template
        try:
            text_body = render_to_string(f"{template_prefix}_message.txt", context)
        except TemplateDoesNotExist:
            text_body = None
        
        # Use HTML if available, otherwise text
        contents = html_body if html_body else text_body
        
        # Send via Celery task
        send_email_task.delay(to=email, subject=subject, contents=contents)
```

## Testing the Email System

### Step 1: Start Required Services

```bash
# Start all services (Django, PostgreSQL, Redis, Celery)
./scripts/docker-dev.sh up

# Or manually with docker compose
docker compose up -d --build

# Check that all services are running
docker compose ps
```

### Step 2: Test Email Sending

```bash
# Open Django shell in the web container
./scripts/docker-dev.sh shell

# Or manually
docker compose exec web python manage.py shell
```

```python
# In Django shell
from apps.emails.tasks import send_email_task

# Test basic email sending
send_email_task.delay(
    to="test@example.com",
    subject="Test Email",
    contents="This is a test email from Fyndora!"
)
```

### Step 3: Test Allauth Integration

```python
# Test signup email (in Django shell)
from django.contrib.auth import get_user_model
from apps.emails.services import send_signup_confirmation_email

User = get_user_model()
user = User.objects.create_user(
    username="testuser",
    email="test@example.com",
    password="testpass123"
)
send_signup_confirmation_email(user)
```

### Step 4: Monitor Logs

```bash
# Watch all logs
./scripts/docker-dev.sh logs

# Watch specific service logs
docker compose logs -f web
docker compose logs -f celery_worker

# Watch email logs (mounted volume)
tail -f logs/emails.log
```

### Step 5: Verify Celery Worker

```bash
# Check Celery worker status
docker compose exec celery_worker celery -A config inspect active

# Check Celery worker stats
docker compose exec celery_worker celery -A config inspect stats
```

## Monitoring and Logging

### Log Files

- **Email logs**: `logs/emails.log` (rotating, 5MB max, 2 backups)
- **Django logs**: Console output
- **Celery logs**: Worker process output

### Log Levels

- **INFO**: Successful email sends
- **ERROR**: Failed email sends with details
- **CRITICAL**: Configuration errors

### Example Log Entries

```
INFO 2024-01-15 10:30:45 emails Email sent successfully to user@example.com from account1@gmail.com.
ERROR 2024-01-15 10:31:02 emails Failed to send email to user@example.com from account2@gmail.com.
CRITICAL 2024-01-15 10:31:15 emails No Gmail accounts are configured in settings.GMAIL_ACCOUNTS.
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "No Gmail accounts configured" Error

**Problem**: `GMAIL_ACCOUNTS` is empty or not set.

**Solution**:
```bash
# Check your .env file
echo $GMAIL_ACCOUNTS

# Ensure proper JSON format
GMAIL_ACCOUNTS=[{"user": "your_email@gmail.com", "oauth2_file": "/path/to/creds.json"}]
```

#### 2. OAuth2 Authentication Errors

**Problem**: Invalid or expired OAuth2 credentials.

**Solution**:
```bash
# Regenerate OAuth2 token
python -c "
import yagmail
yag = yagmail.SMTP('your_gmail@gmail.com', oauth2_file='path/to/credentials.json')
"
```

#### 3. Celery Tasks Not Executing

**Problem**: Celery worker not running or Redis connection issues.

**Solution**:
```bash
# Check if all containers are running
docker compose ps

# Check Redis connection from web container
docker compose exec web python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print('Redis ping:', r.ping())
"

# Check Celery worker logs
docker compose logs celery_worker

# Restart Celery worker
docker compose restart celery_worker

# Check Celery task status from web container
docker compose exec web python manage.py shell -c "
from celery import current_app
print('Active tasks:', current_app.control.inspect().active())
"
```

#### 4. Template Not Found Errors

**Problem**: Missing email templates.

**Solution**:
```bash
# Check template directory structure
ls -la templates/account/email/

# Ensure all required templates exist:
# - {template_name}_subject.txt
# - {template_name}_message.txt
# - {template_name}_message.html (optional)
```

#### 5. Gmail Rate Limiting

**Problem**: Too many emails sent from single account.

**Solution**:
- Add more Gmail accounts to `GMAIL_ACCOUNTS`
- Implement delays between email sends
- Monitor Gmail sending limits

### Debug Commands

```bash
# Test Redis connection
docker compose exec web python manage.py shell -c "
from django.core.cache import cache
print('Redis test:', cache.get('test', 'Redis OK'))
"

# Check Gmail account configuration
docker compose exec web python manage.py shell -c "
from django.conf import settings
print('Gmail accounts:', settings.GMAIL_ACCOUNTS)
"

# Test email template rendering
docker compose exec web python manage.py shell -c "
from django.template.loader import render_to_string
print(render_to_string('account/email/email_confirmation_signup_subject.txt', {'user': {'username': 'test'}}))
"

# Monitor Celery tasks
docker compose exec celery_worker celery -A config inspect active
docker compose exec celery_worker celery -A config inspect stats

# Check container health
docker compose ps
docker compose logs --tail=50 web
docker compose logs --tail=50 celery_worker

# Test OAuth2 file access
docker compose exec web ls -la /usr/src/app/credentials/
```

### Performance Optimization

1. **Use multiple Gmail accounts** for higher throughput
2. **Monitor email logs** for performance bottlenecks
3. **Implement email queuing** for bulk operations
4. **Cache frequently used templates**
5. **Use Redis clustering** for high-availability setups

---

## Conclusion

The email system provides a robust, scalable solution for sending emails with the following benefits:

- **High availability** through multiple Gmail accounts
- **Asynchronous processing** for better user experience
- **Comprehensive logging** for monitoring and debugging
- **Template-based emails** for consistent branding
- **OAuth2 security** for Gmail authentication