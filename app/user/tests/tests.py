from unittest import mock
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from employee.models import Employee
from organisation.models import Organisation
from user.models import User, Token
from django.conf import settings



class AuthenticationTests(APITestCase):
    def setUp(self):
        active_org_data = {
            "name": "Active Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status": "ACTIVE"
        }

        active_org = Organisation.objects.create(**active_org_data)

        active_org_user_data = {
            "organisation": active_org,
            "email": "active_user@prunedge.com",
            "password": "passer",
            "verified": True,
        }

        get_user_model().objects.create_user(**active_org_user_data)

        inactive_org_data = {
            "name": "Inactive Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "inactive.hrms.com",
            "status": "INACTIVE"
        }

        inactive_org = Organisation.objects.create(**inactive_org_data)
        inactive_org_user_data = {
            "organisation": inactive_org,
            "email": "inactive_user@prunedge.com",
            "password": "passer",
            "verified": True,
        }
        get_user_model().objects.create_user(**inactive_org_user_data)

    def test_active_user_login(self):
        """Authenticate a user from Active Org"""
        settings.USE_TZ=False
        url = reverse("user:login")
        data = {
            "email": "active_user@prunedge.com",
            "password": "passer",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_user_login(self):
        """Deny login to user from Inactive Org"""
        url = reverse("user:login")
        data = {
            "email": "inactive_user@prunedge.com",
            "password": "passer",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class UserTests(APITestCase):
    def setUp(self):
        org1_data = {
            "name": "First Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status": "ACTIVE"
        }
        org1 = Organisation.objects.create(**org1_data)

        user1_data = {
            "organisation": org1,
            "email": "org1user1@prunedge.com",
            "password": "passer",
            "verified": True,
            "firstname": "First"
        }

        user1 = get_user_model().objects.create_user(**user1_data)
        self.org1_user1_id = user1.id

        user2_data = {
            "organisation": org1,
            "email": "org1user2@prunedge.com",
            "password": "passer",
            "verified": True,
        }
        user2 = get_user_model().objects.create_user(**user2_data)
        self.org1_user2_id = user2.id

        user3_data = {
            "organisation": org1,
            "email": "org1user3@prunedge.com",
            "password": "passer",
            "verified": True,
        }

        get_user_model().objects.create_user(**user3_data)

        # Create another org info

        another_org_data = {
            "name": "Another Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "anotherorg.hrms.com",
            "status": "ACTIVE"
        }
        another_org = Organisation.objects.create(**another_org_data)

        another_org_user_data = {
            "organisation": another_org,
            "email": "org2user1@another.com",
            "password": "passer",
            "verified": True,
        }

        org2_user1 = get_user_model().objects.create_user(**another_org_user_data)
        self.org2_user1_id = org2_user1.id

    def org1_user_authenticator(self):
        """Authenticate Org1 User"""
        url = reverse("user:login")
        data = {
            "email": "org1user1@prunedge.com",
            "password": "passer",
        }
        settings.USE_TZ=False
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        
    def org2_user_authenticator(self):
        """Authenticate Org2 User"""
        url = reverse("user:login")
        data = {
            "email": "org2user1@another.com",
            "password": "passer",
        }
        
        settings.USE_TZ=False
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_user_retrieves_org_users(self):
        self.org1_user_authenticator()
        url = reverse("user:user-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check no. of returned users
        self.assertEqual(response.json()['total'], 3)
        self.assertEqual(len(response.json()['results']), 3)

    def test_user_retrieves_org_users_(self):
        # authenticate as user from the 2nd org
        self.org2_user_authenticator()
        url = reverse("user:user-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check no. of returned users
        self.assertEqual(response.json()['total'], 1)
        self.assertEqual(len(response.json()['results']), 1)

    def test_retrieve_user_own_details(self):
        # User retriving his own details
        self.org1_user_authenticator()
        # user1 retrieving details of user 2 Note:Same Org
        url = reverse("user:user-detail", kwargs={"pk": self.org1_user1_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["email"], "org1user1@prunedge.com")

    # Hey:I dont if this is good. Need clarity of team for this. Just testing this

    def test_retrieve_user_details(self):
        # A user member of an org retrieves details of another user in the same org
        self.org1_user_authenticator()
        # user1 retrieving details of user 2 Note:Same Org
        url = reverse("user:user-detail", kwargs={"pk": self.org1_user2_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["email"], "org1user2@prunedge.com")

    def test_retrieve_user_details_denied(self):
        # A user of an org trying to retieve details of a user in the another org
        self.org1_user_authenticator()
        # user1 retrieving details of user 1 Note:Different Org
        url = reverse("user:user-detail", kwargs={"pk": self.org2_user1_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_user_details_denied(self):
        # A user of an org trying to retieve details of a user in the another org
        self.org1_user_authenticator()
        # user1 retrieving details of user 1 Note:Different Org
        url = reverse("user:user-detail", kwargs={"pk": self.org2_user1_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_update_own_details(self):
        # user updating his own data
        self.org1_user_authenticator()
        url = reverse("user:user-detail", kwargs={"pk": self.org1_user1_id})
        data = {
            "firstname": "Updated"
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["firstname"], "Updated")

    # Hey, i dont know if this is good. Ask team abt this
    def test_user_can_update_users_details_same_org(self):
        # A user updating another user details in the same org
        self.org1_user_authenticator()
        url = reverse("user:user-detail", kwargs={"pk": self.org1_user2_id})
        data = {
            "firstname": "Update first"
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["firstname"], "Update first")

    def test_deny_user_update_details_different_org(self):
        # Deny user updating details of another user in different org
        self.org1_user_authenticator()
        url = reverse("user:user-detail", kwargs={"pk": self.org2_user1_id})
        data = {
            "email": "update_user2org1@email.com"
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_user_delete_data(self):
        self.org1_user_authenticator()
        url = reverse("user:user-detail", kwargs={"pk": self.org1_user1_id})
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # confirm actual delete
        self.assertEqual(User.objects.filter(
            email="org1user1@prunedge.com").count(), 0)


class UserInviteTests(APITestCase):
    def setUp(self):
        org_data = {
            "name": "First Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status": "ACTIVE"
        }
        org = Organisation.objects.create(**org_data)

        hr_admin_user_data = {
            "organisation": org,
            "email": "hradmin@prunedge.com",
            "password": "passer",
            "verified": True,
            "roles": ["HR_ADMIN"]
        }

        get_user_model().objects.create_user(**hr_admin_user_data)

        employee_user_data = {
            "organisation": org,
            "email": "employee@prunedge.com",
            "password": "passer",
            "verified": True,
        }

        get_user_model().objects.create_user(**employee_user_data)

    def hr_admin_authenticator(self):
        """Authenticate as HR ADMIN"""
        url = reverse("user:login")
        data = {
            "email": "hradmin@prunedge.com",
            "password": "passer",
        }
        settings.USE_TZ=False
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def employee_authenticator(self):
        """Authenticate as Employee"""
        url = reverse("user:login")
        data = {
            "email": "employee@prunedge.com",
            "password": "passer",
        }
        settings.USE_TZ=False
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    @mock.patch("user.tasks.send_new_user_email")
    def test_hr_admin_can_invite_a_user(self, mock_send_email):
        # Hey:In essence, this endpoint let Hr creatE/invute anotherhr user-> I dont
        # knw if that is what they mean....Cofirm
        self.hr_admin_authenticator()
        url = reverse("user:user-invite-user")
        data = {
            "email": "invitedhr@prdunedge.com",
            "password": "1234567890",
            "firstname": "Invited",
            "lastname": "Invited",

        }
        mock_send_email.delay.side_effect = print(
            "Sent to celery task:HR Admin Invite User Email!!!"
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check the user with the email has been created and role
        invited_user = get_user_model().objects.get(email="invitedhr@prdunedge.com")
        self.assertEqual(invited_user.email, "invitedhr@prdunedge.com")
        self.assertEqual(invited_user.roles, ["HR_ADMIN","EMPLOYEE"])
        # Hey!The newly created invited does not hava an organisation
        # I dont know if this is intended flow of d app
        self.assertIsNone(invited_user.organisation)

        # Test that mail was sent to the newly created org admin user.
        token = Token.objects.get(user__email="invitedhr@prdunedge.com")
        user = User.objects.get(email="invitedhr@prdunedge.com")

        user_email_args = {
            "id": user.id,
            "email": "invitedhr@prdunedge.com",
            "fullname": "Invited Invited",
            "url": f"https://{settings.CLIENT_URL}/user-signup/?token={token.token}"
            # "url": f"{settings.CLIENT_URL}/verify-user/?token={token.token}"
        }

        mock_send_email.delay.assert_called_once()
        mock_send_email.delay.assert_called_with(user_email_args)


class PasswordResetTests(APITestCase):
    def setUp(self):
        org_data = {
            "name": "Prunedge",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge",
            "status": "ACTIVE",
        }

        org = Organisation.objects.create(**org_data)

        user_data = {
            "organisation": org,
            "email": "employee@prunedge.com",
            "password": "super",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }

        get_user_model().objects.create_user(**user_data)

    def test_deny_initiate_reset(self):
        """Valid email address and but subdomain doesn't match can i"""
        url = reverse("user:user-initialize-reset")
        data = {
            "email": "employee@prunedge.com",
            "subdomain": "unknowedge"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
 
    @mock.patch("user.tasks.send_password_reset_email.delay")
    def test_valid_user_can_initiate_reset(self, mock_send_password_reset_email):
        """Requires Valid(existing) email address and org subdomain to matches"""
        url = reverse("user:user-initialize-reset")
        data = {
            "email": "employee@prunedge.com",
            "subdomain": "edge"
        }
        response = self.client.post(url, data, format="json")
        mock_send_password_reset_email.side_effect = print(
            "Sent to celery task:User Password Reset Email!!!"
        )
        
        
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test that password reset email was sent to the user
        token = Token.objects.get(user__email="employee@prunedge.com")
        user = User.objects.get(email="employee@prunedge.com")

        email_data = {
            "fullname": user.firstname,
            "email": user.email,
            "token": token.token,
        }
        mock_send_password_reset_email.assert_called_once()
        mock_send_password_reset_email.assert_called_with(email_data)


class TokenTests(APITestCase):
    
    def setUp(self):
        org_data = {
            "name": "Onboared Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "onboareded_org.hrms.com",
            "status":"ACTIVE",
        }

        org = Organisation.objects.create(**org_data)
        user_data = {
            "email": "ridwan@prunedge.com",
            "password": "one",
            "roles": ["EMPLOYEE"],
        }
        
        user = get_user_model().objects.create_user(**user_data)

        Employee.objects.create(user=user,organisation= org)
        
        token = {
            "user":user,
            "token":"8u9u9erer-=werrer",
            "token_type":"ACCOUNT_VERIFICATION"       
        }
        created_token =  Token.objects.create(**token)
        self.user_token = created_token.token
        
    def test_user_can_verify_token(self):
        #Token provided to activate email
        url = reverse("user:user-verify-token")
        data = {
            "token":self.user_token
        }
        settings.USE_TZ=True
        response = self.client.get(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["valid"], True)
    #Hey! I  dont know if this is good, same token works for password setting...
    #and acction verification
    def test_user_can_create_password(self):
        #token provided to set password
        url = reverse("user:user-create-password")
        data = {
            "token":self.user_token,
            "password":"Raylink"
        }
        settings.USE_TZ=True
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        


