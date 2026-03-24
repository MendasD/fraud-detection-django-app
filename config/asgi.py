"""
config/asgi.py
Configuration ASGI avec lifespan pour lancer stream_loop
dans l'event loop de Daphne (partage correct de InMemoryChannelLayer).
"""

import os
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

django_asgi_app = get_asgi_application()

from apps.dashboard.routing import websocket_urlpatterns

_inner_app = ProtocolTypeRouter({
    'http':      django_asgi_app,
    'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})


class LifespanApp:
    """
    Middleware ASGI qui planifie stream_loop dans l'event loop de Daphne
    dès le premier appel ASGI (lifespan ou première requête HTTP/WS).
    """

    def __init__(self, app):
        self.app = app
        self._stream_started = False
        self._stream_task = None

    async def __call__(self, scope, receive, send):
        # Planifier le stream une seule fois, dans l'event loop de Daphne
        if not self._stream_started:
            self._stream_started = True
            from apps.dashboard.background_stream import stream_loop
            import logging
            self._stream_task = asyncio.create_task(stream_loop())
            logging.getLogger(__name__).info("[ASGI] stream_loop planifié dans l'event loop Daphne.")

        if scope['type'] == 'lifespan':
            await self._handle_lifespan(receive, send)
        else:
            await self.app(scope, receive, send)

    async def _handle_lifespan(self, receive, send):
        while True:
            msg = await receive()
            if msg['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif msg['type'] == 'lifespan.shutdown':
                if self._stream_task:
                    self._stream_task.cancel()
                await send({'type': 'lifespan.shutdown.complete'})
                return


application = LifespanApp(_inner_app)
