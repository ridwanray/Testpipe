from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from notification.models import Notification
from organisation.models import Organisation
from user.models import User
from .enums import NOTIFICATION_TYPES, NOTIFICATION_ACTIONS


class RetrieveNotificationTests(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        org_data = {
            "name": "Prun",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status": "ACTIVE"
        }

        org = Organisation.objects.create(**org_data)

        superadmin_user_data = {
            "organisation": org,
            "email": "super@org.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
            "firstname": "First",
            "lastname": "Last",
        }

        super_admin_user = get_user_model().objects.create_user(**superadmin_user_data)

        # create objects for another org instance
        onboarded_org_data = {
            "name": "Onboarded Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "onboarded.hrms.com",
            "status": "ACTIVE"
        }

        onboarded_org = Organisation.objects.create(**onboarded_org_data)

        employee_user_data = {
            "organisation": onboarded_org,
            "email": "employee@org.com",
            "password": "employee",
            "verified": True,
            "roles": ["EMPLOYEE"],
            "firstname": "First",
            "lastname": "Last",
        }

        employee_user = get_user_model().objects.create_user(**employee_user_data)

        hr_admin_user_data = {
            "organisation": onboarded_org,
            "email": "hr@org.com",
            "password": "hr",
            "verified": True,
            "roles": ["HR_ADMIN"],
            "firstname": "First",
            "lastname": "Last",
        }

        hr = get_user_model().objects.create_user(**hr_admin_user_data)
        # First 2 notifications target SUPERADMIN
        notification1 = {
            "organisation": org,
            "actor": super_admin_user,
            "description": "Short Desciption",
            "action": "APPROVED",
            "notif_type": "Leave",
            "recipient_level": "SUPERADMIN"
        }

        super_admin_notif = Notification.objects.create(**notification1)
        self.super_admin_notif_id = super_admin_notif.id
        notification2 = {
            "organisation": org,
            "actor": super_admin_user,
            "description": "",
            "action": "DECLINED",
            "notif_type": "Leave",
            "recipient_level": "SUPERADMIN"
        }

        Notification.objects.create(**notification2)
        # Third notification targets just the HR ADMIN
        notification3a = {
            "organisation": org,
            "actor": hr,
            "description": "",
            "action": "DECLINED",
            "notif_type": "Leave",
            "recipient_level": "HR_ADMIN"
        }

        notif3a = Notification.objects.create(**notification3a)
        notif3a.read_users.set([hr.id])

        self.notification3_id = notif3a.id

        notification3b = {
            "organisation": onboarded_org,
            "actor": hr,
            "description": "",
            "action": "DECLINED",
            "notif_type": "Leave",
            "recipient_level": "HR_ADMIN"
        }

        notif3b = Notification.objects.create(**notification3b)
        notif3b.read_users.set([hr.id])

        # 4th notification targets just the Actor and hr
        notification4 = {
            "organisation": onboarded_org,
            "actor": employee_user,
            "description": "",
            "action": "APPLIED",
            "notif_type": "Leave",
            "recipient_level": "HR_ADMIN & ACTOR"
        }

        employee_notif = Notification.objects.create(**notification4)
        self.employee_notif_id = employee_notif.id

        # 5th notification targets all
        notification5 = {
            "organisation": org,
            "actor": super_admin_user,
            "description": "",
            "action": "ANNOUNCEMENT",
            "notif_type": "Leave",
            "recipient_level": "ALL"
        }

        Notification.objects.create(**notification5)

    def super_admin_authenticator(self):
        '''Authenticate  super admin'''
        url = reverse('user:login')
        data = {
            "email": "super@org.com",
            "password": "super",
        }

        response = self.client.post(url, data, format='json')
        token = response.json()['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

    def hr_admin_authenticator(self):
        '''Authenticate hr  admin'''
        url = reverse('user:login')
        data = {
            "email": "hr@org.com",
            "password": "hr",
        }

        response = self.client.post(url, data, format='json')
        token = response.json()['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

    def employee_authenticator(self):
        '''Authenticate hr  admin'''
        url = reverse('user:login')
        data = {
            "email": "employee@org.com",
            "password": "employee",
        }

        response = self.client.post(url, data, format='json')
        token = response.json()['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

    def test_super_admin_user_can_retrieve_notif(self):
        self.super_admin_authenticator()
        url = reverse("notification:notification-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check total no. of notifications returned i.e.recipient_level=SUPERADMIN&ALL
        self.assertEqual(response.json()["total"], 3)
        self.assertEqual(len(response.json()["results"]), 3)
        # Check that those notifications are unread for this user
        self.assertEqual(response.json()["results"][0]["is_read"], False)
        self.assertEqual(response.json()["results"][1]["is_read"], False)
        self.assertEqual(response.json()["results"][2]["is_read"], False)

    def test_hr_admin_can_retrieve_notif(self):
        self.hr_admin_authenticator()
        url = reverse("notification:notification-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check total no. of notifications returned i.e.recipient_level=HR_ADMIN,ALL,HR_ADMIN & ACTOR
        self.assertEqual(response.json()["total"], 3)
        self.assertEqual(len(response.json()["results"]), 3)
        # Test that two of the notifications are read note:-created_by ordering
        self.assertEqual(response.json()["results"][0]["is_read"], False)
        self.assertEqual(response.json()["results"][1]["is_read"], True)
        self.assertEqual(response.json()["results"][2]["is_read"], True)

    def test_employee_user_can_retrieve_notif(self):
        self.employee_authenticator()
        url = reverse("notification:notification-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check total no. of notifications returned.recipient_level=actor,all,hr&actor
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(len(response.json()["results"]), 1)
        # Check the returned notification is unread
        self.assertEqual(response.json()["results"][0]["is_read"], False)

    def test_user_can_read_unread_notif(self):
        self.hr_admin_authenticator()
        url = reverse("notification:notification-update-read-status",
                      kwargs={"pk": self.notification3_id})

        data = {
            "is_read": True
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]['is_read'], False)

    def test_read_unread_denied(self):
        """Restrict a user trying to read/unread not belonging notifications"""
        self.super_admin_authenticator()
        url = reverse("notification:notification-update-read-status",
                      kwargs={"pk": self.notification3_id})

        data = {
            "is_read": True
        }
        # super admin accesing not belonging notification
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.hr_admin_authenticator()
        url2 = reverse("notification:notification-update-read-status",
                       kwargs={"pk": self.super_admin_notif_id})
        data2 = {
            "is_read": True
        }

        # hr admin accessing not belonging notification
        response2 = self.client.put(url2, data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_super_admin_read_unread(self):
        self.super_admin_authenticator()
        url = reverse("notification:notification-update-read-status",
                      kwargs={"pk": self.super_admin_notif_id})
        data = {
            "is_read": False
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["is_read"], True)

    def test_employee_read_unread(self):
        self.employee_authenticator()
        url = reverse("notification:notification-update-read-status",
                      kwargs={"pk": self.employee_notif_id})
        data = {
            "is_read": False
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["is_read"], True)
