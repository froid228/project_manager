from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import status as drf_status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Task, TaskComment, TaskHistory
from .serializers import TaskCommentSerializer, TaskHistorySerializer, TaskSerializer
from core.permissions import IsProjectMemberOrAdmin, can_manage_project


TRACKED_FIELDS = ('status', 'priority', 'assignee', 'deadline')


def display_value(value):
    if value is None:
        return ''
    return str(value)


def record_task_history(task, user, field_name, old_value, new_value):
    old_display = display_value(old_value)
    new_display = display_value(new_value)
    if old_display == new_display:
        return
    TaskHistory.objects.create(
        task=task,
        user=user,
        field_name=field_name,
        old_value=old_display,
        new_value=new_display,
    )

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMemberOrAdmin]
    filterset_fields = ('status', 'priority', 'assignee')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Task.objects.none()

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

    def perform_update(self, serializer):
        old_task = Task.objects.get(pk=serializer.instance.pk)
        task = serializer.save()
        for field_name in TRACKED_FIELDS:
            old_value = getattr(old_task, f'{field_name}_id', None) if field_name == 'assignee' else getattr(old_task, field_name)
            new_value = getattr(task, f'{field_name}_id', None) if field_name == 'assignee' else getattr(task, field_name)
            record_task_history(task, self.request.user, field_name, old_value, new_value)

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

        old_status = task.status
        task.status = new_status
        task.save(update_fields=['status'])
        record_task_history(task, request.user, 'status', old_status, new_status)
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        task = self.get_object()

        if request.method == 'GET':
            comments = task.comments.select_related('author').all()
            serializer = TaskCommentSerializer(comments, many=True)
            return Response(serializer.data)

        if request.user.role == 'observer':
            return Response({'detail': 'Наблюдатель не может добавлять комментарии.'}, status=drf_status.HTTP_403_FORBIDDEN)

        serializer = TaskCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task, author=request.user)
        return Response(serializer.data, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        task = self.get_object()
        history = task.history.select_related('user').all()
        serializer = TaskHistorySerializer(history, many=True)
        return Response(serializer.data)
