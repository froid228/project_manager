from rest_framework.permissions import BasePermission

class IsProjectMemberOrAdmin(BasePermission):
    """Разрешает доступ, если пользователь Admin или участник проекта."""
    
    def has_permission(self, request, view):
        # Блокируем создание задач для Наблюдателей (Observer)
        if view.action == 'create':
            return request.user.role != 'observer'
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        project = obj.project if hasattr(obj, 'project') else obj
        return project.memberships.filter(user=request.user).exists() or project.owner == request.user

class CanManageProject(BasePermission):
    """Разрешает управление проектами только Админам и Менеджерам."""

    def has_permission(self, request, view):
        # Запрещаем создание проектов всем, кроме Admin и Manager
        if view.action == 'create':
            return request.user.role in ('admin', 'manager')
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.role in ('admin', 'manager'):
            return True
        return obj.owner == request.user