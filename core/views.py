from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from projects.models import Project
from tasks.models import Task
from projects.forms import ProjectForm
from tasks.forms import TaskForm
from core.permissions import can_access_project, can_manage_project

User = get_user_model()


def project_people_queryset(project):
    return User.objects.filter(
        Q(id=project.owner_id) | Q(projectmember__project=project)
    ).distinct()

@login_required
def dashboard(request):
    user = request.user
    if user.role == 'admin':
        projects = Project.objects.all()
        tasks = Task.objects.all()
    else:
        projects = Project.objects.filter(Q(owner=user) | Q(memberships__user=user)).distinct()
        tasks = Task.objects.filter(
            Q(project__owner=user) | Q(project__memberships__user=user) | Q(assignee=user)
        ).distinct()
    return render(request, 'dashboard.html', {
        'projects': projects[:5], 'tasks': tasks[:5],
        'total_projects': projects.count(), 'total_tasks': tasks.count()
    })

@login_required
def project_list(request):
    user = request.user
    if request.method == 'POST' and user.role in ('admin', 'manager'):
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = user
            project.save()
            messages.success(request, 'Проект успешно создан!')
            return redirect('project-list')
    else:
        form = ProjectForm()

    if user.role == 'admin':
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(Q(owner=user) | Q(memberships__user=user)).distinct()
    return render(request, 'projects/list.html', {'projects': projects, 'form': form})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_access_project(request.user, project):
        messages.error(request, 'У вас нет доступа к этому проекту.')
        return redirect('project-list')

    can_add_task = request.user.role != 'observer' and can_access_project(request.user, project)

    if request.method == 'POST' and can_add_task:
        form = TaskForm(request.POST)
        form.fields['assignee'].queryset = project_people_queryset(project)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            messages.success(request, 'Задача успешно добавлена!')
            return redirect('project-detail', pk=pk)
    else:
        form = TaskForm()
    form.fields['assignee'].queryset = project_people_queryset(project)

    return render(request, 'projects/detail.html', {
        'project': project,
        'tasks': project.tasks.all().order_by('-deadline'),
        'members': project.memberships.select_related('user').all(),
        'form': form,
        'status_choices': Task.STATUS_CHOICES  # ⬅️ Добавлено
    })

@login_required
def task_list(request):
    user = request.user

    if user.role == 'admin':
        projects = Project.objects.all()
        tasks = Task.objects.all()
    else:
        projects = Project.objects.filter(Q(memberships__user=user) | Q(owner=user)).distinct()
        tasks = Task.objects.filter(
            Q(project__owner=user) | Q(project__memberships__user=user) | Q(assignee=user)
        ).distinct()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete_task':
            task_id = request.POST.get('task_id')
            try:
                task = tasks.get(pk=task_id)
                if not can_manage_project(user, task.project):
                    messages.error(request, 'У вас нет прав на удаление этой задачи.')
                elif task.status != 'done':
                    messages.error(request, 'Можно удалить только задачу со статусом «Готово».')
                else:
                    task.delete()
                    messages.success(request, 'Задача удалена.')
            except Task.DoesNotExist:
                messages.error(request, 'Задача не найдена.')
            return redirect('task-list')

        elif action == 'change_status':
            task_id = request.POST.get('task_id')
            new_status = request.POST.get('new_status')
            try:
                task = tasks.get(pk=task_id)
                if (
                    user.role != 'admin'
                    and task.project.owner_id != user.id
                    and task.assignee_id != user.id
                    and not can_manage_project(user, task.project)
                ):
                    messages.error(request, 'У вас нет прав на изменение статуса.')
                elif new_status not in dict(Task.STATUS_CHOICES):
                    messages.error(request, 'Некорректный статус.')
                else:
                    task.status = new_status
                    task.save(update_fields=['status'])
                    messages.success(request, f'Статус обновлён: {dict(Task.STATUS_CHOICES)[new_status]}')
            except Task.DoesNotExist:
                messages.error(request, 'Задача не найдена.')
            return redirect('task-list')

        # ➕ Создание новой задачи (стандартная логика)
        else:
            project_id = request.POST.get('project')
            if project_id:
                try:
                    project = Project.objects.get(pk=project_id)
                    if not can_access_project(user, project) or user.role == 'observer':
                        messages.error(request, 'Нет прав добавлять задачи в этот проект')
                        form = TaskForm()
                        form.fields['assignee'].queryset = User.objects.none()
                        return render(request, 'tasks/list.html', {'tasks': tasks, 'form': form, 'projects': projects, 'status_choices': Task.STATUS_CHOICES})

                    form = TaskForm(request.POST)
                    form.fields['assignee'].queryset = project_people_queryset(project)
                    if form.is_valid():
                        task = form.save(commit=False)
                        task.project = project
                        task.save()
                        messages.success(request, 'Задача успешно создана!')
                except Project.DoesNotExist:
                    messages.error(request, 'Проект не найден')
            else:
                messages.error(request, 'Выберите проект')
            form = TaskForm()

    else:
        form = TaskForm()

    form.fields['assignee'].queryset = User.objects.filter(
        Q(id__in=projects.values_list('owner_id', flat=True))
        | Q(projectmember__project__in=projects)
    ).distinct()

    return render(request, 'tasks/list.html', {
        'tasks': tasks,
        'form': form,
        'projects': projects,
        'status_choices': Task.STATUS_CHOICES
    })
