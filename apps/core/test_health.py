from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckTests(APITestCase):
    def test_health_check_is_public_and_checks_database(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'healthy', 'database': 'connected'})


class WebAppTests(APITestCase):
    def test_web_app_page_loads(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'Syncora')
        self.assertContains(response, 'id="loginForm"')
        self.assertContains(response, '/static/core/app.js')
