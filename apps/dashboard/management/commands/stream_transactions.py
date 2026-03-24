"""
apps/dashboard/management/commands/stream_transactions.py

Commande Django pour simuler l'arrivée de transactions en temps réel.
Injecte une transaction toutes les N secondes, l'analyse via le moteur ML,
et diffuse les résultats via WebSocket à tous les clients connectés.

Usage :
    python manage.py stream_transactions
    python manage.py stream_transactions --interval 3
    python manage.py stream_transactions --interval 5 --count 100
"""

import time
import random
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Simule un flux de transactions bancaires en temps réel avec détection de fraude'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=float,
            default=5.0,
            help='Intervalle entre chaque transaction (secondes, défaut: 5)',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=0,
            help='Nombre de transactions à générer (0 = illimité)',
        )
        parser.add_argument(
            '--fraud-boost',
            type=float,
            default=0.15,
            help='Probabilité de générer une fraude (défaut: 0.15)',
        )

    def handle(self, *args, **options):
        interval   = options['interval']
        count      = options['count']
        fraud_boost = options['fraud_boost']

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'  FORTAL BANK — Simulation flux temps réel\n'
            f'  Intervalle : {interval}s | Fraudes : {fraud_boost:.0%}\n'
            f'  Ctrl+C pour arrêter\n'
            f'{"="*60}\n'
        ))

        channel_layer = get_channel_layer()
        generated = 0

        try:
            while count == 0 or generated < count:
                # Génération et analyse d'une transaction
                transaction = self._create_and_analyze_transaction(fraud_boost)
                generated += 1

                # Affichage console avec couleur selon le résultat
                self._log_transaction(transaction, generated)

                # Diffusion WebSocket si la couche de channel est disponible
                if channel_layer:
                    self._broadcast(channel_layer, transaction)

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING(
                f'\n\nSimulation arrêtée. {generated} transactions générées.'
            ))

    def _create_and_analyze_transaction(self, fraud_boost: float):
        """
        Génère une transaction synthétique réaliste, la sauvegarde en base
        et la soumet au moteur de détection ML.
        """
        from ml_engine.data_generator import (
            generate_normal_transaction, generate_fraud_transaction,
            SENEGAL_CITIES,
        )
        from ml_engine.client_cache import client_profiles_cache
        from apps.transactions.models import Transaction
        from apps.ml.fraud_detector import FraudDetector

        # Décision : transaction normale ou frauduleuse
        is_forced_fraud = random.random() < fraud_boost

        city_list    = list(SENEGAL_CITIES.keys())
        city_weights = [SENEGAL_CITIES[c]['weight'] for c in city_list]

        if is_forced_fraud:
            data = generate_fraud_transaction(client_profiles_cache, city_list, city_weights)
        else:
            data = generate_normal_transaction(client_profiles_cache, city_list, city_weights)

        # Création de l'objet Django Transaction
        txn = Transaction(
            amount                = data['amount'],
            sender_id             = data['sender_id'],
            sender_phone          = data.get('sender_phone', ''),
            sender_name           = data.get('sender_name', ''),
            receiver_id           = data['receiver_id'],
            receiver_phone        = data.get('receiver_phone', ''),
            receiver_name         = data.get('receiver_name', ''),
            transaction_type      = data['transaction_type'],
            merchant_category     = data.get('merchant_category', 'AUTRE'),
            device_type           = data['device_type'],
            location_lat          = data.get('location_lat'),
            location_lon          = data.get('location_lon'),
            city                  = data.get('city', ''),
            country_code          = data.get('country_code', 'SN'),
            hour_of_day           = data['hour_of_day'],
            day_of_week           = data['day_of_week'],
            is_weekend            = bool(data.get('is_weekend', 0)),
            is_night              = bool(data.get('is_night', 0)),
            distance_from_home    = data.get('distance_from_home', 0),
            is_foreign_ip         = bool(data.get('is_foreign_ip', 0)),
            is_new_device         = bool(data.get('is_new_device', 0)),
            failed_attempts_24h   = data.get('failed_attempts_24h', 0),
            freq_transactions_24h = data.get('freq_transactions_24h', 1),
            freq_transactions_7d  = data.get('freq_transactions_7d', 1),
            avg_amount_30d        = data.get('avg_amount_30d', 0),
            max_amount_30d        = data.get('max_amount_30d', 0),
            ratio_to_avg          = data.get('ratio_to_avg', 1.0),
            nb_unique_receivers_7d = data.get('nb_unique_receivers_7d', 1),
            is_first_transaction  = bool(data.get('is_first_transaction', 0)),
            is_fraud              = bool(data.get('is_fraud', 0)),
            is_simulated          = True,
        )
        txn.save()

        # Analyse ML (mise à jour du statut + création d'alerte si fraude)
        result = FraudDetector.analyze(txn)
        txn.refresh_from_db()

        return txn

    def _log_transaction(self, txn, n: int):
        """Affichage console coloré selon le résultat de l'analyse."""
        score = txn.fraud_score or 0
        score_pct = f"{score:.0%}"

        if txn.status in ('SUSPECTE', 'BLOQUEE'):
            icon   = '🚨' if txn.status == 'BLOQUEE' else '⚠️'
            style  = self.style.ERROR
            status = f"FRAUDE DÉTECTÉE [{score_pct}]"
        else:
            icon   = '✓'
            style  = self.style.SUCCESS
            status = f"Légitime [{score_pct}]"

        self.stdout.write(style(
            f"[{n:>5}] {icon} {str(txn.transaction_id)[:8].upper()} | "
            f"{int(txn.amount):>12,} FCFA | {txn.transaction_type:<15} | "
            f"{txn.city:<15} | {status}"
        ))

    def _broadcast(self, channel_layer, txn):
        """Diffuse la transaction analysée à tous les clients WebSocket."""
        from apps.transactions.models import Alert

        score    = txn.fraud_score or 0
        is_fraud = txn.status in ('SUSPECTE', 'BLOQUEE')

        txn_data = {
            'id':     str(txn.transaction_id)[:8].upper(),
            'amount': int(txn.amount),
            'type':   txn.get_transaction_type_display(),
            'city':   txn.city,
            'status': txn.status,
            'score':  round(score, 3),
            'time':   txn.timestamp.strftime('%H:%M:%S'),
        }

        # Notification de transaction traitée (pour compteur live)
        async_to_sync(channel_layer.group_send)(
            'fraud_alerts',
            {
                'type':        'transaction_processed',
                'transaction': txn_data,
                'timestamp':   timezone.now().isoformat(),
            }
        )

        async_to_sync(channel_layer.group_send)(
            'fraud_alerts',
            {
                'type':  'stats_update',
                'stats': self._compute_stats(),
            }
        )

        # Si fraude détectée, envoi d'une alerte spécifique
        if is_fraud:
            try:
                alert = Alert.objects.get(transaction=txn)
                alert_data = {
                    'id':      alert.id,
                    'level':   alert.level,
                    'score':   round(alert.fraud_score, 3),
                    'message': alert.message[:200],
                }
                async_to_sync(channel_layer.group_send)(
                    'fraud_alerts',
                    {
                        'type':        'fraud_alert',
                        'transaction': txn_data,
                        'alert':       alert_data,
                        'timestamp':   timezone.now().isoformat(),
                    }
                )
            except Alert.DoesNotExist:
                pass

    def _compute_stats(self):
        """Calcule les KPIs courants pour les clients dashboard."""
        from datetime import timedelta
        from django.db.models import Avg, Q, Sum
        from apps.transactions.models import Transaction, Alert

        fraud_statuses = ['SUSPECTE', 'BLOQUEE']
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        amounts = Transaction.objects.aggregate(
            total_amount=Sum('amount'),
            fraud_amount=Sum('amount', filter=Q(status__in=fraud_statuses)),
            avg_score=Avg('fraud_score'),
        )
        total_txn = Transaction.objects.count()
        total_fraud = Transaction.objects.filter(status__in=fraud_statuses).count()

        return {
            'total_txn': total_txn,
            'total_fraud': total_fraud,
            'fraud_rate': round(total_fraud / total_txn * 100, 1) if total_txn else 0,
            'txn_24h': Transaction.objects.filter(timestamp__gte=last_24h).count(),
            'fraud_24h': Transaction.objects.filter(
                timestamp__gte=last_24h,
                status__in=fraud_statuses,
            ).count(),
            'pending_alerts': Alert.objects.filter(status='NOUVELLE').count(),
            'total_amount': int(amounts['total_amount'] or 0),
            'fraud_amount': int(amounts['fraud_amount'] or 0),
            'avg_score': round((amounts['avg_score'] or 0) * 100, 1),
        }
