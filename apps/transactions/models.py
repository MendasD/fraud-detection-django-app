"""
Modèles de données centraux : Transaction, Alerte, Résultat ML.
"""

import uuid
from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    """
    Représente une transaction bancaire/mobile money dans le système Fortal Bank.
    Les colonnes couvrent tous les vecteurs nécessaires à la détection de fraude.
    """

    # Types de transactions 
    class TransactionType(models.TextChoices):
        WAVE          = 'WAVE',          'Wave'
        ORANGE_MONEY  = 'ORANGE_MONEY',  'Orange Money'
        FREE_MONEY    = 'FREE_MONEY',    'Free Money'
        VIREMENT      = 'VIREMENT',      'Virement Bancaire'
        RETRAIT_GAB   = 'RETRAIT_GAB',   'Retrait GAB'
        ACHAT_LIGNE   = 'ACHAT_LIGNE',   'Achat en Ligne'
        PAIEMENT_POS  = 'PAIEMENT_POS',  'Paiement POS'
        DEPOT         = 'DEPOT',         'Dépôt Espèces'

    # Catégories de marchands
    class MerchantCategory(models.TextChoices):
        ALIMENTATION   = 'ALIMENTATION',   'Alimentation & Épicerie'
        TELECOM        = 'TELECOM',        'Télécommunications'
        TRANSPORT      = 'TRANSPORT',      'Transport'
        SANTE          = 'SANTE',          'Santé & Pharmacie'
        EDUCATION      = 'EDUCATION',      'Éducation'
        IMMOBILIER     = 'IMMOBILIER',     'Immobilier'
        ELECTRONIQUE   = 'ELECTRONIQUE',   'Électronique'
        RESTAURANT     = 'RESTAURANT',     'Restaurant & Hôtellerie'
        CARBURANT      = 'CARBURANT',      'Station Service'
        TRANSFERT      = 'TRANSFERT',      'Transfert d\'Argent'
        AUTRE          = 'AUTRE',          'Autre'

    class DeviceType(models.TextChoices):
        MOBILE  = 'MOBILE',  'Mobile (Application)'
        WEB     = 'WEB',     'Navigateur Web'
        POS     = 'POS',     'Terminal POS'
        ATM     = 'ATM',     'Guichet Automatique'
        USSD    = 'USSD',    'USSD (*XXX#)'

    class Status(models.TextChoices):
        EN_ATTENTE  = 'EN_ATTENTE',  'En attente d\'analyse'
        LEGITIME    = 'LEGITIME',    'Transaction légitime'
        SUSPECTE    = 'SUSPECTE',    'Suspecte — sous surveillance'
        FRAUDULEUSE = 'FRAUDULEUSE', 'Fraude confirmée'
        BLOQUEE     = 'BLOQUEE',     'Bloquée automatiquement'

    # Identifiant unique
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='ID Transaction',
    )

    # Horodatage
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Horodatage',
    )

    # Montant en FCFA
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name='Montant (FCFA)',
    )

    # Expéditeur
    sender_id     = models.CharField(max_length=50, verbose_name='ID Expéditeur')
    sender_phone  = models.CharField(max_length=20, blank=True, verbose_name='Téléphone Expéditeur')
    sender_name   = models.CharField(max_length=100, blank=True, verbose_name='Nom Expéditeur')

    # Destinataire
    receiver_id    = models.CharField(max_length=50, verbose_name='ID Destinataire')
    receiver_phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone Destinataire')
    receiver_name  = models.CharField(max_length=100, blank=True, verbose_name='Nom Destinataire')

    # Type et canal
    transaction_type    = models.CharField(max_length=20, choices=TransactionType.choices, verbose_name='Type')
    merchant_category   = models.CharField(max_length=20, choices=MerchantCategory.choices, default=MerchantCategory.AUTRE, verbose_name='Catégorie Marchand')
    device_type         = models.CharField(max_length=10, choices=DeviceType.choices, verbose_name='Appareil')

    # Géolocalisation
    location_lat    = models.FloatField(null=True, blank=True, verbose_name='Latitude')
    location_lon    = models.FloatField(null=True, blank=True, verbose_name='Longitude')
    city            = models.CharField(max_length=100, blank=True, verbose_name='Ville')
    country_code    = models.CharField(max_length=5, default='SN', verbose_name='Code Pays')

    # Contexte temporel
    hour_of_day     = models.IntegerField(verbose_name='Heure de la journée')
    day_of_week     = models.IntegerField(verbose_name='Jour de la semaine (0=Lundi)')
    is_weekend      = models.BooleanField(default=False, verbose_name='Week-end')
    is_night        = models.BooleanField(default=False, verbose_name='Transaction nocturne')

    # Signaux comportementaux
    distance_from_home      = models.FloatField(default=0.0, verbose_name='Distance domicile (km)')
    is_foreign_ip           = models.BooleanField(default=False, verbose_name='IP Étrangère')
    is_new_device           = models.BooleanField(default=False, verbose_name='Nouvel Appareil')
    failed_attempts_24h     = models.IntegerField(default=0, verbose_name='Tentatives échouées 24h')
    freq_transactions_24h   = models.IntegerField(default=1, verbose_name='Nb transactions 24h')
    freq_transactions_7d    = models.IntegerField(default=1, verbose_name='Nb transactions 7j')

    # Historique financier de l'expéditeur
    avg_amount_30d      = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Montant moyen 30j')
    max_amount_30d      = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Montant max 30j')
    ratio_to_avg        = models.FloatField(default=1.0, verbose_name='Ratio montant / moyenne')

    # Réseau de transactions
    nb_unique_receivers_7d  = models.IntegerField(default=1, verbose_name='Destinataires uniques 7j')
    is_first_transaction    = models.BooleanField(default=False, verbose_name='Première transaction')

    # Résultat de l'analyse
    status          = models.CharField(max_length=15, choices=Status.choices, default=Status.EN_ATTENTE, db_index=True, verbose_name='Statut')
    is_fraud        = models.BooleanField(null=True, blank=True, verbose_name='Est une fraude (ground truth)')
    fraud_score     = models.FloatField(null=True, blank=True, verbose_name='Score de fraude (0-1)')
    fraud_label     = models.CharField(max_length=20, blank=True, verbose_name='Label fraude prédit')

    # Métadonnées
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    is_simulated = models.BooleanField(default=False, verbose_name='Donnée simulée')

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['status']),
            models.Index(fields=['sender_id']),
            models.Index(fields=['is_fraud']),
            models.Index(fields=['fraud_score']),
        ]

    def __str__(self):
        return f"TXN-{str(self.transaction_id)[:8].upper()} | {self.amount:,} FCFA | {self.get_transaction_type_display()}"

    @property
    def amount_formatted(self):
        return f"{int(self.amount):,} FCFA"

    @property
    def alert_level(self):
        """Retourne le niveau d'alerte basé sur le score de fraude."""
        if self.fraud_score is None:
            return None
        if self.fraud_score >= 0.85:
            return 'CRITIQUE'
        if self.fraud_score >= 0.65:
            return 'ELEVE'
        if self.fraud_score >= 0.50:
            return 'MOYEN'
        return None


