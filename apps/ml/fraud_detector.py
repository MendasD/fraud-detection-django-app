"""
FraudDetector — Orchestre la détection de fraude sur une transaction Django.
Il fait le lien entre le ModelService (ML pur) et la couche Django
(sauvegarde en base, création d'alertes, diffusion WebSocket).
"""

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class FraudDetector:
    """
    Orchestre la détection de fraude :
    1. Appelle ModelService.predict()
    2. Met à jour la transaction en base
    3. Crée une alerte si nécessaire
    4. Retourne le résultat complet
    """

    @staticmethod
    def analyze(transaction) -> dict:
        """
        Analyse une transaction et met à jour son statut en base.

        Args:
            transaction: Instance du modèle Transaction

        Returns:
            dict avec fraud_score, fraud_label, alert_level, model_results
        """
        from apps.ml.model_service import ModelService
        from apps.transactions.models import Transaction, Alert, MLPrediction

        # Construction du dictionnaire de features depuis l'objet Django
        transaction_data = {
            'amount':                   float(transaction.amount),
            'hour_of_day':              transaction.hour_of_day,
            'day_of_week':              transaction.day_of_week,
            'is_weekend':               int(transaction.is_weekend),
            'is_night':                 int(transaction.is_night),
            'distance_from_home':       transaction.distance_from_home,
            'is_foreign_ip':            int(transaction.is_foreign_ip),
            'is_new_device':            int(transaction.is_new_device),
            'failed_attempts_24h':      transaction.failed_attempts_24h,
            'freq_transactions_24h':    transaction.freq_transactions_24h,
            'freq_transactions_7d':     transaction.freq_transactions_7d,
            'avg_amount_30d':           float(transaction.avg_amount_30d),
            'max_amount_30d':           float(transaction.max_amount_30d),
            'ratio_to_avg':             transaction.ratio_to_avg,
            'nb_unique_receivers_7d':   transaction.nb_unique_receivers_7d,
            'is_first_transaction':     int(transaction.is_first_transaction),
            'transaction_type':         transaction.transaction_type,
            'device_type':              transaction.device_type,
        }

        # Prédiction ML
        result = ModelService.predict(transaction_data)

        fraud_score = result['fraud_score']
        fraud_label = result['fraud_label']
        alert_level = result['alert_level']

        # Mise à jour de la transaction
        if fraud_score >= 0.85:
            new_status = Transaction.Status.BLOQUEE
        elif fraud_score >= 0.50:
            new_status = Transaction.Status.SUSPECTE
        else:
            new_status = Transaction.Status.LEGITIME

        transaction.fraud_score = fraud_score
        transaction.fraud_label = fraud_label
        transaction.status = new_status
        transaction.save(update_fields=['fraud_score', 'fraud_label', 'status', 'updated_at'])

        # Sauvegarde des prédictions individuelles par modèle
        for model_name, model_result in result['model_results'].items():
            MLPrediction.objects.create(
                transaction=transaction,
                model_name=model_name,
                prediction=model_result['prediction'],
                confidence_score=model_result['score'],
                inference_time_ms=model_result['inference_ms'],
            )

        # Création d'une alerte si le score dépasse le seuil
        if alert_level:
            message = FraudDetector._build_alert_message(transaction, fraud_score, alert_level)
            alert, created = Alert.objects.get_or_create(
                transaction=transaction,
                defaults={
                    'level':       alert_level,
                    'fraud_score': fraud_score,
                    'message':     message,
                }
            )
            if created:
                logger.info(f"Alerte {alert_level} créée pour {transaction.transaction_id}")

        return result

    @staticmethod
    def _build_alert_message(transaction, score: float, level: str) -> str:
        """Génère un message d'alerte contextualisé."""
        messages = []

        if transaction.ratio_to_avg > 3:
            messages.append(f"montant {transaction.ratio_to_avg:.1f}x supérieur à la moyenne du client")
        if transaction.distance_from_home > 100:
            messages.append(f"transaction à {transaction.distance_from_home:.0f} km du domicile habituel")
        if transaction.is_foreign_ip:
            messages.append("IP étrangère détectée")
        if transaction.is_new_device:
            messages.append("nouvel appareil non reconnu")
        if transaction.failed_attempts_24h >= 3:
            messages.append(f"{transaction.failed_attempts_24h} tentatives échouées dans les dernières 24h")
        if transaction.freq_transactions_24h > 10:
            messages.append(f"fréquence anormale : {transaction.freq_transactions_24h} transactions en 24h")
        if transaction.is_night:
            messages.append("transaction nocturne inhabituelle")

        detail = " · ".join(messages) if messages else "comportement statistiquement anormal"
        return (
            f"Transaction {str(transaction.transaction_id)[:8].upper()} — "
            f"Score de fraude : {score:.0%} ({level}) — "
            f"{transaction.amount_formatted} via {transaction.get_transaction_type_display()} "
            f"depuis {transaction.city or 'lieu inconnu'}. "
            f"Signaux détectés : {detail}."
        )
