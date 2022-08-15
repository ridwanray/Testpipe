import shutil
import os
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from employee.models import Employee
from organisation.models import Organisation
from tempfile import NamedTemporaryFile, gettempdir
from PIL import Image
from . import models
from django.conf import settings

TEST_DIR = "test_data"

overriden_settings_value = {
    "MEDIA_ROOT": TEST_DIR + "/expense_claim/",
    "DEFAULT_FILE_STORAGE": "django.core.files.storage.FileSystemStorage",
}


class EmployeeClaimCreateTests(APITestCase):
    @override_settings(USE_TZ=False)
    def setUp(self):
        org_data = {
            "name": "Prun",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status":"ACTIVE"
        }

        org = Organisation.objects.create(**org_data)

        user_data = {
            "organisation": org,
            "email": "ridwan.yusuf@prunedge.com",
            "password": "passer",
            "verified": True,
        }

        user = get_user_model().objects.create_user(**user_data)

        employee_data = {
            "user": user,
            "organisation": org,
            "firstname": "Ray",
            "lastname": "Inc",
            "work_email": "ray@prunedge.com",
            "job_title": "Engineer",
            # "employment_category": "FULL TIME",
            "employment_status": "FULL TIME",
        }

        Employee.objects.create(**employee_data)

        self.authenticator()

    @classmethod
    def tearDownClass(cls):
        # remove expense_claims dir i.e the created files
        try:
            shutil.rmtree(TEST_DIR)
            super().tearDownClass()
        except OSError as e:
            print(e)

    def authenticator(self):
        """Authenticate incoming request"""
        url = reverse("user:login")
        data = {
            "email": "ridwan.yusuf@prunedge.com",
            "password": "passer",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_can_create_new_claim(self):
        url = reverse("claims:expense-list")
        data = {
            "title": "Sample Title",
            "description": "Sample Descript.",
            "start_date": "2019-04-30",
            "end_date": "2020-04-30",
            "total_amount": 5000,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(**overriden_settings_value)
    def test_can_create_claim_with_documents(self):
        url = reverse("claims:expense-list")

        f = NamedTemporaryFile()
        f.name += ".png"
        image_1 = Image.new("RGBA", (200, 200), "white")
        image_1.save(f.name)
        image_1_file = open(f.name, "rb")

        g = NamedTemporaryFile()
        g.name += ".png"
        image_2 = Image.new("RGBA", (200, 200), "white")
        image_2.save(g.name)
        image_2_file = open(g.name, "rb")

        data = {
            "title": "Sample Title",
            "description": "Sample Descript.",
            "start_date": "2019-04-30",
            "end_date": "2020-04-30",
            "total_amount": 5000,
            "documents": [image_1_file, image_2_file],
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # check number of documents returned
        self.assertEqual(len(response.json()["documents"]), 2)


class EmployeeClaimPermissionTests(APITestCase):
    @override_settings(USE_TZ=False)
    def setUp(self):
        user_data = {
            "email": "superadmin@prunedge.com",
            "password": "passer",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }

        user = get_user_model().objects.create_user(**user_data)

        self.superadmin_authenticator()

    def superadmin_authenticator(self):
        """Authenticate incoming request"""
        url = reverse("user:login")
        data = {
            "email": "superadmin@prunedge.com",
            "password": "passer",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_super_admin_denied_claim_creation(self):

        url = reverse("claims:expense-list")
        data = {
            "title": "Sample Title",
            "description": "Sample Descript.",
            "start_date": "2019-04-30",
            "end_date": "2020-04-30",
            "total_amount": 5000,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class EmployeeClaimUpdateTests(APITestCase):
    def setUp(self):

        org_data = {
            "name": "Prun",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status":"ACTIVE"
        }

        org = Organisation.objects.create(**org_data)

        user_data = {
            "organisation": org,
            "email": "ridwan.yusuf@prunedge.com",
            "password": "passer",
            "verified": True,
        }

        user = get_user_model().objects.create_user(**user_data)

        employee_data = {
            "user": user,
            "organisation": org,
            "firstname": "Ray",
            "lastname": "Inc",
            "work_email": "ray@prunedge.com",
            "job_title": "Engineer",
            # "employment_category": "FULL TIME",
            "employment_status": "FULL TIME",
        }

        employee = Employee.objects.create(**employee_data)

        expense_claim_data = {
            "employee": employee,
            "title": "Title",
            "description": "Description",
            "start_date": "2020-04-30",
            "end_date": "2022-04-30",
            "total_amount": 500,
        }

        expense_claim = models.Expense.objects.create(**expense_claim_data)
        self.expense_created_id = expense_claim.id
        self.authenticator()

    @classmethod
    def tearDownClass(cls):
        # remove expense_claims dir i.e the created files
        try:
            shutil.rmtree(TEST_DIR)
            super().tearDownClass()
        except OSError as e:
            print(e)

    def authenticator(self):
        """Authenticate incoming request"""
        url = reverse("user:login")
        data = {
            "email": "ridwan.yusuf@prunedge.com",
            "password": "passer",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_can_update_expense_claim(self):
        url = reverse("claims:expense-detail", kwargs={"pk": self.expense_created_id})
        data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "total_amount": 2900,
            "start_date": "2010-04-30",
            "end_date": "2010-04-30",
        }

        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], "Updated Title")
        self.assertEqual(response.json()["description"], "Updated Description")

    def test_can_delete_expense_claim(self):
        url = reverse("claims:expense-detail", kwargs={"pk": self.expense_created_id})

        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            models.Expense.objects.filter(id=str(self.expense_created_id)).count(), 0
        )

    @override_settings(**overriden_settings_value)
    def test_can_update_expense_claim_with_doc(self):
        url = reverse("claims:expense-detail", kwargs={"pk": self.expense_created_id})

        f = NamedTemporaryFile()
        f.name += ".png"
        image_1 = Image.new("RGBA", (200, 200), "white")
        image_1.save(f.name)
        image_1_file = open(f.name, "rb")

        data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "total_amount": 2900,
            "start_date": "2010-04-30",
            "end_date": "2010-04-30",
            "documents": image_1_file,
        }

        response = self.client.put(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["start_date"], "2010-04-30")
        self.assertEqual(len(response.json()["documents"]), 1)

    def test_can_update_expense_claim_status(self):
        url = reverse(
            "claims:expense-approve-claim", kwargs={"pk": self.expense_created_id}
        )
        req_body = {"status": "PAID"}
        response = self.client.post(url, req_body, format="json")
        self.assertEqual(response.json()["data"]["status"], "PAID")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EmployeeExpenseClaimRetrieveTests(APITestCase):
    """Retrieves only Expenses for the company of the authenticated user"""

    settings.USE_TZ = False

    def setUp(self):

        org_1_data = {
            "name": "Prunedge",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status":"ACTIVE"
        }

        org_2_data = {
            "name": "Second Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 5,
            "package": "CORE HR",
            "subdomain": "second.hrms.com",
            "status":"ACTIVE"
        }

        prunedge_org = Organisation.objects.create(**org_1_data)

        org2 = Organisation.objects.create(**org_2_data)

        user_1_data = {
            "organisation": prunedge_org,
            "email": "user1@prunedge.com",
            "password": "passer",
            "verified": True,
        }

        user_2_data = {
            "organisation": org2,
            "email": "user2@anotherorf.com",
            "password": "other_org_pass",
            "verified": True,
        }

        user1 = get_user_model().objects.create_user(**user_1_data)

        user2 = get_user_model().objects.create_user(**user_2_data)

        employee_1_data = {
            "user": user1,
            "organisation": prunedge_org,
            "firstname": "Ray",
            "lastname": "Inc",
            "work_email": "ray@prunedge.com",
            "job_title": "Engineer",
            # "employment_category": "FULL TIME",
            "employment_status": "FULL TIME",
        }

        employee_2_data = {
            "user": user2,
            "organisation": org2,
            "firstname": "Ray",
            "lastname": "Inc",
            "work_email": "ray@prunedge.com",
            "job_title": "Engineer",
            # "employment_category": "FULL TIME",
            "employment_status": "FULL TIME",
        }

        prunedge_employee = Employee.objects.create(**employee_1_data)
        employee2 = Employee.objects.create(**employee_2_data)

        # create Expense claims

        expense_1_data = {
            "employee": prunedge_employee,
            "title": "Expense 1",
            "description": "Desc 1",
            "start_date": "2019-04-30",
            "end_date": "2020-04-30",
            "total_amount": 1000,
        }

        expense_2_data = {
            "employee": employee2,
            "title": "Expense 2",
            "description": "Desc 2",
            "start_date": "2019-04-30",
            "end_date": "2020-04-30",
            "total_amount": 2000,
        }

        expense_3_data = {
            "employee": prunedge_employee,
            "title": "Expense 3",
            "description": "Desc 3",
            "start_date": "2019-04-30",
            "end_date": "2020-04-30",
            "total_amount": 3000,
        }

        expense_4_data = {
            "employee": prunedge_employee,
            "title": "Expense 4",
            "description": "Desc 4",
            "start_date": "2019-04-30",
            "end_date": "2020-04-30",
            "total_amount": 4000,
        }

        models.Expense.objects.create(**expense_1_data)
        models.Expense.objects.create(**expense_2_data)
        models.Expense.objects.create(**expense_3_data)
        models.Expense.objects.create(**expense_4_data)
        self.authenticator()

    def authenticator(self):
        """Authenticate incoming request"""
        url = reverse("user:login")
        data = {
            "email": "user1@prunedge.com",
            "password": "passer",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_can_only_retrieve_by_employee_organisation(self):
        """Retrieve only expenses from this user's organisation"""
        url = reverse("claims:expense-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.json()["total"], 3)
        self.assertEqual(len(response.json()["results"]), 3)
