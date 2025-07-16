from django.apps import AppConfig


class MarketplacesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplaces'
    verbose_name = 'Marketplaces'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        # Import signals here if needed in the future
        pass
