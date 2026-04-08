import pytest
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from projects.models import Project

@pytest.mark.django_db
class TestProjectsAPI:
    def test_create_project_admin(self, auth_client):
        response = auth_client.post('/api/projects/', {'name': 'New Proj', 'description': 'Test'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_project_manager(self, api_client, manager_user):
        token = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = api_client.post('/api/projects/', {'name': 'Manager Proj', 'description': 'Test'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_project_observer_forbidden(self, api_client, observer_user):
        token = RefreshToken.for_user(observer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = api_client.post('/api/projects/', {'name': 'Forbidden'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_projects_member(self, api_client, member_user, project_with_member):
        token = RefreshToken.for_user(member_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = api_client.get('/api/projects/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_delete_project_owner(self, auth_client, project):
        response = auth_client.delete(f'/api/projects/{project.pk}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Project.objects.filter(pk=project.pk).exists()