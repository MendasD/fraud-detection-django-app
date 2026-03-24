"""
apps/api/views.py
API REST pour la simulation de flux et la consommation des données.
"""

import random
from django.utils import timezone
from django.db.models import Count, Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class TransactionSimulateView(APIView):
    """
    POST /api/v1/transactions/simulate/
    Génère et analyse une transaction synthétique immédiatement.
    Utile pour tester le système sans lancer stream_transactions.
    """

    def post(self, request):
        from ml_engine.data_generator import (
            generate_normal_transaction, generate_fraud_transaction,
            SENEGAL_CITIES, generate_client_id, generate_phone,
            FIRST_NAMES, LAST_NAMES
        )
        from apps.transactions.models import Transaction
        from apps.ml.fraud_detector import FraudDetector

        force_fraud = request.data.get('force_fraud', False)
        fraud_prob  = float(request.data.get('fraud_probability', 0.15))

        city_list    = list(SENEGAL_CITIES.keys())
        city_weights = [SENEGAL_CITIES[c]['weight'] for c in city_list]

        # Pool de clients minimal pour la simulation
        from ml_engine.data_generator import lognormal_amount
        client = {
            'id':         generate_client_id(),
            'name':       f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            'phone':      generate_phone(),
            'home_city':  random.choices(city_list, weights=city_weights)[0],
            'avg_amount': lognormal_amount(5_000, 500_000, 30_000),
        }

        is_fraud = force_fraud or (random.random() < fraud_prob)

        if is_fraud:
            data = generate_fraud_transaction([client], city_list, city_weights)
        else:
            data = generate_normal_transaction([client], city_list, city_weights)

        txn = Transaction(
            amount=data['amount'], sender_id=data['sender_id'],
            sender_phone=data.get('sender_phone', ''), sender_name=data.get('sender_name', ''),
            receiver_id=data['receiver_id'], receiver_phone=data.get('receiver_phone', ''),
            receiver_name=data.get('receiver_name', ''),
            transaction_type=data['transaction_type'],
            merchant_category=data.get('merchant_category', 'AUTRE'),
            device_type=data['device_type'],
            location_lat=data.get('location_lat'), location_lon=data.get('location_lon'),
            city=data.get('city', ''), country_code=data.get('country_code', 'SN'),
            hour_of_day=data['hour_of_day'], day_of_week=data['day_of_week'],
            is_weekend=bool(data.get('is_weekend', 0)), is_night=bool(data.get('is_night', 0)),
            distance_from_home=data.get('distance_from_home', 0),
            is_foreign_ip=bool(data.get('is_foreign_ip', 0)),
            is_new_device=bool(data.get('is_new_device', 0)),
            failed_attempts_24h=data.get('failed_attempts_24h', 0),
            freq_transactions_24h=data.get('freq_transactions_24h', 1),
            freq_transactions_7d=data.get('freq_transactions_7d', 1),
            avg_amount_30d=data.get('avg_amount_30d', 0),
            max_amount_30d=data.get('max_amount_30d', 0),
            ratio_to_avg=data.get('ratio_to_avg', 1.0),
            nb_unique_receivers_7d=data.get('nb_unique_receivers_7d', 1),
            is_first_transaction=bool(data.get('is_first_transaction', 0)),
            is_fraud=bool(data.get('is_fraud', 0)), is_simulated=True,
        )
        txn.save()
        result = FraudDetector.analyze(txn)
        txn.refresh_from_db()

        return Response({
            'transaction_id': str(txn.transaction_id),
            'amount':         int(txn.amount),
            'type':           txn.transaction_type,
            'city':           txn.city,
            'status':         txn.status,
            'fraud_score':    txn.fraud_score,
            'alert_level':    result.get('alert_level'),
            'inference_ms':   result.get('inference_time'),
        }, status=status.HTTP_201_CREATED)


class StatsView(APIView):
    """GET /api/v1/stats/ — Statistiques globales en JSON."""

    def get(self, request):
        from apps.transactions.models import Transaction, Alert
        from datetime import timedelta

        now     = timezone.now()
        last_24h = now - timedelta(hours=24)

        return Response({
            'total_transactions': Transaction.objects.count(),
            'transactions_24h':   Transaction.objects.filter(timestamp__gte=last_24h).count(),
            'fraud_detected':     Transaction.objects.filter(status__in=['SUSPECTE', 'BLOQUEE']).count(),
            'fraud_24h':          Transaction.objects.filter(timestamp__gte=last_24h, status__in=['SUSPECTE', 'BLOQUEE']).count(),
            'pending_alerts':     Alert.objects.filter(status='NOUVELLE').count(),
            'model_loaded':       _check_models(),
            'timestamp':          now.isoformat(),
        })


class ModelStatusView(APIView):
    """GET /api/v1/ml/status/ — État des modèles ML."""

    def get(self, request):
        from apps.ml.model_service import ModelService
        return Response({
            'is_ready':       ModelService.is_ready(),
            'models_loaded':  list(ModelService._models.keys()),
            'features_count': len(ModelService._feature_names),
        })


def _check_models():
    from apps.ml.model_service import ModelService
    return ModelService.is_ready()


class AlertUpdateView(APIView):
    """POST /api/v1/alerts/<id>/update/ — Met à jour le statut d'une alerte."""

    def post(self, request, alert_id):
        from apps.transactions.models import Alert
        try:
            alert = Alert.objects.get(id=alert_id)
        except Alert.DoesNotExist:
            return Response({'error': 'Alerte introuvable'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        allowed = [c[0] for c in Alert.AlertStatus.choices]
        if new_status not in allowed:
            return Response({'error': f'Statut invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        alert.status = new_status
        if new_status in ('RESOLUE', 'FAUX_POSITIF'):
            alert.resolved_by = request.user
            alert.resolved_at = timezone.now()
        alert.save()

        return Response({'success': True, 'alert_id': alert_id, 'new_status': new_status})

class HealthCheckView(APIView):
    """GET /api/v1/health/ — Endpoint public pour Railway healthcheck."""
    authentication_classes = []
    permission_classes     = []
 
    def get(self, request):
        return Response({'status': 'ok', 'service': 'fortal-bank'})