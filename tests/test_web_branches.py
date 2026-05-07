import pytest
from django.urls import reverse

from projects.models import Project, ProjectMember
from tasks.models import Task
from users.models import User


@pytest.mark.django_db
class TestLoginView:
    def test_login_page_get(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200

    def test_login_view_rejects_invalid_credentials(self, client):
        response = client.post(
            reverse("login"),
            {"username": "bad", "password": "bad"},
            follow=True,
        )

        assert response.status_code == 200
        assert "Неверные данные" in response.content.decode()

    def test_login_view_accepts_valid_credentials(self, client, admin_user):
        response = client.post(
            reverse("login"),
            {"username": "test_admin", "password": "testpass123"},
            follow=False,
        )

        assert response.status_code == 302
        assert response.url == "/"


@pytest.mark.django_db
class TestRegisterView:
    def test_register_page_get(self, client):
        response = client.get(reverse("register"))

        assert response.status_code == 200
        assert "Регистрация" in response.content.decode()

    def test_register_view_creates_user_and_logs_in(self, client):
        response = client.post(
            reverse("register"),
            {
                "username": "new_user",
                "email": "new@example.com",
                "phone": "+79990000000",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
            follow=False,
        )

        assert response.status_code == 302
        assert response.url == "/"
        user = User.objects.get(username="new_user")
        assert user.email == "new@example.com"
        assert user.phone == "+79990000000"
        assert user.role == "observer"
        assert user.check_password("StrongPass123")
        assert "_auth_user_id" in client.session


@pytest.mark.django_db
class TestDashboardAndProjectViews:
    def test_project_list_get_for_admin_shows_all_projects(self, client, admin_user, manager_user):
        Project.objects.create(name="Admin visible", description="x", owner=manager_user)

        client.force_login(admin_user)
        response = client.get(reverse("project-list"))

        assert response.status_code == 200
        assert "Admin visible" in response.content.decode()

    def test_dashboard_filters_data_for_regular_user(self, client, manager_user, member_user):
        owned_project = Project.objects.create(name="Owned", description="x", owner=member_user)
        joined_project = Project.objects.create(name="Joined", description="y", owner=manager_user)
        hidden_project = Project.objects.create(name="Hidden", description="z", owner=manager_user)
        ProjectMember.objects.create(project=joined_project, user=member_user, role="member")
        Task.objects.create(project=owned_project, title="Own task", status="todo", priority="medium")
        Task.objects.create(project=joined_project, title="Joined task", status="todo", priority="medium")
        Task.objects.create(project=hidden_project, title="Hidden task", status="todo", priority="medium")

        client.force_login(member_user)
        response = client.get(reverse("dashboard"))

        assert response.status_code == 200
        assert response.context["total_projects"] == 2
        assert response.context["total_tasks"] == 2

    def test_project_list_get_for_member_shows_only_accessible_projects(self, client, manager_user, member_user):
        visible_project = Project.objects.create(name="Visible", description="x", owner=manager_user)
        hidden_project = Project.objects.create(name="Hidden", description="y", owner=manager_user)
        ProjectMember.objects.create(project=visible_project, user=member_user, role="member")

        client.force_login(member_user)
        response = client.get(reverse("project-list"))

        content = response.content.decode()
        assert response.status_code == 200
        assert "Visible" in content
        assert "Hidden" not in content

    def test_project_list_invalid_post_renders_form_again(self, client, manager_user):
        client.force_login(manager_user)

        response = client.post(reverse("project-list"), {"name": "", "description": "x"})

        assert response.status_code == 200
        assert Project.objects.count() == 0

    def test_project_detail_get_for_observer_renders_page(self, client, project, observer_user):
        ProjectMember.objects.create(project=project, user=observer_user, role="observer")
        client.force_login(observer_user)

        response = client.get(reverse("project-detail", args=[project.pk]))

        assert response.status_code == 200
        assert response.context["project"] == project
        assert set(response.context["form"].fields["assignee"].queryset) == {project.owner, observer_user}

    def test_project_detail_post_creates_task(self, client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        client.force_login(project.owner)

        response = client.post(
            reverse("project-detail", args=[project.pk]),
            {
                "title": "Новая задача",
                "description": "Описание",
                "status": "todo",
                "priority": "medium",
                "assignee": member_user.pk,
                "deadline": "2030-01-01",
            },
            follow=True,
        )

        assert response.status_code == 200
        assert "Задача успешно добавлена!" in response.content.decode()
        assert project.tasks.filter(title="Новая задача").exists()

    def test_project_detail_invalid_post_keeps_user_on_page(self, client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        client.force_login(project.owner)

        response = client.post(
            reverse("project-detail", args=[project.pk]),
            {
                "title": "",
                "description": "Описание",
                "status": "todo",
                "priority": "medium",
                "assignee": member_user.pk,
            },
        )

        assert response.status_code == 200
        assert not project.tasks.filter(description="Описание").exists()


@pytest.mark.django_db
class TestTaskListViewBranches:
    def test_task_list_get_for_member_filters_visible_tasks(self, client, manager_user, member_user):
        visible_project = Project.objects.create(name="Visible", description="x", owner=manager_user)
        hidden_project = Project.objects.create(name="Hidden", description="y", owner=manager_user)
        ProjectMember.objects.create(project=visible_project, user=member_user, role="member")
        Task.objects.create(project=visible_project, title="Visible task", status="todo", priority="medium")
        Task.objects.create(project=hidden_project, title="Hidden task", status="todo", priority="medium")

        client.force_login(member_user)
        response = client.get(reverse("task-list"))

        content = response.content.decode()
        assert response.status_code == 200
        assert "Visible task" in content
        assert "Hidden task" not in content

    def test_task_list_delete_denied_without_manage_permission(self, client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        task = Task.objects.create(project=project, title="Task", status="done", priority="medium")
        client.force_login(member_user)

        response = client.post(
            reverse("task-list"),
            {"action": "delete_task", "task_id": task.pk},
            follow=True,
        )

        assert response.status_code == 200
        assert "У вас нет прав на удаление этой задачи." in response.content.decode()
        assert Task.objects.filter(pk=task.pk).exists()

    def test_task_list_delete_requires_done_status(self, client, project):
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"action": "delete_task", "task_id": task.pk},
            follow=True,
        )

        assert response.status_code == 200
        assert "Можно удалить только задачу со статусом «Готово»." in response.content.decode()
        assert Task.objects.filter(pk=task.pk).exists()

    def test_task_list_delete_handles_missing_task(self, client, project):
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"action": "delete_task", "task_id": 999999},
            follow=True,
        )

        assert response.status_code == 200
        assert "Задача не найдена." in response.content.decode()

    def test_task_list_delete_success(self, client, project):
        task = Task.objects.create(project=project, title="Task", status="done", priority="medium")
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"action": "delete_task", "task_id": task.pk},
            follow=True,
        )

        assert response.status_code == 200
        assert "Задача удалена." in response.content.decode()
        assert not Task.objects.filter(pk=task.pk).exists()

    def test_task_list_change_status_denied(self, client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client.force_login(member_user)

        response = client.post(
            reverse("task-list"),
            {"action": "change_status", "task_id": task.pk, "new_status": "done"},
            follow=True,
        )

        assert response.status_code == 200
        assert "У вас нет прав на изменение статуса." in response.content.decode()
        task.refresh_from_db()
        assert task.status == "todo"

    def test_task_list_change_status_rejects_invalid_value(self, client, project):
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"action": "change_status", "task_id": task.pk, "new_status": "bad"},
            follow=True,
        )

        assert response.status_code == 200
        assert "Некорректный статус." in response.content.decode()

    def test_task_list_change_status_handles_missing_task(self, client, project):
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"action": "change_status", "task_id": 999999, "new_status": "done"},
            follow=True,
        )

        assert response.status_code == 200
        assert "Задача не найдена." in response.content.decode()

    def test_task_list_change_status_success(self, client, project):
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"action": "change_status", "task_id": task.pk, "new_status": "done"},
            follow=True,
        )

        assert response.status_code == 200
        assert "Статус обновлён: Готово" in response.content.decode()
        task.refresh_from_db()
        assert task.status == "done"

    def test_task_list_change_assignee_success(self, client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"action": "change_assignee", "task_id": task.pk, "assignee": member_user.pk},
            follow=True,
        )

        assert response.status_code == 200
        assert "Исполнитель обновлён" in response.content.decode()
        task.refresh_from_db()
        assert task.assignee == member_user

    def test_task_list_change_assignee_denied_for_member(self, client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        task = Task.objects.create(project=project, title="Task", status="todo", priority="medium")
        client.force_login(member_user)

        response = client.post(
            reverse("task-list"),
            {"action": "change_assignee", "task_id": task.pk, "assignee": project.owner.pk},
            follow=True,
        )

        assert response.status_code == 200
        assert "У вас нет прав на изменение исполнителя." in response.content.decode()
        task.refresh_from_db()
        assert task.assignee is None

    def test_task_list_create_requires_project_selection(self, client, project):
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"title": "Task without project", "status": "todo", "priority": "medium"},
            follow=True,
        )

        assert response.status_code == 200
        assert "Выберите проект" in response.content.decode()

    def test_task_list_create_handles_missing_project(self, client, project):
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"project": 999999, "title": "Task", "status": "todo", "priority": "medium"},
            follow=True,
        )

        assert response.status_code == 200
        assert "Проект не найден" in response.content.decode()

    def test_task_list_create_denied_for_observer(self, client, project, observer_user):
        ProjectMember.objects.create(project=project, user=observer_user, role="observer")
        client.force_login(observer_user)

        response = client.post(
            reverse("task-list"),
            {"project": project.pk, "title": "Task", "status": "todo", "priority": "medium"},
        )

        assert response.status_code == 200
        assert "Нет прав добавлять задачи в этот проект" in response.content.decode()

    def test_task_list_create_invalid_form_does_not_save_task(self, client, project):
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {"project": project.pk, "title": "", "status": "todo", "priority": "medium"},
        )

        assert response.status_code == 200
        assert project.tasks.count() == 0

    def test_task_list_create_success(self, client, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        client.force_login(project.owner)

        response = client.post(
            reverse("task-list"),
            {
                "project": project.pk,
                "title": "Созданная задача",
                "description": "Описание",
                "status": "todo",
                "priority": "medium",
                "assignee": member_user.pk,
                "deadline": "2030-01-01",
            },
            follow=True,
        )

        assert response.status_code == 200
        assert "Задача успешно создана!" in response.content.decode()
        assert project.tasks.filter(title="Созданная задача").exists()
