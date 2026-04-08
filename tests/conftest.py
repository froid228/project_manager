import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from projects.models import Project, ProjectMember
from tasks.models import Task

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(username='test_admin', password='testpass123', role='admin')

@pytest.fixture
def manager_user(db):
    return User.objects.create_user(username='test_manager', password='testpass123', role='manager')

@pytest.fixture
def member_user(db):
    return User.objects.create_user(username='test_member', password='testpass123', role='member')

@pytest.fixture
def observer_user(db):
    return User.objects.create_user(username='test_observer', password='testpass123', role='observer')

@pytest.fixture
def project(db, admin_user):
    return Project.objects.create(name='Тестовый проект', description='Описание для тестов', owner=admin_user)

@pytest.fixture
def project_with_member(db, project, member_user):
    ProjectMember.objects.create(project=project, user=member_user, role='member')
    return project

@pytest.fixture
def task(db, project, member_user):
    return Task.objects.create(project=project, title='Тестовая задача', status='todo', priority='medium', assignee=member_user)

@pytest.fixture
def auth_client(api_client, admin_user):
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client