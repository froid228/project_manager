import pytest
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from projects.models import ProjectMember

@pytest.mark.django_db
class TestPermissions:
    def test_admin_edit_any_project(self, auth_client, project):
        response = auth_client.patch(f'/api/projects/{project.pk}/', {'name': 'Edited by Admin'}, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_manager_cannot_edit_other_project(self, api_client, manager_user, project):
        token = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        url = f'/api/projects/{project.pk}/'
        response = api_client.patch(url, {'name': 'Hacked'}, format='json')
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_observer_cannot_create_task(self, api_client, observer_user, project):
        ProjectMember.objects.create(project=project, user=observer_user, role='observer')
        token = RefreshToken.for_user(observer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = api_client.post('/api/tasks/', {'project': project.pk, 'title': 'Observer Task'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN