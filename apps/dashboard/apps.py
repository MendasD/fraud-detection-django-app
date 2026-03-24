"""
apps/dashboard/apps.py

Lance la boucle asyncio de streaming dans le même processus que Daphne,
ce qui garantit le partage du InMemoryChannelLayer.
"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = 'Dashboard Analytique'

    def ready(self):
        """
        Le streaming est désormais lancé via le lifespan ASGI dans config/asgi.py,
        ce qui garantit qu'il s'exécute dans l'event loop de Daphne.
        """
        pass

    def _start_background_stream(self):
        """Lance la tâche asyncio de streaming en arrière-plan."""
        import asyncio
        import threading

        def run_in_thread():
            """
            Lance un event loop dédié dans un thread séparé.
            Ce thread partage la mémoire du processus Daphne,
            donc le channel_layer InMemory est bien partagé.
            """
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from apps.dashboard.background_stream import stream_loop
                loop.run_until_complete(stream_loop())
            except Exception as e:
                logger.error(f"[STREAM] Erreur fatale : {e}")
            finally:
                loop.close()

        t = threading.Thread(target=run_in_thread, daemon=True, name="fortal-stream")
        t.start()
        logger.info("[STREAM] Thread de streaming démarré en arrière-plan.")