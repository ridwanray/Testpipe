import os
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from organisation.models import Organisation
from django.core import mail
from user.tasks import send_new_user_email, send_registration_email, send_password_reset_email
from django.test import override_settings

overriden_settings_value = {
    "STATIC_URL" :'/static/',
    "STATICFILES_STORAGE" :"django.contrib.staticfiles.storage.StaticFilesStorage",
}


class CeleryUtilsTests(APITestCase):
    def setUp(self):
        org_data = {
            "name": "Org Name",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status": "ACTIVE"
        }
        org = Organisation.objects.create(**org_data)

        user_data = {
            "organisation": org,
            "email": "user@prunedge.com",
            "password": "passer",
            "verified": True,
            "firstname": "Ray",
            "lastname": "Inc"
        }

        user = get_user_model().objects.create_user(**user_data)

        user_data = {
            "id": user.id,
            "email": user.email,
            "fullname": f"{user.lastname} {user.firstname}"
        }

        self.user_info = user_data

    @override_settings(**overriden_settings_value)
    def test_send_new_user_email(self):
        print("mes....", os.environ.get("SENDER_EMAIL"))
        send_new_user_email(self.user_info)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Verify Email")
        self.assertEqual(mail.outbox[0].from_email,
                         os.environ.get("SENDER_EMAIL"))
        self.assertEqual(mail.outbox[0].to[0], self.user_info["email"])
        
    @override_settings(**overriden_settings_value)
    def test_send_registration_email(self):
        send_registration_email(self.user_info)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Account Verification")
        self.assertEqual(mail.outbox[0].from_email,
                         os.environ.get("SENDER_EMAIL"))
        self.assertEqual(mail.outbox[0].to[0], self.user_info["email"])

    @override_settings(**overriden_settings_value)
    def test_mail_sent_on_password_reset_request(self):
        send_password_reset_email(self.user_info)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Password Reset")
        self.assertEqual(mail.outbox[0].from_email,
                         os.environ.get("SENDER_EMAIL"))
        self.assertEqual(mail.outbox[0].to[0], self.user_info["email"])
