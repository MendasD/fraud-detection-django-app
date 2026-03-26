"""
WebSocket Consumer pour la diffusion temps réel des alertes et transactions.
Utilise Django Channels pour maintenir des connexions persistantes avec le dashboard.

Fonctionnement :
  - Chaque client connecté au dashboard rejoint le groupe 'fraud_alerts'
  - Quand une nouvelle transaction est analysée, le FraudDetector envoie
    un message à ce groupe via channel_layer.group_send()
  - Tous les clients connectés reçoivent instantanément la mise à jour
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

# Nom du groupe de diffusion — tous les clients dashboard s'y abonnent
FRAUD_ALERTS_GROUP = 'fraud_alerts'


class FraudAlertConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour les alertes de fraude en temps réel.
    Chaque connexion (onglet/utilisateur) rejoint le groupe fraud_alerts.
    """

    async def connect(self):
        """
        Connexion WebSocket établie.
        Ajoute ce client au groupe de diffusion fraud_alerts.
        """
        await self.channel_layer.group_add(
            FRAUD_ALERTS_GROUP,
            self.channel_name
        )
        await self.accept()
        logger.info(f"Client WebSocket connecté : {self.channel_name}")

        # Message de bienvenue pour confirmer la connexion
        await self.send(text_data=json.dumps({
            'type':    'connection_established',
            'message': 'Connecté au flux de détection de fraudes Fortal Bank',
        }))

    async def disconnect(self, close_code):
        """
        Déconnexion du client.
        Retire ce client du groupe de diffusion.
        """
        await self.channel_layer.group_discard(
            FRAUD_ALERTS_GROUP,
            self.channel_name
        )
        logger.info(f"Client WebSocket déconnecté : {self.channel_name} (code: {close_code})")

    async def receive(self, text_data):
        """
        Message reçu depuis le client (ex: acquittement d'alerte).
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'ping':
                # Keep-alive ping
                await self.send(text_data=json.dumps({'type': 'pong'}))

            elif msg_type == 'acknowledge_alert':
                # Le client a acquitté une alerte
                alert_id = data.get('alert_id')
                logger.info(f"Alerte {alert_id} acquittée par {self.channel_name}")

        except json.JSONDecodeError:
            logger.warning(f"Message WebSocket invalide reçu de {self.channel_name}")

    # Gestionnaires de messages de groupe
    async def fraud_alert(self, event):
        """
        Reçoit un événement 'fraud_alert' depuis le groupe
        et le transmet au client WebSocket connecté.
        """
        await self.send(text_data=json.dumps({
            'type':        'fraud_alert',
            'transaction': event['transaction'],
            'alert':       event['alert'],
            'timestamp':   event['timestamp'],
        }))

    async def transaction_processed(self, event):
        """
        Notifie qu'une transaction vient d'être analysée
        (même légitime — pour le compteur du dashboard).
        """
        await self.send(text_data=json.dumps({
            'type':        'transaction_processed',
            'transaction': event['transaction'],
            'timestamp':   event['timestamp'],
        }))

    async def stats_update(self, event):
        """
        Mise à jour des statistiques agrégées du dashboard.
        Envoyée toutes les N transactions pour rafraîchir les jauges.
        """
        await self.send(text_data=json.dumps({
            'type':  'stats_update',
            'stats': event['stats'],
        }))