class Alert(models.Model):
    """
    Alerte générée automatiquement lorsqu'une transaction dépasse
    le seuil de probabilité de fraude configuré.
    """

    class Level(models.TextChoices):
        CRITIQUE = 'CRITIQUE', 'Critique (>=85%)'
        ELEVE    = 'ELEVE',    'Élevé (>=65%)'
        MOYEN    = 'MOYEN',    'Moyen (>=50%)'

    class AlertStatus(models.TextChoices):
        NOUVELLE    = 'NOUVELLE',    'Nouvelle'
        EN_COURS    = 'EN_COURS',    'En cours de traitement'
        RESOLUE     = 'RESOLUE',     'Résolue'
        FAUX_POSITIF = 'FAUX_POSITIF', 'Faux positif'

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='alert',
        verbose_name='Transaction',
    )
    level           = models.CharField(max_length=10, choices=Level.choices, verbose_name='Niveau')
    fraud_score     = models.FloatField(verbose_name='Score de fraude')
    message         = models.TextField(verbose_name='Message d\'alerte')
    status          = models.CharField(max_length=15, choices=AlertStatus.choices, default=AlertStatus.NOUVELLE, verbose_name='Statut')
    resolved_by     = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Résolu par')
    resolved_at     = models.DateTimeField(null=True, blank=True, verbose_name='Résolu le')
    resolution_note = models.TextField(blank=True, verbose_name='Note de résolution')
    created_at      = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Alerte'
        verbose_name_plural = 'Alertes'
        ordering = ['-created_at']

    def __str__(self):
        return f"ALERTE {self.level} — {self.transaction} ({self.fraud_score:.0%})"


class MLPrediction(models.Model):
    """
    Détail des prédictions de chaque modèle ML pour une transaction.
    Permet l'audit et la comparaison des modèles.
    """

    transaction         = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='ml_predictions')
    model_name          = models.CharField(max_length=50, verbose_name='Modèle ML')
    model_version       = models.CharField(max_length=20, default='1.0', verbose_name='Version')
    prediction          = models.IntegerField(verbose_name='Prédiction (0=normal, 1=fraude, -1=anomalie)')
    confidence_score    = models.FloatField(verbose_name='Score de confiance')
    inference_time_ms   = models.FloatField(verbose_name='Temps d\'inférence (ms)')
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Prédiction ML'
        verbose_name_plural = 'Prédictions ML'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.model_name} → {self.prediction} ({self.confidence_score:.2%})"
