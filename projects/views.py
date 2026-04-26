from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from .models import Project, ProjectMember
from .serializers import ProjectSerializer, ProjectMemberSerializer
from core.permissions import can_access_project, can_manage_project, CanManageProject

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Project.objects.all()
        return Project.objects.filter(
            Q(owner=user) | Q(memberships__user=user)
        ).distinct()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), CanManageProject()]
        return super().get_permissions()

class ProjectMemberViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_project(self):
        project = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if not can_access_project(self.request.user, project):
            raise PermissionDenied('Нет доступа к участникам этого проекта.')
        return project

    def get_queryset(self):
        return self.get_project().memberships.select_related('user').all()

    def perform_create(self, serializer):
        project = self.get_project()
        if not can_manage_project(self.request.user, project):
            raise PermissionDenied('Нет прав на изменение состава участников.')
        serializer.save(project=project)

    def perform_update(self, serializer):
        if not can_manage_project(self.request.user, serializer.instance.project):
            raise PermissionDenied('Нет прав на изменение состава участников.')
        serializer.save()

    def perform_destroy(self, instance):
        if not can_manage_project(self.request.user, instance.project):
            raise PermissionDenied('Нет прав на изменение состава участников.')
        instance.delete()
