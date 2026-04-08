from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.exceptions import PermissionDenied
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

    # 🔒 Блокируем удаление, если задача не выполнена
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'done':
            raise PermissionDenied("Удалить можно только задачи со статусом «Готово».")
        return super().destroy(request, *args, **kwargs)

    # 🔄 Экшен для смены статуса через API (PATCH /api/tasks/<id>/change_status/)
    @action(detail=True, methods=['patch'])
    def change_status(self, request, pk=None):
        task = self.get_object()
        
        # Права: админ, владелец проекта или исполнитель задачи
        if request.user.role != 'admin' and task.project.owner != request.user and task.assignee != request.user:
            return Response({'detail': 'Нет прав на изменение статуса.'}, status=drf_status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        # Валидация статуса
        valid_statuses = dict(Task.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({'detail': 'Недопустимый статус.'}, status=drf_status.HTTP_400_BAD_REQUEST)

        task.status = new_status
        task.save(update_fields=['status'])
        serializer = self.get_serializer(task)
        return Response(serializer.data)