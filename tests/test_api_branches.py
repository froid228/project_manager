import pytest
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from projects.models import Project, ProjectMember
from tasks.models import Task


def authorize(api_client, user):
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.mark.django_db
class TestProjectMemberApi:
    def test_member_list_is_available_to_project_participant(self, api_client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        client = authorize(api_client, member_user)

        response = client.get(f"/api/projects/{project.pk}/members/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["user"]["id"] == member_user.pk

    def test_member_list_is_forbidden_for_foreign_user(self, api_client, project, manager_user):
        client = authorize(api_client, manager_user)

        response = client.get(f"/api/projects/{project.pk}/members/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_add_project_member(self, api_client, project, manager_user, observer_user):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        client = authorize(api_client, manager_user)

        response = client.post(
            f"/api/projects/{project.pk}/members/",
            {"user_id": observer_user.pk, "role": "observer"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert ProjectMember.objects.filter(project=project, user=observer_user, role="observer").exists()

    def test_regular_member_cannot_add_project_member(self, api_client, project, member_user, observer_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        client = authorize(api_client, member_user)

        response = client.post(
            f"/api/projects/{project.pk}/members/",
            {"user_id": observer_user.pk, "role": "observer"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_update_project_member_role(self, api_client, project, manager_user, member_user):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        membership = ProjectMember.objects.create(project=project, user=member_user, role="member")
        client = authorize(api_client, manager_user)

        response = client.patch(
            f"/api/projects/{project.pk}/members/{membership.pk}/",
            {"role": "observer"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.role == "observer"

    def test_regular_member_cannot_update_project_member_role(self, api_client, project, member_user, observer_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        membership = ProjectMember.objects.create(project=project, user=observer_user, role="observer")
        client = authorize(api_client, member_user)

        response = client.patch(
            f"/api/projects/{project.pk}/members/{membership.pk}/",
            {"role": "member"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_delete_project_member(self, api_client, project, manager_user, member_user):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        membership = ProjectMember.objects.create(project=project, user=member_user, role="member")
        client = authorize(api_client, manager_user)

        response = client.delete(f"/api/projects/{project.pk}/members/{membership.pk}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ProjectMember.objects.filter(pk=membership.pk).exists()

    def test_regular_member_cannot_delete_project_member(self, api_client, project, member_user, observer_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        membership = ProjectMember.objects.create(project=project, user=observer_user, role="observer")
        client = authorize(api_client, member_user)

        response = client.delete(f"/api/projects/{project.pk}/members/{membership.pk}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTaskApiBranches:
    def test_admin_sees_all_tasks_in_list(self, api_client, admin_user, manager_user, project):
        foreign_project = Project.objects.create(name="Foreign", description="x", owner=manager_user)
        Task.objects.create(project=foreign_project, title="Visible for admin", status="todo", priority="medium")
        client = authorize(api_client, admin_user)

        response = client.get("/api/tasks/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_member_sees_tasks_from_joined_project(self, api_client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        Task.objects.create(project=project, title="Joined task", status="todo", priority="medium")
        client = authorize(api_client, member_user)

        response = client.get("/api/tasks/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_delete_task_requires_manage_rights(self, api_client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        task = Task.objects.create(project=project, title="Done task", status="done", priority="medium")
        client = authorize(api_client, member_user)

        response = client.delete(f"/api/tasks/{task.pk}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_task_requires_done_status(self, api_client, project, manager_user):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        task = Task.objects.create(project=project, title="Not done", status="todo", priority="medium")
        client = authorize(api_client, manager_user)

        response = client.delete(f"/api/tasks/{task.pk}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_done_task_by_manager(self, api_client, project, manager_user):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        task = Task.objects.create(project=project, title="Done", status="done", priority="medium")
        client = authorize(api_client, manager_user)

        response = client.delete(f"/api/tasks/{task.pk}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Task.objects.filter(pk=task.pk).exists()

    def test_change_status_requires_permission(self, api_client, project, manager_user, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client = authorize(api_client, member_user)

        response = client.patch(f"/api/tasks/{task.pk}/change_status/", {"status": "done"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_change_status_validates_status_value(self, api_client, project, manager_user):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client = authorize(api_client, manager_user)

        response = client.patch(f"/api/tasks/{task.pk}/change_status/", {"status": "bad"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_status_succeeds_for_assignee(self, api_client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        task = Task.objects.create(
            project=project,
            title="Task",
            status="todo",
            priority="medium",
            assignee=member_user,
        )
        client = authorize(api_client, member_user)

        response = client.patch(
            f"/api/tasks/{task.pk}/change_status/",
            {"status": "done"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.status == "done"


@pytest.mark.django_db
class TestUsersApiBranches:
    def test_staff_admin_can_list_and_create_users(self, api_client, admin_user):
        admin_user.is_staff = True
        admin_user.save(update_fields=["is_staff"])
        client = authorize(api_client, admin_user)

        list_response = client.get("/api/users/")
        create_response = client.post(
            "/api/users/",
            {"username": "created_user", "email": "created@example.com", "role": "member"},
            format="json",
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert create_response.status_code == status.HTTP_201_CREATED

    def test_non_staff_user_cannot_access_user_list(self, api_client, member_user):
        client = authorize(api_client, member_user)

        response = client.get("/api/users/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_access_any_user_detail(self, api_client, admin_user, member_user):
        client = authorize(api_client, admin_user)

        response = client.get(f"/api/users/{member_user.pk}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == member_user.pk

    def test_regular_user_can_access_only_own_detail(self, api_client, member_user, observer_user):
        client = authorize(api_client, member_user)

        own_response = client.get(f"/api/users/{member_user.pk}/")
        foreign_response = client.get(f"/api/users/{observer_user.pk}/")

        assert own_response.status_code == status.HTTP_200_OK
        assert foreign_response.status_code == status.HTTP_404_NOT_FOUND
