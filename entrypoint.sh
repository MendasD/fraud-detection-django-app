#!/bin/sh
set -e

echo "==> Migrations..."
python manage.py migrate --noinput

echo "==> Création superuser si absent..."
python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@fortalbank.sn', 'fortal2024')
    print('Superuser admin créé')
else:
    print('Superuser déjà existant')
" || true

echo "==> Démarrage Daphne sur port ${PORT:-8080}..."
exec daphne -b 0.0.0.0 -p "${PORT:-8080}" config.asgi:application