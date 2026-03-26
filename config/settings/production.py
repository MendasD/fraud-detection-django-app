"""
Paramètres spécifiques à la production.
"""
import dj_database_url
import os
from .base import *


DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS','*').split(',')

SECRET_KEY = os.environ.get('SECRET_KEY','django-insecure-8q-sq74l8cf@7mzk1h7c*6lll04c)f4)7l5g2)lat-bze)qh@z')

# CSRF — domaine Railway + accepter toutes les origines railway.app
RAILWAY_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
]
if RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_DOMAIN}')

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Django Channels avec Redis en production pour le multi-worker
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             'hosts': [(os.environ.get('REDIS_HOST', '127.0.0.1'), 6379)],
#         },
#     }
# }
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Sécurité HTTPS (desactivé pour complications railway)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 31536000

# Indique à Django que la requête vient bien de HTTPS (header proxy Railway)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
 
# Clé CSRF — doit être stable entre les requêtes
# (déjà couverte par SECRET_KEY, mais on s'assure que le middleware est actif)
CSRF_USE_SESSIONS = False  # Utiliser le cookie standard, pas la session

# Logging en production vers fichier
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
        'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
