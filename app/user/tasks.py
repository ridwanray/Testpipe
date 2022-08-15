from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import get_template
from django.core.management import call_command
from .utils import send_email
from core.celery import APP


@APP.task()
def send_new_user_email(email_data):
    html_template = get_template("emails/new_user_welcome_template.html")
    text_template = get_template("emails/new_user_welcome_template.txt")
    html_alternative = html_template.render(email_data)
    text_alternative = text_template.render(email_data)
    send_email("Verify Email", email_data["email"], html_alternative, text_alternative)


@APP.task()
def send_registration_email(email_data):
    html_template = get_template("emails/account_verification_template.html")
    text_template = get_template("emails/account_verification_template.txt")
    html_alternative = html_template.render(email_data)
    text_alternative = text_template.render(email_data)
    send_email(
        "Account Verification", email_data["email"], html_alternative, text_alternative
    )


@APP.task()
def send_password_reset_email(email_data):
    html_template = get_template("emails/password_reset_template.html")
    text_template = get_template("emails/password_reset_template.txt")
    html_alternative = html_template.render(email_data)
    text_alternative = text_template.render(email_data)
    send_email(
        "Password Reset", email_data["email"], html_alternative, text_alternative
    )
