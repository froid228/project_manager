from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Администратор'),
        ('manager', 'Менеджер проекта'),
        ('member', 'Участник'),
        ('observer', 'Наблюдатель'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='observer')
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
