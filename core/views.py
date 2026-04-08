from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from projects.models import Project
from tasks.models import Task
from projects.forms import ProjectForm
from tasks.forms import TaskForm

@login_required
def dashboard(request):
    user = request.user
    projects = Project.objects.filter(owner=user) | Project.objects.filter(memberships__user=user)
    tasks = Task.objects.filter(assignee=user)
    return render(request, 'dashboard.html', {
        'projects': projects[:5], 'tasks': tasks[:5],
        'total_projects': projects.count(), 'total_tasks': tasks.count()
    })

@login_required
def project_list(request):
    user = request.user
    # Обработка создания нового проекта
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

    projects = Project.objects.filter(owner=user) | Project.objects.filter(memberships__user=user)
    return render(request, 'projects/list.html', {'projects': projects, 'form': form})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    # Проверка прав на создание задачи
    can_add_task = (request.user.role in ('admin', 'manager') or project.owner == request.user)
    
    # Обработка создания новой задачи
    if request.method == 'POST' and can_add_task:
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            messages.success(request, 'Задача успешно добавлена!')
            return redirect('project-detail', pk=pk)
    else:
        form = TaskForm()

    return render(request, 'projects/detail.html', {
        'project': project,
        'tasks': project.tasks.all().order_by('-deadline'),
        'members': project.memberships.select_related('user').all(),
        'form': form
    })

@login_required
def task_list(request):
    user = request.user
    
    # Обработка создания задачи (POST-запрос)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            # Если пользователь не админ, проверяем доступ к проекту
            if user.role != 'admin':
                # Упрощенная проверка: пользователь должен быть участником проекта задачи
                if not task.project.memberships.filter(user=user).exists() and task.project.owner != user:
                     messages.error(request, 'У вас нет прав добавлять задачи в этот проект')
                     return redirect('task-list')
            
            task.save()
            messages.success(request, 'Задача успешно создана!')
            return redirect('task-list')
    else:
        form = TaskForm()

    # Выборка задач
    if user.role == 'admin':
        tasks = Task.objects.all()
    else:
        tasks = Task.objects.filter(project__memberships__user=user) | Task.objects.filter(assignee=user)

    return render(request, 'tasks/list.html', {'tasks': tasks, 'form': form})