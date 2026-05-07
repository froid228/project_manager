import builtins
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

import manage
from core.permissions import (
    CanManageProject,
    IsProjectMemberOrAdmin,
    can_access_project,
    can_manage_project,
    get_project_for_object,
)
from core.templatetags.russian_plural import ru_plural
from core.views import project_people_queryset
from projects.models import ProjectMember
from tasks.serializers import TaskSerializer


def make_request(user, method="GET", data=None):
    return SimpleNamespace(user=user, method=method, data=data or {})


@pytest.mark.django_db
class TestPermissionsHelpers:
    def test_get_project_for_object_returns_project_attribute(self, project):
        wrapper = SimpleNamespace(project=project)
        assert get_project_for_object(wrapper) == project

    def test_get_project_for_object_returns_object_itself(self, project):
        assert get_project_for_object(project) == project

    def test_can_access_project_for_anonymous_user(self, project):
        assert can_access_project(AnonymousUser(), project) is False

    def test_can_access_project_for_admin_owner_member_and_stranger(
        self, admin_user, manager_user, member_user, observer_user, project
    ):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        owned_by_manager = type(project).objects.create(
            name="Проект менеджера",
            description="Личный проект",
            owner=manager_user,
        )

        assert can_access_project(admin_user, project) is True
        assert can_access_project(manager_user, owned_by_manager) is True
        assert can_access_project(member_user, project) is True
        assert can_access_project(observer_user, project) is False

    def test_can_manage_project_for_roles(self, admin_user, manager_user, member_user, project):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        ProjectMember.objects.create(project=project, user=member_user, role="member")

        assert can_manage_project(admin_user, project) is True
        assert can_manage_project(project.owner, project) is True
        assert can_manage_project(manager_user, project) is True
        assert can_manage_project(member_user, project) is False

    def test_can_manage_project_without_access_is_false(self, observer_user, project):
        assert can_manage_project(observer_user, project) is False


@pytest.mark.django_db
class TestPermissionClasses:
    def test_is_project_member_or_admin_denies_unauthenticated_request(self):
        permission = IsProjectMemberOrAdmin()
        request = make_request(AnonymousUser(), method="POST")
        view = SimpleNamespace(action="create")
        assert permission.has_permission(request, view) is False

    def test_is_project_member_or_admin_denies_observer_create(self, observer_user):
        permission = IsProjectMemberOrAdmin()
        request = make_request(observer_user, method="POST", data={"project": 1})
        view = SimpleNamespace(action="create")
        assert permission.has_permission(request, view) is False

    def test_is_project_member_or_admin_allows_create_without_project(self, manager_user):
        permission = IsProjectMemberOrAdmin()
        request = make_request(manager_user, method="POST", data={})
        view = SimpleNamespace(action="create")
        assert permission.has_permission(request, view) is True

    def test_is_project_member_or_admin_denies_create_for_missing_project(self, manager_user):
        permission = IsProjectMemberOrAdmin()
        request = make_request(manager_user, method="POST", data={"project": 999999})
        view = SimpleNamespace(action="create")
        assert permission.has_permission(request, view) is False

    def test_is_project_member_or_admin_checks_project_access(self, manager_user, project):
        permission = IsProjectMemberOrAdmin()
        request = make_request(manager_user, method="POST", data={"project": project.pk})
        view = SimpleNamespace(action="create")
        assert permission.has_permission(request, view) is False

    def test_is_project_member_or_admin_allows_non_create_requests(self, manager_user):
        permission = IsProjectMemberOrAdmin()
        request = make_request(manager_user, method="GET")
        view = SimpleNamespace(action="list")
        assert permission.has_permission(request, view) is True

    def test_is_project_member_or_admin_safe_method_uses_access_check(self, member_user, project):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        permission = IsProjectMemberOrAdmin()
        request = make_request(member_user, method="GET")
        assert permission.has_object_permission(request, SimpleNamespace(), project) is True

    def test_is_project_member_or_admin_denies_observer_write(self, observer_user, project):
        ProjectMember.objects.create(project=project, user=observer_user, role="observer")
        permission = IsProjectMemberOrAdmin()
        request = make_request(observer_user, method="PATCH")
        assert permission.has_object_permission(request, SimpleNamespace(), project) is False

    def test_is_project_member_or_admin_allows_member_write(self, member_user, project):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        permission = IsProjectMemberOrAdmin()
        request = make_request(member_user, method="PATCH")
        assert permission.has_object_permission(request, SimpleNamespace(), project) is True

    def test_can_manage_project_permission_denies_unauthenticated_request(self):
        permission = CanManageProject()
        request = make_request(AnonymousUser(), method="POST")
        view = SimpleNamespace(action="create")
        assert permission.has_permission(request, view) is False

    def test_can_manage_project_permission_for_create_roles(self, admin_user, manager_user, observer_user):
        permission = CanManageProject()
        view = SimpleNamespace(action="create")

        assert permission.has_permission(make_request(admin_user, method="POST"), view) is True
        assert permission.has_permission(make_request(manager_user, method="POST"), view) is True
        assert permission.has_permission(make_request(observer_user, method="POST"), view) is False

    def test_can_manage_project_permission_allows_non_create_authenticated(self, member_user):
        permission = CanManageProject()
        request = make_request(member_user, method="GET")
        view = SimpleNamespace(action="list")
        assert permission.has_permission(request, view) is True

    def test_can_manage_project_object_permission(self, manager_user, member_user, project):
        ProjectMember.objects.create(project=project, user=manager_user, role="manager")
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        permission = CanManageProject()
        request_manager = make_request(manager_user, method="PATCH")
        request_member = make_request(member_user, method="PATCH")

        assert permission.has_object_permission(request_manager, SimpleNamespace(), project) is True
        assert permission.has_object_permission(request_member, SimpleNamespace(), project) is False


