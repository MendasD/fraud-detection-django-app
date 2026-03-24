"""
apps/reports/views.py
"""

from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView
from django.utils import timezone


class ReportGenerateView(LoginRequiredMixin, TemplateView):
    """Page de configuration et téléchargement du rapport PDF."""
    template_name = 'reports/generate.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.transactions.models import Transaction
        ctx['total_txn'] = Transaction.objects.count()
        ctx['oldest_date'] = Transaction.objects.order_by('timestamp').first()
        ctx['report_contents'] = [
            "Page de couverture avec KPIs",
            "Résumé exécutif",
            "Graphique d'évolution des fraudes",
            "Analyse géographique par ville",
            "Top 20 transactions frauduleuses",
            "Recommandations personnalisées",
        ]
        return ctx


class ReportDownloadView(LoginRequiredMixin, View):
    """Génère et télécharge le rapport PDF."""

    def get(self, request):
        period_days = int(request.GET.get('days', 30))
        period_days = max(1, min(period_days, 365))

        try:
            from .pdf_generator import generate_fraud_report
            pdf_bytes = generate_fraud_report(period_days=period_days)

            filename = f"fortal_bank_rapport_fraudes_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(pdf_bytes)
            return response

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
