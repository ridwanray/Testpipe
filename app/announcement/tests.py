from urllib import response
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from announcement.models import Announcement
from employee.models import Employee
from organisation.models import Organisation, OrganisationNode
from django.conf import settings

# Sample Tree Structure used in Announcement Tests
# 0                         org -->root_org_node
# 1     Software            Talent              Sales
# 2 FrontEnd  BackEnd  Training   Acqui.  Physical   Online
class CreateAnnouncementTests(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        super_admin_user_data = {
            "email": "super@superorg.com",
            "password": "super",
            "verified": True,
            "roles": ["SUPERADMIN"],
        }
        get_user_model().objects.create_user(**super_admin_user_data)

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
        # attach root node to org
        org_root_node = OrganisationNode.objects.create(
            organisation=org, name=org.name, parent=None
        )

        hr_admin_user_data = {
            "organisation": org,
            "email": "orghradmin@org.com",
            "password": "hradmin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        get_user_model().objects.create_user(**hr_admin_user_data)

        employee_user_data = {
            "organisation": org,
            "email": "employee@org.com",
            "password": "employee",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }

        get_user_model().objects.create_user(**employee_user_data)

        # Create a tree structure for the organisation
        # Create parent nodes. Software, Talent, Sales
        parentnode1_data = {
            "parent": org_root_node,
            "name": "Software",
            "level": 1,
            "organisation": org,
        }

        parentnode1 = OrganisationNode.objects.create(**parentnode1_data)

        self.parentnode1_id = parentnode1.id

        parentnode2_data = {
            "parent": org_root_node,
            "name": "Talent",
            "level": 1,
            "organisation": org,
        }

        parentnode2 = OrganisationNode.objects.create(**parentnode2_data)

        self.parentnode2_id = parentnode2.id

        parentnode3_data = {
            "parent": org_root_node,
            "name": "Sales",
            "level": 1,
            "organisation": org,
        }

        parentnode3 = OrganisationNode.objects.create(**parentnode3_data)

        self.parentnode3_id = parentnode3.id

        # Create child nodes..(Frontend, Backend) (Training, Acquisition) (Online,Physical)
        first_childnode_p1data = {
            "parent": parentnode1,
            "name": "FRONT END",
            "level": 2,
            "organisation": org,
        }

        OrganisationNode.objects.create(**first_childnode_p1data)

        second_childnode_p1data = {
            "parent": parentnode1,
            "name": "BACK END",
            "level": 2,
            "organisation": org,
        }

        OrganisationNode.objects.create(**second_childnode_p1data)

        first_childnode_p2data = {
            "parent": parentnode2,
            "name": "Talent Training",
            "level": 2,
            "organisation": org,
        }

        OrganisationNode.objects.create(**first_childnode_p2data)

        second_childnode_p2data = {
            "parent": parentnode2,
            "name": "Talent Acquisition",
            "level": 2,
            "organisation": org,
        }

        OrganisationNode.objects.create(**second_childnode_p2data)

        first_childnode_p3data = {
            "parent": parentnode3,
            "name": "Sales Physical",
            "level": 2,
            "organisation": org,
        }

        OrganisationNode.objects.create(**first_childnode_p3data)

        second_childnode_p3data = {
            "parent": parentnode3,
            "name": "Sales Online",
            "level": 2,
            "organisation": org,
        }

        OrganisationNode.objects.create(**second_childnode_p3data)

    def employee_authenticator(self):
        """Login as an employee"""
        url = reverse("user:login")
        data = {
            "email": "employee@org.com",
            "password": "employee",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def org_hradmin_authenticator(self):
        """Login as an organisation HR Admin"""
        url = reverse("user:login")
        data = {
            "email": "orghradmin@org.com",
            "password": "hradmin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def super_admin_authenticator(self):
        """Login as a super-admin on the system"""
        url = reverse("user:login")
        data = {
            "email": "employee@org.com",
            "password": "empoyee",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_employee_cannot_create_announcement(self):
        self.employee_authenticator()
        url = reverse("announcement:announcement-list")
        data = {
            "title": "1st Announce",
            "description": "Hey, just a sample",
            "category": "EVENT",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_create_announcement_to_all(self):
        """Target announcements to all nodes i.e. from the org root node"""
        self.org_hradmin_authenticator()
        url = reverse("announcement:announcement-list")
        data = {
            "title": "1st Announce",
            "description": "Hey, just a sample",
            "category": "EVENT",
            "nodes": [],
            "level": "all",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["title"], "1st Announce")
        self.assertEqual(response.json()["data"]["description"], "Hey, just a sample")
        # check that the attached nodes to the announcement created is correct

        expected_nodes = [
            str(self.parentnode1_id),
            str(self.parentnode2_id),
            str(self.parentnode2_id),
        ]
        returned_nodes = response.json()["data"]["nodes"]

        # check if returned_node contain all expected nodes
        result = all(node in returned_nodes for node in expected_nodes)
        self.assertEqual(result, True)

    def test_can_create_announcement_to_specific_nodes_level(self):
        """Target announcements to all nodesi.e. from the org root node"""
        self.org_hradmin_authenticator()
        url = reverse("announcement:announcement-list")
        data = {
            "title": "Simple Announce",
            "description": "Simple simple",
            "category": "EVENT",
            "nodes": [str(self.parentnode1_id)],
            "level": 1,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["title"], "Simple Announce")
        self.assertEqual(response.json()["data"]["description"], "Simple simple")
        self.assertEqual(response.json()["data"]["level"], str(1))
        self.assertEqual(len(response.json()["data"]["nodes"]), 1)


class UpdateRetrieveAnnouncementTests(APITestCase):
    settings.USE_TZ = False

    def setUp(self):
        org_data = {
            "name": "First Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 4,
            "package": "CORE HR",
            "subdomain": "another.hrms.com",
            "status":"ACTIVE",
        }
        onboarded_org = Organisation.objects.create(**org_data)

        hr_admin_user_data = {
            "organisation": onboarded_org,
            "email": "hradmin@prunedge.com",
            "password": "hradmin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }

        employee_user_data = {
            "organisation": onboarded_org,
            "email": "employee@org.com",
            "password": "emp",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }

        hr_admin = get_user_model().objects.create_user(**hr_admin_user_data)
        get_user_model().objects.create_user(**employee_user_data)

        announce_data = {
            "created_by": hr_admin,
            "title": "Announce 1",
            "description": "Desc 1",
            "category": "EVENT",
        }

        announce_1 = Announcement.objects.create(**announce_data)
        self.created_announce_id = announce_1.id

    def hr_admin_authenticator(self):
        url = reverse("user:login")
        data = {
            "email": "hradmin@prunedge.com",
            "password": "hradmin",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def employee_authenticator(self):
        url = reverse("user:login")
        data = {
            "email": "employee@org.com",
            "password": "emp",
        }
        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_can_update_announcement(self):
        self.hr_admin_authenticator()
        url = reverse(
            "announcement:announcement-detail", kwargs={"pk": self.created_announce_id}
        )
        data = {
            "title": "Updated Announce 1",
            "description": "Updated Des",
            "nodes": [],
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], "Updated Announce 1")
        self.assertEqual(response.json()["description"], "Updated Des")

    def test_can_delete_announcement(self):
        self.hr_admin_authenticator()
        url = reverse(
            "announcement:announcement-detail", kwargs={"pk": self.created_announce_id}
        )

        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_can_retrieve_announcement(self):
        self.hr_admin_authenticator()
        url = reverse(
            "announcement:announcement-detail", kwargs={"pk": self.created_announce_id}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], "Announce 1")
        self.assertEqual(response.json()["description"], "Desc 1")
        self.assertEqual(response.json()["category"], "EVENT")

    def test_employee_user_cannot_delete(self):
        self.employee_authenticator()
        url = reverse(
            "announcement:announcement-detail", kwargs={"pk": self.created_announce_id}
        )

        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveEmployeeAnnouncementTests(APITestCase):
    # Tree to retrieve announcement for employee.
    # 0                         org -->root_org_node
    # 1     Software           Talent              Sales
    # 2 Employee1
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
        # attach root node to org
        org_root_node = OrganisationNode.objects.create(
            organisation=org, name=org.name, parent=None
        )

        hr_admin_user_data = {
            "organisation": org,
            "email": "hradmin@org.com",
            "password": "hradmin",
            "verified": True,
            "roles": ["HR_ADMIN"],
        }
        hr_admin_user = get_user_model().objects.create_user(**hr_admin_user_data)

        org_data = {
            "name": "Org",
            "sector": "PRIVATE",
            "type": "MULTIPLE",
            "size": 10,
            "package": "CORE HR",
            "subdomain": "edge.hrms.com",
            "status":"ACTIVE",
        }

        # Create parent nodes. Software, Talent, Sales
        parentnode1_data = {
            "parent": org_root_node,
            "name": "Software",
            "level": 1,
            "organisation": org,
        }

        parentnode1 = OrganisationNode.objects.create(**parentnode1_data)

        self.software_node = parentnode1.id

        parentnode2_data = {
            "parent": org_root_node,
            "name": "Talent",
            "level": 1,
            "organisation": org,
        }

        parentnode2 = OrganisationNode.objects.create(**parentnode2_data)

        self.parentnode2_id = parentnode2.id

        parentnode3_data = {
            "parent": org_root_node,
            "name": "Sales",
            "level": 1,
            "organisation": org,
        }

        parentnode3 = OrganisationNode.objects.create(**parentnode3_data)

        self.parentnode3_id = parentnode3.id

        # Create announcements targeting Software i.e. Node
        announce1_data = {
            "title": "Announce 1",
            "description": "Desc. 1",
            "category": "EVENT",
            "level": 1,
            "created_by": hr_admin_user,
        }

        announce2_data = {
            "title": "Announce 2",
            "description": "New hire msg ",
            "category": "New Hire",
            "level": 1,
            "created_by": hr_admin_user,
        }
        # nodes.set(node_ids)
        announcement1 = Announcement.objects.create(**announce1_data)
        announcement2 = Announcement.objects.create(**announce2_data)
        announcement1.nodes.set([self.software_node])
        announcement2.nodes.set([self.software_node])

        employee_user_data = {
            "organisation": org,
            "email": "employee@prunedge.com",
            "password": "employee",
            "verified": True,
            "roles": ["EMPLOYEE"],
        }

        employee_user = get_user_model().objects.create_user(**employee_user_data)
        Employee.objects.create(user=employee_user, organisation=org)

    def employee_authenticator(self):
        """Login as an employee"""
        url = reverse("user:login")
        data = {
            "email": "employee@prunedge.com",
            "password": "employee",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def admin_authenticator(self):
        """Login as an employee"""
        url = reverse("user:login")
        data = {
            "email": "hradmin@org.com",
            "password": "hradmin",
        }

        response = self.client.post(url, data, format="json")
        token = response.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_employee_can_retrieve_announcements(self):
        """Retrieve announcements where the employee is a receiver/recipient"""
        self.employee_authenticator()
        url = reverse("announcement:announcement-employee-announcement")

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Todos:check if employee retrieves his associated announcements.

    def test_nonemployee_cannot_retrieve(self):
        """Permission Tests on the endpoin"""
        self.admin_authenticator()
        url = reverse("announcement:announcement-employee-announcement")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
