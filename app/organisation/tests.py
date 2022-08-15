from urllib import response
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from employee.models import Employee
from organisation.models import Organisation, OrganisationNode, Location
from user.tasks import send_new_user_email
from unittest import mock
from user.models import Token, User
from django.conf import settings
from core.utils.reverse_querystring import reverse_querystring


class OrganisationCreateTests(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        prunedge_org_data = {
            "name": "Prunedge",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status":"ACTIVE",
        }

        another_org_data = {
            "name": "First Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 4,
            "package": "CORE HR",
            "subdomain": "another.hrms.com",
            "status":"ACTIVE"
        }

        prunedge_org = Organisation.objects.create(**prunedge_org_data)
        onboarded_org = Organisation.objects.create(**another_org_data)

        super_admin_user_data = {
            "organisation": prunedge_org,
            "email": "superadmin@prunedge.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }

        hr_admin_user_data = {
            "organisation": onboarded_org,
            "email": "hradmin@prunedge.com",
            "password": "hradmin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        employee_user_data = {
            "organisation": onboarded_org,
            "email": "employee@prunedge.com",
            "password": "employee",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }

        hr_admin_without_an_org_data = {
            "email": "null_org_hradmin@hradmin.com",
            "password": "null_org_hradmin",
            "verified": True,
            "roles": ["HR_ADMIN"],
            "firstname":"Admin First",
            "lastname":"Admin Last",
        }

        super_admin = get_user_model().objects.create_user(**super_admin_user_data)
        hr_admin = get_user_model().objects.create_user(**hr_admin_user_data)
        null_org_hr_admin = get_user_model().objects.create_user(
            **hr_admin_without_an_org_data
        )
        employee_user = get_user_model().objects.create_user(**employee_user_data)

    def super_admin_authenticator(self):
        """Authenticate  super admin"""
        url = reverse("user:login")
        data = {
            "email": "superadmin@prunedge.com",
            "password": "super",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def hr_admin_authenticator(self):
        """Authenticate  hr admin"""
        url = reverse("user:login")
        data = {
            "email": "hradmin@prunedge.com",
            "password": "hradmin",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def null_org_hr_admin_authenticator(self):
        """Authenticate an hr admin without an"""
        url = reverse("user:login")
        data = {
            "email": "null_org_hradmin@hradmin.com",
            "password": "null_org_hradmin",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def employee_user_authenticator(self):
        """Authenticate employee admin"""
        url = reverse("user:login")
        data = {
            "email": "employee@prunedge.com",
            "password": "employee",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    @mock.patch("user.tasks.send_new_user_email")
    def test_super_admin_can_create_org(self, mock_send_email):
        self.super_admin_authenticator()
        url = reverse("organization:organisation-list")

        new_org_data = {
            "name": "New Org",
            "sector": "PRIVATE",
            "type": "SINGLE",
            "size": 90,
            "package": "CORE HR",
            "firstname": "First",
            "lastname": "Last",
            "email": "neworg@neworg.com",
            "subdomain": "org_sub_domain",
            "status":"ACTIVE"
        }
        mock_send_email.delay.side_effect = print(
            "Sent to celery task:New User Email!!!"
        )
        response = self.client.post(url, new_org_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], "New Org")
        self.assertEqual(response.json()["subdomain"], "org_sub_domain")

        # Test that mail was sent to the newly created org admin user.
        token = Token.objects.get(user__email="neworg@neworg.com")
        user = User.objects.get(email="neworg@neworg.com")

        user_email_args = {
            "id": user.id,
            "email": "neworg@neworg.com",
            "fullname": "Last First",
            "url": f"https://org_sub_domain.{settings.CLIENT_URL}/user-signup/?token={token.token}"
            # "url": f"{settings.CLIENT_URL}/verify-user/?token={token.token}"
        }

        mock_send_email.delay.assert_called_once()
        mock_send_email.delay.assert_called_with(user_email_args)

        # Test that a root organisation node is created along the created organisation
        org_root_node = OrganisationNode.objects.filter(
            name="New Org", parent__isnull=True
        ).count()
        self.assertEqual(org_root_node, 1)

    def test_hr_admin_cannot_create_org(self):
        """ "Test that HR admin and Other Employee cannot create org"""
        self.hr_admin_authenticator()
        url = reverse("organization:organisation-list")

        new_org_data = {
            "name": "New Org",
            "sector": "PRIVATE",
            "type": "SINGLE",
            "size": 90,
            "package": "CORE HR",
            "firstname": "First",
            "lastname": "Last",
            "email": "neworg@neworg.com",
            "subdomain": "new_org",
            "status":"ACTIVE",
        }

        response = self.client.post(url, new_org_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.employee_user_authenticator()
        response = self.client.post(url, new_org_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hr_admin_with_a_setup_org_cannot_self_onboard(self):
        self.hr_admin_authenticator()
        url = reverse("organization:organisation-self-onboard")
        data = {
            "name": "Self Onboarded Org",
            "sector": "PRIVATE",
            "type": "SINGLE",
            "size": 90,
            "package": "CORE HR",
            "firstname": "Self",
            "lastname": "Onboarded",
            "email": "selfonboard@neworg.com",
            "subdomain": "self-onboard",
            "status":"ACTIVE"
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hr_admin_without_a_setup_org_can_self_onboard(self):
        self.null_org_hr_admin_authenticator()
        url = reverse("organization:organisation-self-onboard")
        data = {
            "name": "Null Org HR Admin Org",
            "sector": "PRIVATE",
            "type": "SINGLE",
            "size": 90,
            "package": "CORE HR",
            "firstname": "Self",
            "lastname": "Onboarded",
            "email": "selfonboard@neworg.com",
            "subdomain": "self-onboard",
            "status":"ACTIVE"
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test that a root organisation node is created along the created organisation
        org_root_node = OrganisationNode.objects.filter(
            name="Null Org HR Admin Org", parent__isnull=True
        ).count()
        self.assertEqual(org_root_node, 1)

    def test_super_admin_cannot_self_onboard(self):
        self.super_admin_authenticator()
        url = reverse("organization:organisation-self-onboard")
        data = {
            "name": "Super Self Onboard Org",
            "sector": "PRIVATE",
            "type": "SINGLE",
            "size": 90,
            "package": "CORE HR",
            "firstname": "Self",
            "lastname": "Onboarded",
            "email": "superselfonboard@neworg.com",
            "subdomain": "superself-onboard",
            "status":"ACTIVE"
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_user_cannot_self_onboard(self):
        self.employee_user_authenticator()
        url = reverse("organization:organisation-self-onboard")
        data = {
            "name": "Employee Self Onboard Org",
            "sector": "PRIVATE",
            "type": "SINGLE",
            "size": 90,
            "package": "CORE HR",
            "firstname": "Self",
            "lastname": "Onboarded",
            "email": "superselfonboard@neworg.com",
            "subdomain": "superself-onboard",
            "status":"ACTIVE"
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OrganisationUpdateTests(APITestCase):
    settings.USE_TZ = False

    def setUp(self):

        prunedge_org_data = {
            "name": "Prunedge",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status":"ACTIVE",
        }

        another_org_data = {
            "name": "First Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 4,
            "package": "CORE HR",
            "subdomain": "another.hrms.com",
            "status":"ACTIVE",
        }

        another_org_data2 = {
            "name": "First",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 4,
            "package": "CORE HR",
            "subdomain": "another1.hrms.com",
            "status":"ACTIVE",
        }

        prunedge_org = Organisation.objects.create(**prunedge_org_data)
        onboarded_org = Organisation.objects.create(**another_org_data)
        # onboarded_org2 = Organisation.objects.create(**another_org_data2)

        self.super_admin_org_id = prunedge_org.id
        self.hr_admin_org_id = onboarded_org.id
        # self.hr2_admin_org_id = onboarded_org2.id

        super_admin_user_data = {
            "organisation": prunedge_org,
            "email": "superadmin@prunedge.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }

        hr_admin_user_data = {
            "organisation": onboarded_org,
            "email": "hradmin@prunedge.com",
            "password": "hradmin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        super_admin = get_user_model().objects.create_user(**super_admin_user_data)
        hr_admin = get_user_model().objects.create_user(**hr_admin_user_data)

    def super_admin_authenticator(self):
        """Authenticate a super admin"""
        url = reverse("user:login")
        data = {
            "email": "superadmin@prunedge.com",
            "password": "super",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def hr_admin_authenticator(self):
        """Authenticate hr admin"""
        url = reverse("user:login")
        data = {
            "email": "hradmin@prunedge.com",
            "password": "hradmin",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_superadmin_can_update_any_org_data(self):
        self.super_admin_authenticator()
        super_admin_org_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.super_admin_org_id}
        )

        data = {
            "name": "Prunedge Update Name",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 5000,
            "package": "CORE HR",
            "subdomain": "edgeupdated.hrms.com",
            "firstname": "Prun",
            "lastname": "Prun",
            "location": "World",
            "email": "ceo@prunedge.com",
            "status":"ACTIVE",
        }
        response = self.client.put(super_admin_org_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Prunedge Update Name")
        self.assertEqual(response.json()["subdomain"], "edge.hrms.com")
        self.assertEqual(response.json()["size"], str(5000))

        different_org_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.hr_admin_org_id}
        )
        data = {
            "name": "Updated First Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 50,
            "package": "CORE HR",
            "subdomain": "different.hrms.com",
            "firstname": "updated First",
            "lastname": "updated Last",
            "location": "Lagos",
            "email": "updatedorg@prunedge.com",
            "status":"ACTIVE",
        }

        response = self.client.put(different_org_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Updated First Org")
        #Test that subdomain is not replaceable
        self.assertEqual(response.json()["subdomain"], "another.hrms.com")
        self.assertEqual(response.json()["size"], str(50))
        self.assertEqual(response.json()["location"], "Lagos")

    def test_hr_admin_can_update_own_org_data(self):
        self.hr_admin_authenticator()
        hr_admin_org_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.hr_admin_org_id}
        )

        data = {
            "name": "Updated by HR Admin",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 999,
            "package": "CORE HR",
            "subdomain": "byhradmin.hrms.com",
            "firstname": "updated First",
            "lastname": "updated Last",
            "location": "Lagos",
            "email": "byhradminorg@prunedge.com",
            "status":"ACTIVE",
        }

        response = self.client.put(hr_admin_org_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Updated by HR Admin")
        #subdomain cannot  be updated
        self.assertEqual(response.json()["subdomain"], "another.hrms.com")
        self.assertEqual(response.json()["size"], str(999))

    def test_hr_admin_cannot_update_another_org_data(self):
        self.hr_admin_authenticator()
        different_admin_org_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.super_admin_org_id}
        )
        data = {
            "name": "Forbidden Hr Admin",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 999,
            "package": "CORE HR",
            "subdomain": "forbidden.hrms.com",
            "firstname": "updated First",
            "lastname": "updated Last",
            "location": "Lagos",
            "email": "forbidden@prunedge.com",
            "status":"ACTIVE"
        }

        response = self.client.put(different_admin_org_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OrganisationRetrieveTestCases(APITestCase):
    settings.USE_TZ = False

    def setUp(self):

        prunedge_org_data = {
            "name": "Prunedge",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "prunedge.hrms.com",
            "status":"ACTIVE"
        }

        org_1_data = {
            "name": "1st Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org1.hrms.com",
            "status":"ACTIVE"
        }

        org_2_data = {
            "name": "2nd Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 4,
            "package": "CORE HR",
            "subdomain": "org2.hrms.com",
            "status":"ACTIVE"
        }

        org_3_data = {
            "name": "3rd Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 4,
            "package": "CORE HR",
            "subdomain": "org3.hrms.com",
            "status":"ACTIVE"
        }

        org_4_data = {
            "name": "4th Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 5,
            "package": "CORE HR",
            "subdomain": "org4.hrms.com",
            "status":"ACTIVE"
        }

        prunedge_org = Organisation.objects.create(**prunedge_org_data)
        org1 = Organisation.objects.create(**org_1_data)
        org2 = Organisation.objects.create(**org_2_data)
        org3 = Organisation.objects.create(**org_3_data)
        org4 = Organisation.objects.create(**org_4_data)

        self.prunedge_org_id = prunedge_org.id
        self.org1_id = org1.id
        self.org2_id = org2.id
        self.org3_id = org3.id

        super_admin_user_data = {
            "organisation": prunedge_org,
            "email": "superadmin@prunedge.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }

        org2_hr_admin_user_data = {
            "organisation": org2,
            "email": "org2@org2.com",
            "password": "org2admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        employee_user_data = {
            "organisation": prunedge_org,
            "email": "employee@prunedge.com",
            "password": "prunemployee",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }

        user_without_org = {
            "email": "nullorg@org.com",
            "password": "nullorg",
            "verified": True,
            "roles": ["EMPLOYEE", "HR_ADMIN"],
        }

        get_user_model().objects.create_user(**super_admin_user_data)
        get_user_model().objects.create_user(**org2_hr_admin_user_data)
        get_user_model().objects.create_user(**employee_user_data)
        get_user_model().objects.create_user(**user_without_org)

    def super_admin_authenticator(self):
        """Authenticate  super admin"""
        url = reverse("user:login")
        data = {
            "email": "superadmin@prunedge.com",
            "password": "super",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def hr_admin_authenticator(self):
        """Authenticate  hr admin"""
        url = reverse("user:login")
        data = {
            "email": "org2@org2.com",
            "password": "org2admin",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def employee_user_authenticator(self):
        """Authenticate employee admin"""
        url = reverse("user:login")
        data = {
            "email": "employee@prunedge.com",
            "password": "prunemployee",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def user_without_assigned_org_authenticator(self):
        """null organisation user"""
        url = reverse("user:login")
        data = {
            "email": "nullorg@org.com",
            "password": "nullorg",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_retrieve_all_org_by_superadmin(self):
        """Retrieves all organisation to a super admin"""
        self.super_admin_authenticator()
        url = reverse("organization:organisation-list")
        response = self.client.get(url, format="json")
        # check all orgs are returned
        self.assertEqual(response.json()["total"], 5)
        self.assertEqual(len(response.json()["results"]), 5)

    def test_retrieve_a_valid_organisation(self):
        """Retrieve specific org details using id"""
        self.super_admin_authenticator()
        valid_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.prunedge_org_id}
        )
        response = self.client.get(valid_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Prunedge")

        org3_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.org3_id}
        )
        response = self.client.get(org3_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "3rd Org")

    def test_delete_organisation_by_superadmin(self):
        """Delete specific org details using id"""
        self.super_admin_authenticator()
        valid_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.prunedge_org_id}
        )
        response = self.client.delete(valid_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            Organisation.objects.filter(id=str(self.prunedge_org_id)).count(), 0
        )

    def test_delete_organisation_by_hradmin(self):
        """Delete specific org details using id"""
        self.hr_admin_authenticator()
        valid_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.org2_id}
        )
        response = self.client.delete(valid_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Organisation.objects.filter(id=str(self.org2_id)).count(), 0)

    def test_cannot_retrieve_an_invalid_organisation(self):
        self.super_admin_authenticator()
        invalid_url = reverse(
            "organization:organisation-detail",
            kwargs={"pk": "invalidf2-6220-4c41-a5bf-38c6c298d25d"},
        )
        response = self.client.get(invalid_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_not_permitted_organisation(self):
        """An HR admin trying to retrieve another org details"""
        # note:hr_admin_authenticator() is associated with org2
        self.hr_admin_authenticator()
        org3_url = reverse(
            "organization:organisation-detail", kwargs={"pk": self.org3_id}
        )
        response = self.client.get(org3_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_org_by_hr_admin(self):
        """Retrieves only organisation of an hr admin"""
        self.hr_admin_authenticator()
        url = reverse("organization:organisation-list")
        response = self.client.get(url, format="json")
        # check only one org is returned; confirm it's content also.
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(len(response.json()["results"]), 1)
        # check returned content tallies
        self.assertEqual(response.json()["results"][0]["name"], "2nd Org")
        self.assertEqual(response.json()["results"][0]["size"], str(4))
        self.assertEqual(response.json()["results"][0]["subdomain"], "org2.hrms.com")

    def test_employee_cannot_retrieve_org_data(self):
        self.employee_user_authenticator()
        url = reverse("organization:organisation-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unassigned_user_cannot_retrieve_org_data(self):
        """Test that a user without an organisation retrieves nothing"""
        self.user_without_assigned_org_authenticator()
        url = reverse("organization:organisation-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total"], 0)
        self.assertEqual(len(response.json()["results"]), 0)


class OrganisationLevelTests(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        prunedge_org_data = {
            "name": "PrunedgeOrg",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 8900,
            "package": "CORE HR",
            "subdomain": "prunedgeorg.hrms.com",
            "status":"ACTIVE"
        }

        org_1_data = {
            "name": "1st Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org1domain.hrms.com",
            "status":"ACTIVE"
        }

        prunedge_org = Organisation.objects.create(**prunedge_org_data)
        org1 = Organisation.objects.create(**org_1_data)

        super_admin_user_data = {
            "organisation": prunedge_org,
            "email": "superadmin@prunedge.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }

        org1_hr_admin_user_data = {
            "organisation": org1,
            "email": "org1@org1.com",
            "password": "org1admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        get_user_model().objects.create_user(**super_admin_user_data)
        get_user_model().objects.create_user(**org1_hr_admin_user_data)

    def super_admin_authenticator(self):
        """Authenticate  super admin"""
        url = reverse("user:login")
        data = {
            "email": "superadmin@prunedge.com",
            "password": "super",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def hr_admin_authenticator(self):
        """Authenticate  hr admin"""
        url = reverse("user:login")
        data = {
            "email": "org1@org1.com",
            "password": "org1admin",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_can_create_org_level(self):
        """Each Org level is created one at a time"""
        self.super_admin_authenticator()
        url = reverse("organization:OrganisationLevel-list")

        org_level1 = {"name": "Department"}

        org_level2 = {"name": "Unit"}

        response1 = self.client.post(url, org_level1, format="json")
        response2 = self.client.post(url, org_level2, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        returned_levels = response2.json()["levels"]
        # check numbers of levels returned
        self.assertEqual(len(returned_levels), 2)
        self.assertEqual(returned_levels["1"], "Department")
        self.assertEqual(returned_levels["2"], "Unit")

    def test_can_create_org_level_by_hradmin(self):
        self.hr_admin_authenticator()
        url = reverse("organization:OrganisationLevel-list")
        org_level = {"name": "Division"}
        response = self.client.post(url, org_level, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_levels = response.json()["levels"]
        # check numbers of levels returned
        self.assertEqual(len(returned_levels), 1)
        self.assertEqual(returned_levels["1"], "Division")


class OrgLevelRetrieveUpdateTests(APITestCase):
    # """Test Suite for Listing and Updating Org. Levels For
    # the authenticated Admin(Super/HR) user
    # """
    settings.USE_TZ = False

    def setUp(self):
        org1_data = {
            "levels": {"1": "Org1Department", "2": "Org1Unit"},
            "name": "1st Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org1domain.hrms.com",
            "status":"ACTIVE"
        }

        org2_data = {
            "levels": {"1": "Org2Department", "2": "Org2Unit"},
            "name": "2nd Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org2domain.hrms.com",
            "status":"ACTIVE"
        }

        prunedge_data = {
            "levels": {},
            "name": "Prunedge",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "superdomain.hrms.com",
            "status":"ACTIVE"
        }

        super_org = Organisation.objects.create(**prunedge_data)
        org1 = Organisation.objects.create(**org1_data)
        org2 = Organisation.objects.create(**org2_data)

        org1_hr_admin_data = {
            "organisation": org1,
            "email": "org1@org1.com",
            "password": "org1admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        org2_hr_admin_data = {
            "organisation": org2,
            "email": "org2@org2.com",
            "password": "org2admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        super_user_data = {
            "organisation": super_org,
            "email": "super@prun.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }

        ordinary_employee_user_data = {
            "organisation": org1,
            "email": "employee@org1.com",
            "password": "employee",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }

        get_user_model().objects.create_user(**ordinary_employee_user_data)
        get_user_model().objects.create_user(**super_user_data)
        get_user_model().objects.create_user(**org1_hr_admin_data)
        get_user_model().objects.create_user(**org2_hr_admin_data)

    def org1_hr_admin_authenticator(self):
        """Authenticate as Hr Admin from Org1"""
        url = reverse("user:login")
        data = {
            "email": "org1@org1.com",
            "password": "org1admin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def org2_hr_admin_authenticator(self):
        """Authenticate as Hr Admin from Org2"""
        url = reverse("user:login")
        data = {
            "email": "org2@org2.com",
            "password": "org2admin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def super_authenticator(self):
        """Authenticate as Super Admin on the system"""
        url = reverse("user:login")
        data = {
            "email": "super@prun.com",
            "password": "super",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def employee_user_authenticator(self):
        """Authenticate as employee"""
        url = reverse("user:login")
        data = {
            "email": "employee@org1.com",
            "password": "employee",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_super_admin_retrieves_org_levels(self):
        """Only Org. levels of the super admin is returned to super admin"""
        self.super_authenticator()
        url = reverse("organization:OrganisationLevel-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_levels = response.json()["data"]
        # check the content,i.e empty dict as created.
        self.assertEqual(len(returned_levels), 0)

    def test_hr_admin_retrieves_org_levels(self):
        """Only Org. levels of the hr admin is returned to hr admin"""
        self.org1_hr_admin_authenticator()
        url = reverse("organization:OrganisationLevel-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_levels = response.json()["data"]
        # check the content,i.e empty dict as created.
        self.assertEqual(len(returned_levels), 2)
        self.assertEqual(returned_levels["1"], "Org1Department")
        self.assertEqual(returned_levels["2"], "Org1Unit")

    def test_emloyee_user_cannot_retrieve_org_levels(self):
        self.employee_user_authenticator()
        url = reverse("organization:OrganisationLevel-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_update_organisation_level(self):
        """The level (i.e. 1,2,3,etc.) to update is passed as pk"""
        self.org2_hr_admin_authenticator()
        url = reverse("organization:OrganisationLevel-detail", kwargs={"pk": 1})
        data = {"name": "Updated Org2Department"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_levels = response.json()
        self.assertEqual(len(returned_levels), 2)
        # check if properly updated
        self.assertEqual(returned_levels["1"], "Updated Org2Department")
        self.assertEqual(returned_levels["2"], "Org2Unit")

    def test_cannot_update_invalid_org_level(self):
        self.org2_hr_admin_authenticator()
        url = reverse("organization:OrganisationLevel-detail", kwargs={"pk": 30})
        data = {"name": "Updatedly Org2Department"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OrgNodeTests(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        org1_data = {
            "levels": {"1": "Department"},
            "name": "1st Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org1domain.hrms.com",
            "status":"ACTIVE"
        }

        org2_data = {
            "levels": {"1": "Department", "2": "Teams"},
            "name": "2nd Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org2domain.hrms.com",
            "status":"ACTIVE"
        }

        super_org_data = {
            "levels": {},
            "name": "Prunedge Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "prun.hrms.com",
            "status":"ACTIVE"
        }

        # create organisations and respective root org node
        org1 = Organisation.objects.create(**org1_data)
        org1_root_node = OrganisationNode.objects.create(
            organisation=org1, name=org1.name, parent=None
        )

        self.org1_root_node_id = org1_root_node.id

        org2 = Organisation.objects.create(**org2_data)
        org2_root_node = OrganisationNode.objects.create(
            organisation=org2, name=org2.name, parent=None
        )

        self.org2_root_node_id = org2_root_node.id

        super_org = Organisation.objects.create(**super_org_data)
        OrganisationNode.objects.create(
            organisation=super_org, name=super_org.name, parent=None
        )

        org1_hr_admin_data = {
            "organisation": org1,
            "email": "org1@org1.com",
            "password": "org1admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        org2_hr_admin_data = {
            "organisation": org2,
            "email": "org2@org2.com",
            "password": "org2admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        super_user_data = {
            "organisation": super_org,
            "email": "super@super.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }

        get_user_model().objects.create_user(**org1_hr_admin_data)
        get_user_model().objects.create_user(**org2_hr_admin_data)
        get_user_model().objects.create_user(**super_user_data)

    def org1_hr_admin_authenticator(self):
        """Authenticate as Hr Admin from Org1"""
        url = reverse("user:login")
        data = {
            "email": "org1@org1.com",
            "password": "org1admin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def org2_hr_admin_authenticator(self):
        """Authenticate as Hr Admin from Org2"""
        url = reverse("user:login")
        data = {
            "email": "org2@org2.com",
            "password": "org2admin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def super_admin_authenticator(self):
        """Authenticate a Super Admin"""
        url = reverse("user:login")
        data = {
            "email": "super@super.com",
            "password": "super",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_cannot_create_org_node_with_empty_org_level(self):
        """Test that organisation with empty Org levels Cannot create Node
        The super admin org. created in setUp has empty dict.
        """
        self.super_admin_authenticator()
        url = reverse("organization:organisationnode-list")
        data = {
            "name": "Org Node 1",
            "level": "1",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_create_org_node(self):
        self.org2_hr_admin_authenticator()
        url = reverse("organization:organisationnode-list")

        data = {"name": "Org Node 1"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # test that the first newly created org node has its parent as root_org_node and
        # that its level is 1
        returned_data = response.json()
        self.assertEqual(returned_data["parent"], str(self.org2_root_node_id))
        self.assertEqual(returned_data["level"], 1)

        # create second node i.e. level 2
        data2 = {"parent": returned_data["id"], "name": "Org Node 2"}
        response2 = self.client.post(url, data2, format="json")
        returned_data2 = response2.json()
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        # Test the level created is 2
        self.assertEqual(returned_data2["level"], 2)

        # # Test cannot create node beyond Org levels
        data3 = {"parent": returned_data2["id"], "name": "Org Node 3"}

        response3 = self.client.post(url, data3, format="json")
        returned_data3 = response3.json()
        self.assertEqual(response3.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_org_node_beyond_org_level(self):
        # Org1 Only has one level created.i.e. {"1": "Department"}
        self.org1_hr_admin_authenticator()
        url = reverse("organization:organisationnode-list")
        data = {"name": "Teams"}
        response = self.client.post(url, data, format="json")
        returned_data = response.json()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(returned_data["level"], 1)

        data = {"parent": f"{returned_data['id']}", "name": "Team2"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_update_org_root_node(self):
        self.org1_hr_admin_authenticator()
        url = reverse(
            "organization:organisationnode-detail",
            kwargs={"pk": self.org1_root_node_id},
        )

        data = {
            "name": "Updated Name Here",
        }

        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_org_node(self):
        self.org1_hr_admin_authenticator()
        url = reverse(
            "organization:organisationnode-detail",
            kwargs={"pk": self.org1_root_node_id},
        )
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_hr_admin_cannot_act_on_another_organisation_org_node(self):
        """Simulating Org2 Hr Admin trying to act on Org1 data"""
        self.org2_hr_admin_authenticator()
        url = reverse(
            "organization:organisationnode-detail",
            kwargs={"pk": self.org1_root_node_id},
        )
        delete_response = self.client.delete(url, format="json")
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)

        data = {"name": "Denied Update"}

        update_response = self.client.put(url, data, format="json")
        self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_org_nodes(self):
        # Retrieves Org Nodes belonging to the organisation of the authenticated admin
        self.org1_hr_admin_authenticator()
        url = reverse("organization:organisationnode-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class RetrieveOrgNodeRootAndLeafTests(APITestCase):
    """
                        Sample tree structure for test
    0                             Organisation
    1            Software              Sales                      Talent
    2     FrontEnd      BackEnd      Online   Physical     T. Training   T. Acquisition
    3    React  Vue   Python  DotNet                       Paid   Free
    """

    settings.USE_TZ = False

    def setUp(self):

        org1_data = {
            "name": "1st Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org1domain.hrms.com",
            "status":"ACTIVE"
        }
        org1 = Organisation.objects.create(**org1_data)

        user_data = {
            "organisation": org1,
            "email": "org@org.com",
            "password": "super",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }
        get_user_model().objects.create_user(**user_data)
        # Create root node
        org1_root_node = OrganisationNode.objects.create(
            organisation=org1, name=org1.name, parent=None
        )

        self.created_root_node_id = org1_root_node.id
        # Create parent nodes. Software Talent Sales
        parentnode1_data = {
            "parent": org1_root_node,
            "name": "Software",
            "level": 1,
            "organisation": org1,
        }

        parentnode1 = OrganisationNode.objects.create(**parentnode1_data)

        parentnode2_data = {
            "parent": org1_root_node,
            "name": "Talent",
            "level": 1,
            "organisation": org1,
        }

        parentnode2 = OrganisationNode.objects.create(**parentnode2_data)

        parentnode3_data = {
            "parent": org1_root_node,
            "name": "Sales",
            "level": 1,
            "organisation": org1,
        }

        parentnode3 = OrganisationNode.objects.create(**parentnode3_data)

        # Create child nodes..(Frontend, Backend) (Training, Acquisition) (Online,Physical)
        first_childnode_p1data = {
            "parent": parentnode1,
            "name": "FRONT END",
            "level": 2,
            "organisation": org1,
        }

        first_childnode_p1 = OrganisationNode.objects.create(**first_childnode_p1data)

        second_childnode_p1data = {
            "parent": parentnode1,
            "name": "BACK END",
            "level": 2,
            "organisation": org1,
        }

        second_childnode_p1 = OrganisationNode.objects.create(**second_childnode_p1data)

        first_childnode_p2data = {
            "parent": parentnode2,
            "name": "Talent Training",
            "level": 2,
            "organisation": org1,
        }

        first_childnode_p2 = OrganisationNode.objects.create(**first_childnode_p2data)

        second_childnode_p2data = {
            "parent": parentnode2,
            "name": "Talent Acquisition",
            "level": 2,
            "organisation": org1,
        }

        second_childnode_p2 = OrganisationNode.objects.create(**second_childnode_p2data)

        first_childnode_p3data = {
            "parent": parentnode3,
            "name": "Sales Physical",
            "level": 2,
            "organisation": org1,
        }

        first_childnode_p3 = OrganisationNode.objects.create(**first_childnode_p3data)

        second_childnode_p3data = {
            "parent": parentnode2,
            "name": "Sales Online",
            "level": 2,
            "organisation": org1,
        }

        second_childnode_p3 = OrganisationNode.objects.create(**second_childnode_p3data)

        # Creat leaf nodes for the first parenti.e Software
        parent1_first_leaf_node = {
            "parent": first_childnode_p1,
            "name": "React",
            "level": 3,
            "organisation": org1,
        }

        OrganisationNode.objects.create(**parent1_first_leaf_node)

        parent1_second_leaf_node = {
            "parent": first_childnode_p1,
            "name": "Vue",
            "level": 3,
            "organisation": org1,
        }
        OrganisationNode.objects.create(**parent1_second_leaf_node)

        parent1_3rd_leaf_node = {
            "parent": second_childnode_p1,
            "name": "Python",
            "level": 3,
            "organisation": org1,
        }

        OrganisationNode.objects.create(**parent1_3rd_leaf_node)
        parent1_4th_leaf_node = {
            "parent": second_childnode_p1,
            "name": "DotNet",
            "level": 3,
            "organisation": org1,
        }
        OrganisationNode.objects.create(**parent1_4th_leaf_node)

        # # Create leaf nodes for the third parent i.e. Talent

        parent3_first_leaf_node_data = {
            "parent": first_childnode_p2,
            "name": "Paid",
            "level": 3,
            "organisation": org1,
        }
        OrganisationNode.objects.create(**parent3_first_leaf_node_data)

        parent3_second_leaf_node_data = {
            "parent": first_childnode_p2,
            "name": "Free",
            "level": 3,
            "organisation": org1,
        }

        OrganisationNode.objects.create(**parent3_second_leaf_node_data)

    def authenticator(self):
        """Authenticate as Hr Admin from Org1"""
        url = reverse("user:login")
        data = {
            "email": "org@org.com",
            "password": "super",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_can_retrieve_root_node(self):
        self.authenticator()
        url = reverse("organization:organisationnode-root")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(self.created_root_node_id))

    def test_can_retrieve_leaf_nodes(self):
        # React Vue   Python DotNet  Online Physical   Paid Free   T.Acquisition
        self.authenticator()
        url = reverse("organization:organisationnode-leaf")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check the number of leaf nodes returned and contents
        self.assertEqual(response.json()["total"], 9)
        self.assertEqual(len(response.json()["results"]), 9)

        returned_leafs = [leaf["name"] for leaf in response.json()["results"]]
        expected_leaf_nodes = [
            "React",
            "Vue",
            "Python",
            "DotNet",
            "Sales Online",
            "Sales Physical",
            "Paid",
            "Free",
            "Talent Acquisition",
        ]
        # check if returned_leafs contain all expected lead nodes

        result = all(elem in returned_leafs for elem in expected_leaf_nodes)
        self.assertEqual(result, True)


class RetrievePackageStatsTests(APITestCase):
    def setUp(self):
        org1_data = {
            "name": "Super Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "PAYROLL",
            "subdomain": "org1.hrms.com",
            "status":"ACTIVE"
        }
        org2_data = {
            "name": "Org 2",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "PAYROLL",
            "subdomain": "org2.hrms.com",
            "status":"ACTIVE"
        }
        org3_data = {
            "name": "Org 3",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org3.hrms.com",
            "status":"ACTIVE"
        }
        org4_data = {
            "name": "Org 4",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "CORE HR",
            "subdomain": "org4.hrms.com",
            "status":"ACTIVE"
        }
        org5_data = {
            "name": "Org 5",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "HR & PAYROLL",
            "subdomain": "org5.hrms.com",
            "status":"ACTIVE"
        }

        super_org = Organisation.objects.create(**org1_data)
        Organisation.objects.create(**org2_data)
        Organisation.objects.create(**org3_data)
        Organisation.objects.create(**org4_data)
        Organisation.objects.create(**org5_data)

        super_user_data = {
            "organisation": super_org,
            "email": "super@org.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }
        get_user_model().objects.create_user(**super_user_data)

    def authenticator(self):
        url = reverse("user:login")
        data = {
            "email": "super@org.com",
            "password": "super",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_retrieve_package_stats(self):
        self.authenticator()
        url = reverse("organization:organisation-package-stat")
        response = self.client.get(url, format="json")
        package_stats = response.json()["package_stat"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(package_stats["core_package"], 2)
        self.assertEqual(package_stats["hr_package"], 2)
        self.assertEqual(package_stats["core_and_hr_package"], 1)


class TenantValidationTests(APITestCase):
    """Test validity/existence of a tenant using subdomain"""

    def setUp(self):
        org = {
            "name": "Valid Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "PAYROLL",
            "subdomain": "valid.hrms.com",
            "status":"ACTIVE"
        }
        Organisation.objects.create(**org)

    def test_verify_valid_tenant(self):
        url = reverse_querystring(
            "organization:organisation-check-tenant",
            query_kwargs={"subdomain": "valid.hrms.com"},
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["exist"], True)

    def test_verify_invalid_tenant(self):
        url = reverse_querystring(
            "organization:organisation-check-tenant",
            query_kwargs={"subdomain": "unknowndomain.hrms.com"},
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["exist"], False)


class CreateOrganisationLocationTestCases(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        org_data = {
            "name": "Org Name",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "PAYROLL",
            "subdomain": "orgname.hrms.com",
            "status":"ACTIVE"
        }
        org = Organisation.objects.create(**org_data)
        hradmin_user_data = {
            "organisation": org,
            "email": "hradmin@org.com",
            "password": "admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }
        get_user_model().objects.create_user(**hradmin_user_data)

        employee_user_data = {
            "organisation": org,
            "email": "employee@org.com",
            "password": "employee",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }
        get_user_model().objects.create_user(**employee_user_data)

    def employee_authenticator(self):
        """Login as an employee of the Org."""
        url = reverse("user:login")
        data = {
            "email": "employee@org.com",
            "password": "employee",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def hr_admin_authenticator(self):
        """Login as an hr admin of the Org."""
        url = reverse("user:login")
        data = {
            "email": "hradmin@org.com",
            "password": "admin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_hr_can_create_org_location(self):
        self.hr_admin_authenticator()
        url = reverse("organization:location-list")
        data = {
            "branch": "Mainland",
            "street": "Main Street",
            "city": "Ikeja",
            "state": "Lagos",
            "country": "NG",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        returned_data = response.json()
        # Test returned data content
        self.assertEqual(returned_data["branch"], "Mainland")
        self.assertEqual(returned_data["street"], "Main Street")
        self.assertEqual(returned_data["city"], "Ikeja")

    def test_employeeuser_cannot_create_org_location(self):
        self.employee_authenticator()
        url = reverse("organization:location-list")
        data = {
            "branch": "Mainland",
            "street": "Main Street",
            "city": "Ikeja",
            "state": "Lagos",
            "country": "NG",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OrganisationLocationRetrieveTestCases(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        org_data = {
            "name": "Org Name",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 3,
            "package": "PAYROLL",
            "subdomain": "orgname.hrms.com",
            "status":"ACTIVE"
        }
        org = Organisation.objects.create(**org_data)

        org_location_data = {
            "organisation": org,
            "branch": "Mainland",
            "street": "Main Street",
            "city": "Ikeja",
            "state": "Lagos",
            "country": "NG",
            "branch_code": "A90",
        }

        org_loccation = Location.objects.create(**org_location_data)

        self.org_location_id = org_loccation.id

        hradmin_user_data = {
            "organisation": org,
            "email": "hradmin@org.com",
            "password": "admin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }
        get_user_model().objects.create_user(**hradmin_user_data)

    def hr_admin_authenticator(self):
        """Login as an hr admin of the Org."""
        url = reverse("user:login")
        data = {
            "email": "hradmin@org.com",
            "password": "admin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_can_retrieve_org_location(self):
        self.hr_admin_authenticator()
        url = reverse(
            "organization:location-detail", kwargs={"pk": self.org_location_id}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["branch"], "Mainland")
        self.assertEqual(response.json()["street"], "Main Street")
        self.assertEqual(response.json()["country"], "NG")
        self.assertEqual(response.json()["branch_code"], "A90")

    def test_can_delete_org_location(self):
        self.hr_admin_authenticator()
        url = reverse(
            "organization:location-detail", kwargs={"pk": self.org_location_id}
        )
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # confirm location not exists after deleted
        self.assertEqual(
            Location.objects.filter(id=f"{self.org_location_id}").count(), 0
        )

    def test_can_update_org_location(self):
        self.hr_admin_authenticator()
        url = reverse(
            "organization:location-detail", kwargs={"pk": self.org_location_id}
        )
        data = {
            "branch": "Updated Branch",
            "street": "Updated Street",
            "branch_code": "Updated Code",
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["branch"], "Updated Branch")
        self.assertEqual(response.json()["street"], "Updated Street")
        self.assertEqual(response.json()["branch_code"], "Updated Code")
        self.assertEqual(response.json()["country"], "NG")