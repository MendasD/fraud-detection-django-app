"""
config/settings/production.py
Paramètres spécifiques à la production.
"""
import dj_database_url
import os
from .base import *


DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS','*').split(',')
#['127.0.0.1','fraud-detection-django-app-production.up.railway.app']
#os.environ.get('ALLOWED_HOSTS', '').split(',')

SECRET_KEY = os.environ.get('SECRET_KEY','django-insecure-8q-sq74l8cf@7mzk1h7c*6lll04c)f4)7l5g2)lat-bze)qh@z')

# Base de données PostgreSQL en production
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME', 'fortal_fraud'),
#         'USER': os.environ.get('DB_USER', 'postgres'),
#         'PASSWORD': os.environ.get('DB_PASSWORD', ''),
#         'HOST': os.environ.get('DB_HOST', 'localhost'),
#         'PORT': os.environ.get('DB_PORT', '5432'),
#     }
# }
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
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000

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
