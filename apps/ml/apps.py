"""
AppConfig du module ML.
Les modèles joblib sont chargés en mémoire UNE SEULE FOIS au démarrage
de Django via la méthode ready(), ce qui garantit des inférences rapides
sans rechargement disque à chaque requête.
"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MLConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ml'
    verbose_name = 'Moteur ML - Détection de Fraudes'

    def ready(self):
        """
        Appelé automatiquement par Django au démarrage du serveur.
        Charge tous les modèles ML en mémoire via ModelService.
        Si les fichiers .pkl n'existent pas encore (avant entraînement),
        on logue un avertissement sans bloquer le démarrage.
        """
        try:
            from .model_service import ModelService
            ModelService.load_models()
            logger.info("Modèles ML chargés avec succès au démarrage.")
        except FileNotFoundError:
            logger.warning(
                "Fichiers de modèles ML introuvables. "
                "Lancez 'python ml_engine/train_models.py' pour entraîner les modèles."
            )
        except Exception as e:
            logger.error(f"Erreur lors du chargement des modèles ML : {e}")
