# Fortal Bank — Système de Détection de Fraudes Bancaires

Système ML de détection de fraudes en temps réel pour Fortal Bank (contexte sénégalais).

## Stack technique

- **Backend** : Django 4.x + Django REST Framework
- **Temps réel** : Django Channels + WebSocket
- **ML** : scikit-learn (Isolation Forest, One-Class SVM, Random Forest) + joblib
- **Données** : Transactions bancaires sénégalaises synthétiques (FCFA, Wave, Orange Money…)
- **Carte** : Leaflet.js centré sur le Sénégal
- **Graphiques** : Chart.js
- **PDF** : ReportLab

## Installation

```bash
# 1. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate

# 2. Installer les dépendances
pip install django djangorestframework channels django-environ \
            scikit-learn pandas numpy joblib faker reportlab Pillow

# 3. Variables d'environnement (développement)
export DJANGO_SETTINGS_MODULE=config.settings.development

# 4. Migrations
python manage.py makemigrations accounts transactions
python manage.py migrate

# 5. Créer un superutilisateur
python manage.py createsuperuser
```

## Entraînement des modèles ML

```bash
# Génère 50 000 transactions synthétiques + entraîne les 3 modèles
python ml_engine/train_models.py

# Options avancées
python ml_engine/train_models.py --n_samples 100000 --models_dir models/
```

Les fichiers `.pkl` sont sauvegardés dans `models/` :
- `isolation_forest.pkl` — Détection d'anomalies
- `one_class_svm.pkl`    — Frontière de normalité
- `random_forest.pkl`    — Classification supervisée
- `scaler.pkl`           — Normalisation des features
- `feature_names.pkl`    — Ordre des features

## Démarrage

```bash
# Serveur Django (avec WebSocket via ASGI)
python manage.py runserver

# Dans un autre terminal : simulation du flux temps réel
python manage.py stream_transactions --interval 5 --fraud-boost 0.15
```

## Accès

| URL | Description |
|-----|-------------|
| http://localhost:8000/ | Dashboard principal |
| http://localhost:8000/dashboard/map/ | Carte Sénégal |
| http://localhost:8000/dashboard/alerts/ | Alertes |
| http://localhost:8000/reports/ | Rapport PDF |
| http://localhost:8000/api/v1/stats/ | API statistiques |
| http://localhost:8000/api/v1/transactions/simulate/ | Simuler 1 transaction |
| http://localhost:8000/admin/ | Administration Django |

## Architecture ML

```
Transaction → FraudDetector.analyze()
                    │
                    ├── ModelService.predict()
                    │       ├── Isolation Forest  → score (×0.25)
                    │       ├── One-Class SVM     → score (×0.25)
                    │       └── Random Forest     → score (×0.50)
                    │               ↓
                    │       Score agrégé pondéré
                    │
                    ├── Mise à jour Transaction (statut, fraud_score)
                    ├── Création MLPrediction (audit par modèle)
                    ├── Création Alert (si score ≥ 0.50)
                    └── Diffusion WebSocket (channel_layer.group_send)
```

## Scénarios de fraude simulés

1. **Gros montant** — Montant 5x à 20x supérieur à la moyenne client
2. **IP étrangère** — Transaction depuis Nigeria, Côte d'Ivoire, Mali…
3. **Nouvel appareil** — Prise de contrôle de compte
4. **Transaction nocturne** — Entre 1h et 4h du matin
5. **Flooding** — 15 à 40 transactions rapides en 24h
6. **Géoloc suspecte** — Transaction à 300-800 km du domicile

## Structure du projet

```
fortal_fraud/
├── config/         # Settings, URLs, ASGI/WSGI
├── apps/
│   ├── accounts/   # Modèle User personnalisé
│   ├── transactions/ # Transaction, Alert, MLPrediction
│   ├── ml/         # ModelService, FraudDetector
│   ├── dashboard/  # Vues, WebSocket, management commands
│   ├── reports/    # Génération PDF ReportLab
│   └── api/        # DRF endpoints
├── ml_engine/      # Scripts standalone ML
│   ├── data_generator.py
│   ├── train_models.py
│   └── client_cache.py
├── models/         # Fichiers .pkl (après entraînement)
├── static/         # CSS, JS
└── templates/      # HTML
```