@pytest.mark.django_db
class TestTaskSerializerValidation:
    def test_denies_work_with_foreign_project(self, manager_user, member_user, project):
        factory = APIRequestFactory()
        request = factory.post("/api/tasks/", {}, format="json")
        request.user = manager_user

        serializer = TaskSerializer(
            data={"project": project.pk, "title": "Task", "status": "todo", "priority": "medium"},
            context={"request": request},
        )

        with pytest.raises(serializers.ValidationError, match="чужого проекта"):
            serializer.is_valid(raise_exception=True)

    def test_denies_observer_write(self, observer_user, project):
        ProjectMember.objects.create(project=project, user=observer_user, role="observer")
        factory = APIRequestFactory()
        request = factory.post("/api/tasks/", {}, format="json")
        request.user = observer_user

        serializer = TaskSerializer(
            data={"project": project.pk, "title": "Task", "status": "todo", "priority": "medium"},
            context={"request": request},
        )

        with pytest.raises(serializers.ValidationError, match="только права на чтение"):
            serializer.is_valid(raise_exception=True)

    def test_denies_assignee_outside_project(self, admin_user, manager_user, member_user, project):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        factory = APIRequestFactory()
        request = factory.post("/api/tasks/", {}, format="json")
        request.user = admin_user

        serializer = TaskSerializer(
            data={
                "project": project.pk,
                "title": "Task",
                "status": "todo",
                "priority": "medium",
                "assignee": manager_user.pk,
            },
            context={"request": request},
        )

        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.is_valid(raise_exception=True)

        assert "assignee" in exc_info.value.detail

    def test_denies_project_transfer_if_current_assignee_not_in_new_project(
        self, admin_user, manager_user, member_user, observer_user, project, task
    ):
        new_project = type(project).objects.create(
            name="Другой проект",
            description="Для переноса",
            owner=manager_user,
        )
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        factory = APIRequestFactory()
        request = factory.patch("/api/tasks/1/", {}, format="json")
        request.user = admin_user

        serializer = TaskSerializer(
            instance=task,
            data={"project": new_project.pk},
            partial=True,
            context={"request": request},
        )

        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.is_valid(raise_exception=True)

        assert "project" in exc_info.value.detail
        assert observer_user.username != task.assignee.username

    def test_accepts_valid_payload_for_project_owner_as_assignee(self, admin_user, project):
        factory = APIRequestFactory()
        request = factory.post("/api/tasks/", {}, format="json")
        request.user = admin_user

        serializer = TaskSerializer(
            data={
                "project": project.pk,
                "title": "Task",
                "status": "todo",
                "priority": "medium",
                "assignee": project.owner.pk,
            },
            context={"request": request},
        )

        assert serializer.is_valid(), serializer.errors

    def test_get_request_does_not_block_observer(self, observer_user, project):
        ProjectMember.objects.create(project=project, user=observer_user, role="observer")
        factory = APIRequestFactory()
        request = factory.get("/api/tasks/")
        request.user = observer_user

        serializer = TaskSerializer(
            instance=[],
            many=True,
            context={"request": request},
        )

        assert serializer.data == []


