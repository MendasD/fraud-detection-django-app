"""
Routage principal de l'application Fortal Bank Fraud Detection.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Interface d'administration Django
    path('admin/', admin.site.urls),

    # Authentification (login, logout)
    path('accounts/', include('apps.accounts.urls')),

    # Dashboard principal
    path('dashboard/', include('apps.dashboard.urls')),

    # API REST
    path('api/v1/', include('apps.api.urls')),

    # Rapports PDF
    path('reports/', include('apps.reports.urls')),

    # Racine : redirection vers dashboard (pas de double include)
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personnalisation de l'admin
admin.site.site_header = 'Fortal Bank - Administration'
admin.site.site_title  = 'Fortal Bank Admin'
admin.site.index_title = 'Tableau de bord administrateur'
