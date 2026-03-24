"""
apps/transactions/admin.py
"""

from django.contrib import admin
from .models import Transaction, Alert, MLPrediction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ('transaction_id', 'amount_formatted', 'transaction_type', 'city', 'status', 'fraud_score', 'timestamp')
    list_filter   = ('status', 'transaction_type', 'is_fraud', 'city', 'is_simulated')
    search_fields = ('transaction_id', 'sender_id', 'receiver_id', 'sender_phone')
    readonly_fields = ('transaction_id', 'created_at', 'updated_at')
    ordering      = ['-timestamp']

    def amount_formatted(self, obj):
        return obj.amount_formatted
    amount_formatted.short_description = 'Montant'


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display  = ('transaction', 'level', 'fraud_score', 'status', 'created_at')
    list_filter   = ('level', 'status')
    ordering      = ['-created_at']


@admin.register(MLPrediction)
class MLPredictionAdmin(admin.ModelAdmin):
    list_display  = ('transaction', 'model_name', 'prediction', 'confidence_score', 'inference_time_ms')
    list_filter   = ('model_name',)
    ordering      = ['-created_at']
