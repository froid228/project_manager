from rest_framework.permissions import BasePermission

class IsProjectMemberOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        project = obj.project if hasattr(obj, 'project') else obj
        return project.memberships.filter(user=request.user).exists() or project.owner == request.user

class CanManageProject(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ('admin', 'manager'):
            return True
        return obj.owner == request.user
