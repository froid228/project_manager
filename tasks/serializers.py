from rest_framework import serializers
from .models import Task
from core.permissions import can_access_project

class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        request = self.context['request']
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        assignee = attrs.get('assignee')
        project_changed = 'project' in attrs

        if project and not can_access_project(request.user, project):
            raise serializers.ValidationError('Нельзя работать с задачами чужого проекта.')

        if request.method != 'GET' and request.user.role == 'observer':
            raise serializers.ValidationError('Наблюдатель имеет только права на чтение.')

        if assignee and project:
            is_project_owner = project.owner_id == assignee.id
            is_member = project.memberships.filter(user=assignee).exists()
            if not is_project_owner and not is_member:
                raise serializers.ValidationError(
                    {'assignee': 'Исполнитель должен быть владельцем проекта или его участником.'}
                )

        if project_changed and not assignee and self.instance and self.instance.assignee:
            current_assignee = self.instance.assignee
            is_project_owner = project.owner_id == current_assignee.id
            is_member = project.memberships.filter(user=current_assignee).exists()
            if not is_project_owner and not is_member:
                raise serializers.ValidationError(
                    {'project': 'Нельзя перенести задачу в проект, где текущий исполнитель не состоит.'}
                )

        return attrs
