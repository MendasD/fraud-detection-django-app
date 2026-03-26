from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('transactions/simulate/', views.TransactionSimulateView.as_view(), name='simulate'),
    path('stats/', views.StatsView.as_view(), name='stats'),
    path('ml/status/', views.ModelStatusView.as_view(), name='ml-status'),
    path('alerts/<int:alert_id>/update/', views.AlertUpdateView.as_view(), name='alert-update'),
     path('health/', views.HealthCheckView.as_view(), name='health'),
]
