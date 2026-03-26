"""
Routes WebSocket pour Django Channels.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/fraud-alerts/$', consumers.FraudAlertConsumer.as_asgi()),
]
