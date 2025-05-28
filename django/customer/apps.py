from django.apps import AppConfig
# from 


class CustomerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customer'

    # def ready(self):
    #     import drf_keycloak.schema  # noqa: E402