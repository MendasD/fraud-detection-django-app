from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField' # type du champ id auto généré pour les modèles de cette app
    name = 'apps.accounts' # chemin de l'app, doit correspondre à ce qui est dans INSTALLED_APPS dans settings/base.py
    verbose_name = 'Comptes Utilisateurs' # nom affiché dans l'interface admin de django
