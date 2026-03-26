"""
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
