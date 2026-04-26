import pytest
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from projects.models import ProjectMember
from tasks.models import Task

@pytest.mark.django_db
class TestTasksAPI:
    def test_create_task(self, auth_client, project):
        data = {'project': project.pk, 'title': 'Task 1', 'status': 'todo', 'priority': 'high'}
        response = auth_client.post('/api/tasks/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_task_status(self, auth_client, task):
        response = auth_client.patch(f'/api/tasks/{task.pk}/', {'status': 'in_progress'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.status == 'in_progress'

    def test_filter_tasks_by_status(self, auth_client, project):
        Task.objects.create(project=project, title='Done Task', status='done')
        response = auth_client.get('/api/tasks/?status=done')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_observer_cannot_update_task(self, api_client, observer_user, project, task):
        ProjectMember.objects.create(project=project, user=observer_user, role='observer')
        token = RefreshToken.for_user(observer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        response = api_client.patch(f'/api/tasks/{task.pk}/', {'status': 'done'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
