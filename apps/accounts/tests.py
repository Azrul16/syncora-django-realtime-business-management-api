from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class AccountRegistrationTests(APITestCase):
    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(
            '/api/v1/auth/register/',
            {
                'email': 'new-user@example.com',
                'password': 'StrongPass1234',
                'first_name': 'New',
                'last_name': 'User',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'new-user@example.com')
        self.assertTrue(get_user_model().objects.filter(email='new-user@example.com').exists())

    def test_register_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            email='duplicate@example.com',
            password='StrongPass1234',
        )

        response = self.client.post(
            '/api/v1/auth/register/',
            {'email': 'duplicate@example.com', 'password': 'StrongPass1234'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['error']['details'])
