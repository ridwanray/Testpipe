from django.dispatch import receiver
from .models import Token


def generate_token(sender, instance, **kwargs):
    instance.generate()
