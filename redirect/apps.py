from django.apps import AppConfig


class RedirectConfig(AppConfig):
    name = 'redirect'

    def ready(self):
        import redirect.signals
