"""
ASGI config for community_feed project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'community_feed.settings')

application = get_asgi_application()
