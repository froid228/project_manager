from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from projects.models import Project, ProjectMember
from tasks.models import Task
from random import choice, randint
from datetime import timedelta, date

User = get_user_model()

class Command(BaseCommand):
    help = 'Заполняет БД демо-данными для курсовой'

    def handle(self, *args, **kwargs):
        if User.objects.count() > 1:
            self.stdout.write(self.style.WARNING('⚠️ Данные уже есть. Пропускаю.'))
            return

        # 1. Пользователи
        users_data = [
            ('admin', 'admin@example.com', 'admin', '123'),
            ('manager_ivan', 'ivan@example.com', 'manager', '123'),
            ('member_anna', 'anna@example.com', 'member', '123'),
            ('observer_petr', 'petr@example.com', 'observer', '123'),
        ]
        created_users = []
        for uname, email, role, pwd in users_data:
            u = User.objects.create_user(username=uname, email=email, password=pwd, role=role)
            created_users.append(u)
            self.stdout.write(f'✅ {role}: {uname}')

        # 2. Проекты
        proj1 = Project.objects.create(
            name='Разработка CRM',
            description='Система управления клиентами для отдела продаж',
            owner=created_users[0]
        )
        proj2 = Project.objects.create(
            name='Мобильное приложение',
            description='iOS/Android клиент для доставки еды',
            owner=created_users[1]
        )
        self.stdout.write('✅ Создано 2 проекта')

        # 3. Участники проектов
        ProjectMember.objects.create(project=proj1, user=created_users[1], role='manager')
        ProjectMember.objects.create(project=proj1, user=created_users[2], role='member')
        ProjectMember.objects.create(project=proj2, user=created_users[2], role='member')
        ProjectMember.objects.create(project=proj2, user=created_users[3], role='observer')
        self.stdout.write('✅ Назначены участники')

        # 4. Задачи
        statuses = ['todo', 'in_progress', 'done']
        priorities = ['low', 'medium', 'high']
        
        for i in range(1, 6):
            Task.objects.create(
                project=proj1,
                title=f'Настроить авторизацию v{i}',
                status=choice(statuses),
                priority=choice(priorities),
                assignee=created_users[2],
                deadline=date.today() + timedelta(days=randint(1, 14))
            )
        
        for i in range(1, 4):
            Task.objects.create(
                project=proj2,
                title=f'Реализовать push-уведомления {i}',
                status='todo',
                priority='high',
                assignee=created_users[2],
                deadline=date.today() + timedelta(days=i*3)
            )
        
        self.stdout.write(self.style.SUCCESS('🎉 Демо-данные загружены!'))