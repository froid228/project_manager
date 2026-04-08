from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Task
from .serializers import TaskSerializer
from core.permissions import IsProjectMemberOrAdmin

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMemberOrAdmin]
    filterset_fields = ('status', 'priority', 'assignee')

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Task.objects.all()
        return Task.objects.filter(project__memberships__user=user) | Task.objects.filter(assignee=user)
