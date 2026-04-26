from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import status as drf_status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Task
from .serializers import TaskSerializer
from core.permissions import IsProjectMemberOrAdmin, can_manage_project

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMemberOrAdmin]
    filterset_fields = ('status', 'priority', 'assignee')

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Task.objects.all()
        return Task.objects.filter(
            Q(project__owner=user) | Q(project__memberships__user=user) | Q(assignee=user)
        ).distinct()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not can_manage_project(request.user, instance.project):
            raise PermissionDenied('Удалять задачи может только администратор или менеджер проекта.')
        if instance.status != 'done':
            raise PermissionDenied('Удалить можно только задачи со статусом «Готово».')
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['patch'])
    def change_status(self, request, pk=None):
        task = self.get_object()

        if (
            request.user.role != 'admin'
            and task.project.owner_id != request.user.id
            and task.assignee_id != request.user.id
            and not can_manage_project(request.user, task.project)
        ):
            return Response({'detail': 'Нет прав на изменение статуса.'}, status=drf_status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        valid_statuses = dict(Task.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({'detail': 'Недопустимый статус.'}, status=drf_status.HTTP_400_BAD_REQUEST)

        task.status = new_status
        task.save(update_fields=['status'])
        serializer = self.get_serializer(task)
        return Response(serializer.data)
