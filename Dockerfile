# Fortal Bank — Fraud Detection System
# Image Python officielle, stable sur Railway

FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DAPHNE_RUNNING=true

WORKDIR /app

# Dépendances système (pour scikit-learn, reportlab, Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Collecte des fichiers statiques au build
RUN python manage.py collectstatic --noinput || true

# Port exposé (Railway injecte $PORT, Daphne l'utilise)
EXPOSE 8080

# Démarrage : migrations + serveur
CMD python manage.py migrate --noinput && \
    daphne -b 0.0.0.0 -p ${PORT:-8080} config.asgi:application