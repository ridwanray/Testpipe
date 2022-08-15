# from django.contrib.auth import get_user_model
# from rest_framework import status
# from rest_framework.reverse import reverse
# from rest_framework.test import APITestCase
#
# PASSWORD = 'pAssw0rd!'
#
#
# def create_user(email='user@example.com', password=PASSWORD, **kwargs):
#     return get_user_model().objects.create_user(email, password, **kwargs)
#
#
# class AuthenticationTest(APITestCase):
#
#     def test_user_can_sign_up(self):
#         """User can sign up"""
#         response = self.client.post(reverse('user:signup'), data={
#             'email': 'user@example.com',
#             'firstname': 'Test',
#             'lastname': 'User',
#             'password': PASSWORD,
#         })
#         user = get_user_model().objects.last()
#         self.assertEqual(status.HTTP_201_CREATED, response.status_code)
#         self.assertEqual(response.data['id'], str(user.id))
#         self.assertEqual(response.data['lastname'], user.lastname)
#         self.assertEqual(response.data['firstname'], user.firstname)
#
#     def test_user_can_log_in(self):
#         user = create_user()
#         response = self.client.post(reverse('user:signin'), data={
#                                     'username': user.email, 'password': PASSWORD})
#         self.assertEqual(status.HTTP_200_OK, response.status_code)
#         self.assertEqual(response.data['email'], user.email)
#
#     def test_user_can_log_out(self):
#         user = create_user()
#         self.client.login(username=user.email, password=PASSWORD)
#         response = self.client.post(reverse('user:signout'))
#         self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
