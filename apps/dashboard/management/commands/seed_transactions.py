"""
apps/dashboard/management/commands/seed_transactions.py

Peuple la base de données avec des transactions historiques à partir
du CSV généré ou en les générant à la volée.
Utile pour avoir un dashboard immédiatement exploitable.

Usage :
    python manage.py seed_transactions
    python manage.py seed_transactions --count 5000
    python manage.py seed_transactions --count 2000 --fraud-ratio 0.12
"""

import os
import sys
import random
import logging
import warnings
from datetime import timedelta
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction as db_transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialise la base de données avec des transactions historiques analysées'

    def add_arguments(self, parser):
        parser.add_argument('--count',       type=int,   default=3000, help='Nombre de transactions à insérer')
        parser.add_argument('--fraud-ratio', type=float, default=0.10, help='Ratio de fraudes (défaut: 0.10)')
        parser.add_argument('--days-back',   type=int,   default=30,   help='Répartir sur N jours passés')
        parser.add_argument('--csv',         type=str,   default='data/transactions.csv', help='Chemin vers le CSV')

    def handle(self, *args, **options):
        count       = options['count']
        fraud_ratio = options['fraud_ratio']
        days_back   = options['days_back']
        csv_path    = options['csv']

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'  FORTAL BANK — Initialisation de la base de données\n'
            f'  {count:,} transactions | {fraud_ratio:.0%} fraudes | {days_back} jours\n'
            f'{"="*60}\n'
        ))

        # Chargement des données
        records = self._load_data(csv_path, count, fraud_ratio)

        self.stdout.write(f"Insertion de {len(records):,} transactions en base...")
        self._insert_transactions(records, days_back)

        # Statistiques finales
        from apps.transactions.models import Transaction, Alert
        total   = Transaction.objects.count()
        frauds  = Transaction.objects.filter(status__in=['SUSPECTE', 'BLOQUEE']).count()
        alerts  = Alert.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'  Base initialisée :\n'
            f'  Total transactions : {total:,}\n'
            f'  Transactions suspectes/bloquées : {frauds:,}\n'
            f'  Alertes créées : {alerts:,}\n'
            f'{"="*60}'
        ))

    def _load_data(self, csv_path, count, fraud_ratio):
        """Charge depuis le CSV ou génère les données."""
        if os.path.exists(csv_path):
            self.stdout.write(f"Chargement depuis {csv_path}...")
            import pandas as pd
            df = pd.read_csv(csv_path)
            # Mélange et sélection
            df = df.sample(min(count, len(df)), random_state=42)
            return df.to_dict('records')
        else:
            self.stdout.write(f"CSV introuvable, génération de {count:,} transactions...")
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ))))
            from ml_engine.data_generator import generate_dataset
            df = generate_dataset(n_samples=count, fraud_ratio=fraud_ratio)
            return df.to_dict('records')

    @db_transaction.atomic
    def _insert_transactions(self, records, days_back):
        """Insère les transactions avec timestamps répartis historiquement."""
        from apps.transactions.models import Transaction
        from apps.ml.fraud_detector import FraudDetector
        from apps.ml.model_service import ModelService

        ml_ready = ModelService.is_ready()
        if not ml_ready:
            self.stdout.write(self.style.WARNING(
                "Modèles ML non chargés — les transactions seront insérées sans analyse de fraude.\n"
                "Lancez 'python ml_engine/train_models.py' puis réessayez."
            ))

        now = timezone.now()
        total = len(records)
        batch_size = 50

        for i, rec in enumerate(records):
            # Timestamp historique réparti sur days_back jours
            days_offset  = random.uniform(0, days_back)
            hours_offset = random.uniform(0, 24)
            ts = now - timedelta(days=days_offset, hours=hours_offset)

            # Heure et jour depuis le timestamp
            hour_of_day = ts.hour
            day_of_week = ts.weekday()
            is_night    = hour_of_day < 6 or hour_of_day >= 23
            is_weekend  = day_of_week >= 5

            # Créer l'objet Transaction
            txn = Transaction(
                timestamp             = ts,
                amount                = int(rec.get('amount', 10000)),
                sender_id             = str(rec.get('sender_id', 'FB000000')),
                sender_phone          = str(rec.get('sender_phone', '')),
                sender_name           = str(rec.get('sender_name', '')),
                receiver_id           = str(rec.get('receiver_id', 'FB000001')),
                receiver_phone        = str(rec.get('receiver_phone', '')),
                receiver_name         = str(rec.get('receiver_name', '')),
                transaction_type      = str(rec.get('transaction_type', 'WAVE')),
                merchant_category     = str(rec.get('merchant_category', 'AUTRE')),
                device_type           = str(rec.get('device_type', 'MOBILE')),
                location_lat          = rec.get('location_lat'),
                location_lon          = rec.get('location_lon'),
                city                  = str(rec.get('city', '')),
                country_code          = str(rec.get('country_code', 'SN')),
                hour_of_day           = hour_of_day,
                day_of_week           = day_of_week,
                is_weekend            = is_weekend,
                is_night              = is_night,
                distance_from_home    = float(rec.get('distance_from_home', 0)),
                is_foreign_ip         = bool(rec.get('is_foreign_ip', 0)),
                is_new_device         = bool(rec.get('is_new_device', 0)),
                failed_attempts_24h   = int(rec.get('failed_attempts_24h', 0)),
                freq_transactions_24h = int(rec.get('freq_transactions_24h', 1)),
                freq_transactions_7d  = int(rec.get('freq_transactions_7d', 1)),
                avg_amount_30d        = int(rec.get('avg_amount_30d', 10000)),
                max_amount_30d        = int(rec.get('max_amount_30d', 50000)),
                ratio_to_avg          = float(rec.get('ratio_to_avg', 1.0)),
                nb_unique_receivers_7d = int(rec.get('nb_unique_receivers_7d', 1)),
                is_first_transaction  = bool(rec.get('is_first_transaction', 0)),
                is_fraud              = bool(rec.get('is_fraud', 0)),
                is_simulated          = True,
            )
            txn.save()

            # Analyse ML si modèles disponibles
            if ml_ready:
                FraudDetector.analyze(txn)

            # Progression
            if (i + 1) % batch_size == 0 or (i + 1) == total:
                pct = (i + 1) / total * 100
                bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
                self.stdout.write(
                    f'\r  [{bar}] {pct:.0f}% — {i+1:,}/{total:,}',
                    ending=''
                )
                self.stdout.flush()

        self.stdout.write('')
