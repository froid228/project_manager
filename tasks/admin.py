from django.contrib import admin

from .models import Task, TaskComment, TaskHistory


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'priority', 'assignee', 'deadline')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title', 'description')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')
    search_fields = ('task__title', 'author__username', 'text')


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'field_name', 'old_value', 'new_value', 'user', 'created_at')
    list_filter = ('field_name', 'created_at')
