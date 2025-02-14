"""
ASGI config for BlackDiamondHub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import sonos_control.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BlackDiamondHub.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            sonos_control.routing.websocket_urlpatterns
        )
    ),
})
