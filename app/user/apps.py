from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save

# from app.user.models import Token
# from app.user.signals import generate_token


class UserConfig(AppConfig):
    name = "user"
    verbose_name = _("user")

    # def ready(self):
    #     post_save.connect(generate_token, sender=Token)
