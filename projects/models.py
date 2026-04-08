from django.db import models
from django.conf import settings
from users.models import User  # <--- Импортируем класс модели

class Project(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_projects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'

    def __str__(self):
        return self.name

class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=User.ROLE_CHOICES, default='observer')  # <--- Исправлено

    class Meta:
        unique_together = ('project', 'user')
        verbose_name = 'Участник проекта'
        verbose_name_plural = 'Участники проекта'