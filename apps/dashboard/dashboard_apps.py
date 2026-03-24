"""
apps/dashboard/apps.py

Lance la boucle asyncio de streaming dans le même processus que Daphne,
ce qui garantit le partage du InMemoryChannelLayer.
"""

import logging
import os
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = 'Dashboard Analytique'

    def ready(self):
        """
        Appelé au démarrage Django.
        On lance la boucle de streaming seulement si on est dans
        le process Daphne/ASGI (pas dans migrate, shell, seed_transactions, etc.)
        """
        # Éviter le double lancement en dev (Django appelle ready() deux fois
        # avec le reloader). RUN_MAIN est défini par le reloader.
        if os.environ.get('RUN_MAIN') == 'true':
            return

        # Ne lancer que si la variable d'environnement ENABLE_STREAMING est définie,
        # OU si on est lancé via Daphne (DAPHNE_RUNNING défini dans asgi.py)
        if not os.environ.get('DAPHNE_RUNNING') and not os.environ.get('ENABLE_STREAMING'):
            return

        self._start_background_stream()

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
