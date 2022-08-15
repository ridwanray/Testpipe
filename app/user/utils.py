from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import get_template
from django.core.files import File
from urllib.request import urlretrieve
from .models import Token, User
from django.utils.crypto import get_random_string


def send_email(subject, email_from, html_alternative, text_alternative):
    msg = EmailMultiAlternatives(
        subject, text_alternative, settings.EMAIL_FROM, [email_from]
    )
    msg.attach_alternative(html_alternative, "text/html")
    msg.send(fail_silently=False)


async def create_file_from_image(url):
    return File(open(url, "rb"))


def create_token_and_send_user_email(user, organisation=None):
    from .tasks import send_new_user_email

    token, _ = Token.objects.update_or_create(
        user=user,
        token_type="ACCOUNT_VERIFICATION",
        defaults={
            "user": user,
            "token_type": "ACCOUNT_VERIFICATION",
            "token": get_random_string(120),
        },
    )
    # token.verify_user()
    # token.save()
    user_data = {
        "id": user.id,
        "email": user.email,
        "fullname": f"{user.lastname} {user.firstname}",
        "url": f"https://{organisation.subdomain}.{settings.CLIENT_URL}/user-signup/?token={token.token}"
        if organisation
        else f"https://{settings.CLIENT_URL}/user-signup/?token={token.token}",
    }
    send_new_user_email.delay(user_data)
