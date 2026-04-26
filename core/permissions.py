from rest_framework.permissions import SAFE_METHODS, BasePermission

from projects.models import Project


def get_project_for_object(obj):
    return obj.project if hasattr(obj, 'project') else obj


def can_access_project(user, project):
    if not user.is_authenticated:
        return False
    if user.role == 'admin':
        return True
    if project.owner_id == user.id:
        return True
    return project.memberships.filter(user=user).exists()


def can_manage_project(user, project):
    if not can_access_project(user, project):
        return False
    if user.role == 'admin' or project.owner_id == user.id:
        return True
    return project.memberships.filter(user=user, role='manager').exists()


class IsProjectMemberOrAdmin(BasePermission):
    """Даёт доступ к проекту его участникам, владельцу и администратору."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if view.action == 'create':
            if request.user.role == 'observer':
                return False

            project_id = request.data.get('project')
            if not project_id:
                return True

            try:
                project = Project.objects.get(pk=project_id)
            except Project.DoesNotExist:
                return False

            return can_access_project(request.user, project)

        return True

    def has_object_permission(self, request, view, obj):
        project = get_project_for_object(obj)

        if request.method in SAFE_METHODS:
            return can_access_project(request.user, project)

        if request.user.role == 'observer':
            return False

        return can_access_project(request.user, project)


class CanManageProject(BasePermission):
    """Разрешает управление только администратору и менеджеру своего проекта."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if view.action == 'create':
            return request.user.role in ('admin', 'manager')

        return True

    def has_object_permission(self, request, view, obj):
        return can_manage_project(request.user, get_project_for_object(obj))
