"""
Tâche de fond asyncio lancée au démarrage de Daphne (dans le même processus).
Génère des transactions et les diffuse via channel_layer IN-PROCESS.

Avantage : fonctionne avec InMemoryChannelLayer sans Redis,
car tout s'exécute dans le même process Python/event-loop.

Appelé depuis config.asgi.py
"""

import asyncio
import logging
import random

logger = logging.getLogger(__name__)

# Intervalle en secondes entre chaque transaction simulée
STREAM_INTERVAL = 5


async def stream_loop():
    """
    Boucle infinie asyncio qui génère une transaction toutes les
    STREAM_INTERVAL secondes et la diffuse via channel_layer.
    S'exécute dans le même event-loop que Daphne/Channels.
    """
    # Attente initiale pour laisser Django/Daphne finir de démarrer
    await asyncio.sleep(8)
    logger.info("[STREAM] Démarrage de la boucle de streaming temps réel...")

    from channels.layers import get_channel_layer
    from asgiref.sync import sync_to_async
    from django.utils import timezone

    channel_layer = get_channel_layer()

    if channel_layer is None:
        logger.error("[STREAM] channel_layer non disponible — streaming désactivé.")
        return

    # Initialisation du pool de clients
    from ml_engine.data_generator import (
        SENEGAL_CITIES,
    )
    from ml_engine.client_cache import client_profiles_cache

    city_list    = list(SENEGAL_CITIES.keys())
    city_weights = [SENEGAL_CITIES[c]['weight'] for c in city_list]

    count = 0
    while True:
        try:
            await asyncio.sleep(STREAM_INTERVAL)

            # Génération et analyse dans le thread Django (sync_to_async)
            txn, result = await sync_to_async(_create_and_analyze)()

            count += 1
            score  = txn.fraud_score or 0
            status = txn.status

            logger.debug(
                f"[STREAM #{count}] {str(txn.transaction_id)[:8].upper()} "
                f"| {int(txn.amount):,} FCFA | {txn.city} | score={score:.2f} | {status}"
            )

            # Données de la transaction pour le broadcast
            txn_data = {
                'id':     str(txn.transaction_id)[:8].upper(),
                'amount': int(txn.amount),
                'type':   txn.get_transaction_type_display(),
                'city':   txn.city or '',
                'status': status,
                'score':  round(score, 3),
                'time':   txn.timestamp.strftime('%H:%M:%S'),
            }

            # Broadcast "transaction traitée" à tous les clients connectés
            await channel_layer.group_send(
                'fraud_alerts',
                {
                    'type':        'transaction_processed',
                    'transaction': txn_data,
                    'timestamp':   timezone.now().isoformat(),
                }
            )

            # Mise à jour des KPIs toutes les 5 transactions
            stats = await sync_to_async(_compute_stats)()
            await channel_layer.group_send(
                'fraud_alerts',
                {
                    'type':  'stats_update',
                    'stats': stats,
                }
            )

            # Si fraude détectée : broadcast alerte spécifique
            if status in ('SUSPECTE', 'BLOQUEE'):
                try:
                    from apps.transactions.models import Alert
                    alert = await sync_to_async(
                        Alert.objects.select_related('transaction').get
                    )(transaction=txn)

                    alert_data = {
                        'id':      alert.id,
                        'level':   alert.level,
                        'score':   round(alert.fraud_score, 3),
                        'message': alert.message[:200],
                    }
                    await channel_layer.group_send(
                        'fraud_alerts',
                        {
                            'type':        'fraud_alert',
                            'transaction': txn_data,
                            'alert':       alert_data,
                            'timestamp':   timezone.now().isoformat(),
                        }
                    )
                    logger.info(
                        f"[STREAM] 🚨 ALERTE {alert.level} — "
                        f"{int(txn.amount):,} FCFA | {txn.city} | {score:.0%}"
                    )
                except Exception:
                    pass

        except asyncio.CancelledError:
            logger.info("[STREAM] Boucle arrêtée proprement.")
            break
        except Exception as e:
            logger.warning(f"[STREAM] Erreur dans la boucle : {e}")
            await asyncio.sleep(2)


def _compute_stats():
    """Calcule les KPIs actuels pour la mise à jour du dashboard."""
    from datetime import timedelta
    from django.db.models import Sum, Avg, Q
    from django.utils import timezone as tz
    from apps.transactions.models import Transaction, Alert

    fraud_statuses = ['SUSPECTE', 'BLOQUEE']
    now = tz.now()
    since_24h = now - timedelta(hours=24)

    total = Transaction.objects.count()
    fraud = Transaction.objects.filter(status__in=fraud_statuses).count()
    fraud_rate = round(fraud / total * 100, 1) if total else 0
    pending = Alert.objects.filter(status='NOUVELLE').count()

    amounts = Transaction.objects.aggregate(
        total_amount=Sum('amount'),
        fraud_amount=Sum('amount', filter=Q(status__in=fraud_statuses)),
        avg_score=Avg('fraud_score'),
    )

    return {
        'total_txn':      total,
        'total_fraud':    fraud,
        'fraud_rate':     fraud_rate,
        'pending_alerts': pending,
        'total_amount':   int(amounts['total_amount'] or 0),
        'fraud_amount':   int(amounts['fraud_amount'] or 0),
        'avg_score':      round((amounts['avg_score'] or 0) * 100, 1),
        'txn_24h':        Transaction.objects.filter(timestamp__gte=since_24h).count(),
        'fraud_24h':      Transaction.objects.filter(status__in=fraud_statuses, timestamp__gte=since_24h).count(),
    }


def _create_and_analyze():
    """
    Fonction synchrone : génère une transaction, l'analyse ML,
    retourne (transaction, result). Appelée via sync_to_async.
    """
    from ml_engine.data_generator import (
        generate_normal_transaction,
        generate_fraud_transaction,
        SENEGAL_CITIES,
    )
    from ml_engine.client_cache import client_profiles_cache
    from apps.transactions.models import Transaction
    from apps.ml.fraud_detector import FraudDetector

    city_list    = list(SENEGAL_CITIES.keys())
    city_weights = [SENEGAL_CITIES[c]['weight'] for c in city_list]

    # 8% de chance de générer une fraude
    is_fraud = random.random() < 0.08

    if is_fraud:
        data = generate_fraud_transaction(client_profiles_cache, city_list, city_weights)
    else:
        data = generate_normal_transaction(client_profiles_cache, city_list, city_weights)

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
    result = FraudDetector.analyze(txn)
    txn.refresh_from_db()
    return txn, result
