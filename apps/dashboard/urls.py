"""
apps/dashboard/urls.py
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',               views.DashboardIndexView.as_view(),  name='index'),
    path('transactions/',  views.TransactionListView.as_view(), name='transactions'),
    path('alerts/',        views.AlertListView.as_view(),       name='alerts'),
    path('map/',           views.MapView.as_view(),             name='map'),
    path('api/stats/',     views.StatsAPIView.as_view(),        name='stats-api'),
]
