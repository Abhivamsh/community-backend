"""
WSGI config for community_feed project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'community_feed.settings')

application = get_wsgi_application()
