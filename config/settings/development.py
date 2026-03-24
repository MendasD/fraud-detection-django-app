"""
config/settings/development.py
Paramètres spécifiques à l'environnement de développement.
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

SECRET_KEY = 'django-insecure-dev-key-fortal-fraud-2024-change-me'

# Affichage des requêtes SQL en développement (optionnel)
# LOGGING permet de voir les requêtes dans la console
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
        },
    },
    'loggers': {
        'apps.ml': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.transactions': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.dashboard': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# En dev, on utilise la couche In-Memory (pas besoin de Redis)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Email en console pendant le développement
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
