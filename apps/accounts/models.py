"""
apps/accounts/models.py
Modèle utilisateur personnalisé pour Fortal Bank.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilisateur étendu avec rôles spécifiques au système de détection de fraudes.
    """

    class Role(models.TextChoices):
        ADMIN        = 'ADMIN',        'Administrateur'
        ANALYSTE     = 'ANALYSTE',     'Analyste Fraude'
        SUPERVISEUR  = 'SUPERVISEUR',  'Superviseur'
        AUDITEUR     = 'AUDITEUR',     'Auditeur'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ANALYSTE,
        verbose_name='Rôle',
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Département',
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Téléphone',
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Avatar',
    )
    receive_alerts = models.BooleanField(
        default=True,
        verbose_name='Recevoir les alertes temps réel',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_analyste(self):
        return self.role == self.Role.ANALYSTE
