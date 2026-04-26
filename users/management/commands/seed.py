from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from projects.models import Project, ProjectMember
from tasks.models import Task


User = get_user_model()


class Command(BaseCommand):
    help = 'Создаёт демо-данные для курсового проекта по управлению проектами.'

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username='admin_demo',
            defaults={'role': 'admin', 'email': 'admin@example.com'},
        )
        admin.set_password('demo12345')
        admin.save(update_fields=['password'])

        manager, _ = User.objects.get_or_create(
            username='manager_demo',
            defaults={'role': 'manager', 'email': 'manager@example.com'},
        )
        manager.set_password('demo12345')
        manager.save(update_fields=['password'])

        member, _ = User.objects.get_or_create(
            username='member_demo',
            defaults={'role': 'member', 'email': 'member@example.com'},
        )
        member.set_password('demo12345')
        member.save(update_fields=['password'])

        observer, _ = User.objects.get_or_create(
            username='observer_demo',
            defaults={'role': 'observer', 'email': 'observer@example.com'},
        )
        observer.set_password('demo12345')
        observer.save(update_fields=['password'])

        project, _ = Project.objects.get_or_create(
            name='Разработка веб-приложения',
            defaults={
                'description': 'Демонстрационный проект для управления задачами команды.',
                'owner': manager,
            },
        )

        ProjectMember.objects.get_or_create(project=project, user=member, defaults={'role': 'member'})
        ProjectMember.objects.get_or_create(project=project, user=observer, defaults={'role': 'observer'})

        Task.objects.get_or_create(
            project=project,
            title='Подготовить архитектурную схему',
            defaults={
                'description': 'Сформировать MVT-архитектуру и связи между приложениями.',
                'status': 'in_progress',
                'priority': 'high',
                'assignee': member,
                'deadline': date.today() + timedelta(days=3),
            },
        )
        Task.objects.get_or_create(
            project=project,
            title='Оформить отчёт по ГОСТ 7.32-2017',
            defaults={
                'description': 'Подготовить пояснительную записку и список использованных источников.',
                'status': 'todo',
                'priority': 'medium',
                'assignee': manager,
                'deadline': date.today() + timedelta(days=7),
            },
        )

        self.stdout.write(self.style.SUCCESS('Демо-данные успешно созданы.'))
