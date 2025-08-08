"""Custom context processors for the application."""

import os
from django.conf import settings


def css_version(request):
    """
    Add CSS version based on file modification time for cache busting.
    """
    try:
        css_path = os.path.join(settings.STATICFILES_DIRS[0], 'css', 'output.css')
        if os.path.exists(css_path):
            mtime = int(os.path.getmtime(css_path))
            return {'css_version': mtime}
    except (IndexError, OSError):
        pass
    
    return {'css_version': '1'}