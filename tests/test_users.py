import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestAuthentication:
    def test_get_token_success(self, api_client, admin_user):
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {'username': 'test_admin', 'password': 'testpass123'})
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_get_token_fail(self, api_client):
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {'username': 'wrong_user', 'password': 'wrong_pass'})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_without_token(self, api_client):
        response = api_client.get('/api/projects/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_with_token(self, auth_client):
        response = auth_client.get('/api/projects/')
        assert response.status_code == status.HTTP_200_OK