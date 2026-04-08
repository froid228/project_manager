from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
