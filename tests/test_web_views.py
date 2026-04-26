import pytest
from django.urls import reverse
from projects.models import Project

@pytest.mark.django_db
class TestWebViews:
    def test_dashboard_redirect_if_anonymous(self, client):
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302

    def test_dashboard_accessible_logged_in(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200

    def test_web_create_project(self, client, manager_user):
        client.force_login(manager_user)
        response = client.post(reverse('project-list'), {'name': 'Web Project', 'description': 'Test'}, follow=True)
        assert response.status_code == 200
        assert 'Проект успешно создан!' in response.content.decode()

    def test_project_detail_denied_for_foreign_user(self, client, manager_user, member_user):
        project = Project.objects.create(name='Hidden', description='Private', owner=manager_user)
        client.force_login(member_user)
        response = client.get(reverse('project-detail', args=[project.pk]), follow=True)
        assert response.status_code == 200
        assert 'У вас нет доступа к этому проекту.' in response.content.decode()
