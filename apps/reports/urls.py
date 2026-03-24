"""
apps/reports/urls.py
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('',         views.ReportGenerateView.as_view(),  name='generate'),
    path('download/', views.ReportDownloadView.as_view(), name='download'),
]
