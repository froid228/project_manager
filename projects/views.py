from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Project, ProjectMember
from .serializers import ProjectSerializer, ProjectMemberSerializer
from core.permissions import IsProjectMemberOrAdmin, CanManageProject

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Project.objects.all()
        return Project.objects.filter(owner=user) | Project.objects.filter(memberships__user=user)

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [CanManageProject()]
        return super().get_permissions()

class ProjectMemberViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticated, CanManageProject]

    def get_queryset(self):
        return ProjectMember.objects.filter(project_id=self.kwargs.get('project_pk'))

    def perform_create(self, serializer):
        serializer.save(project_id=self.kwargs.get('project_pk'))