@pytest.mark.django_db
class TestTemplateAndModels:
    def test_russian_plural_handles_all_branches(self):
        assert ru_plural("abc", "задача,задачи,задач") == "abc"
        assert ru_plural(1, "задача,задачи") == 1
        assert ru_plural(11, "задача,задачи,задач") == "11 задач"
        assert ru_plural(1, "задача,задачи,задач") == "1 задача"
        assert ru_plural(3, "задача,задачи,задач") == "3 задачи"
        assert ru_plural(5, "задача,задачи,задач") == "5 задач"

    def test_model_string_representations(self, admin_user, project, task):
        assert str(admin_user) == "test_admin (Администратор)"
        assert str(project) == "Тестовый проект"
        assert str(task) == "[К выполнению] Тестовая задача"

    def test_project_people_queryset_returns_owner_and_members_once(self, project, member_user):
        ProjectMember.objects.create(project=project, user=member_user, role="member")
        ProjectMember.objects.create(project=project, user=project.owner, role="manager")

        people = list(project_people_queryset(project).order_by("id"))

        assert people == [project.owner, member_user]


@pytest.mark.django_db
class TestInfrastructureAndSeed:
    def test_seed_command_creates_demo_data(self):
        call_command("seed")

        from users.models import User
        from projects.models import Project
        from tasks.models import Task

        assert User.objects.filter(username="admin_demo", role="admin").exists()
        assert User.objects.filter(username="manager_demo", role="manager").exists()
        assert User.objects.filter(username="member_demo", role="member").exists()
        assert User.objects.filter(username="observer_demo", role="observer").exists()
        assert Project.objects.filter(name="Разработка веб-приложения").exists()
        assert Task.objects.filter(project__name="Разработка веб-приложения").count() == 2

    def test_manage_main_executes_command(self, monkeypatch):
        captured = {}

        def fake_execute(argv):
            captured["argv"] = argv

        monkeypatch.setattr("django.core.management.execute_from_command_line", fake_execute)
        monkeypatch.setattr(manage.sys, "argv", ["manage.py", "check"])

        manage.main()

        assert captured["argv"] == ["manage.py", "check"]

    def test_manage_main_wraps_import_error(self, monkeypatch):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "django.core.management":
                raise ImportError("boom")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        assert fake_import("math") is __import__("math")

        with pytest.raises(ImportError, match="Couldn't import Django."):
            manage.main()

    def test_manage_script_entrypoint_runs_main(self, monkeypatch):
        captured = {}

        def fake_execute(argv):
            captured["argv"] = argv

        monkeypatch.setattr("django.core.management.execute_from_command_line", fake_execute)
        monkeypatch.setattr("sys.argv", ["manage.py", "check"])

        runpy.run_path(str(Path(__file__).resolve().parents[1] / "manage.py"), run_name="__main__")

        assert captured["argv"] == ["manage.py", "check"]

    def test_asgi_and_wsgi_modules_expose_application(self):
        import config.asgi
        import config.wsgi

        assert config.asgi.application is not None
        assert config.wsgi.application is not None

    def test_settings_uses_postgres_when_env_is_present(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_DB", "course_db")
        monkeypatch.setenv("POSTGRES_USER", "course_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "course_pass")
        monkeypatch.setenv("POSTGRES_HOST", "db.local")
        monkeypatch.setenv("POSTGRES_PORT", "5433")

        settings_path = Path(__file__).resolve().parents[1] / "config" / "settings.py"
        settings_namespace = runpy.run_path(str(settings_path))

        assert settings_namespace["DATABASES"]["default"]["ENGINE"] == "django.db.backends.postgresql"
        assert settings_namespace["DATABASES"]["default"]["NAME"] == "course_db"
        assert settings_namespace["DATABASES"]["default"]["USER"] == "course_user"
        assert settings_namespace["DATABASES"]["default"]["PASSWORD"] == "course_pass"
        assert settings_namespace["DATABASES"]["default"]["HOST"] == "db.local"
        assert settings_namespace["DATABASES"]["default"]["PORT"] == "5433"
