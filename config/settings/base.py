"""
config/settings/base.py
Paramètres de base partagés entre tous les environnements.
"""

import os
from pathlib import Path

# Racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Clé secrète (à surcharger dans les settings spécifiques)
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = False

ALLOWED_HOSTS = []

# Applications installées
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'channels',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.transactions',
    'apps.ml',
    'apps.dashboard',
    'apps.reports',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ASGI pour Django Channels (WebSocket)
ASGI_APPLICATION = 'config.asgi.application'
WSGI_APPLICATION = 'config.wsgi.application'

# Base de données par défaut (SQLite pour dev)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Validation des mots de passe
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalisation
LANGUAGE_CODE = 'fr-sn'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

# Fichiers statiques
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Fichiers média (PDFs générés, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Clé primaire par défaut
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Modèle utilisateur personnalisé
AUTH_USER_MODEL = 'accounts.User'

# Redirections d'authentification
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Django Channels — couche de channel (In-Memory pour dev, Redis en prod)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Chemins vers les modèles ML sérialisés par joblib
ML_MODELS_DIR = BASE_DIR / 'models'
ML_MODELS = {
    'isolation_forest': ML_MODELS_DIR / 'isolation_forest.pkl',
    'one_class_svm':    ML_MODELS_DIR / 'one_class_svm.pkl',
    'random_forest':    ML_MODELS_DIR / 'random_forest.pkl',
    'scaler':           ML_MODELS_DIR / 'scaler.pkl',
    'feature_names':    ML_MODELS_DIR / 'feature_names.pkl',
}

# Fréquence de simulation du flux de transactions (en secondes)
TRANSACTION_STREAM_INTERVAL = 5

# Seuil de probabilité de fraude pour déclencher une alerte
FRAUD_ALERT_THRESHOLD = 0.5

# Niveaux de criticité des alertes
ALERT_LEVELS = {
    'CRITIQUE': {'min_score': 0.85, 'color': '#C62828'},
    'ELEVE':    {'min_score': 0.65, 'color': '#F59E0B'},
    'MOYEN':    {'min_score': 0.50, 'color': '#EAB308'},
}

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
