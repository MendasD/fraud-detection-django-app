FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DAPHNE_RUNNING=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic au build avec clé factice (pas de secrets nécessaires ici)
RUN SECRET_KEY=build-time-dummy ALLOWED_HOSTS=* \
    python manage.py collectstatic --noinput

RUN chmod +x entrypoint.sh

EXPOSE 8080

CMD ["./entrypoint.sh"]