from rest_framework import serializers
from .models import Project, ProjectMember
from users.serializers import UserSerializer


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=ProjectMember._meta.get_field('user').related_model.objects.all(), write_only=True, source='user')

    class Meta:
        model = ProjectMember
        fields = ('id', 'user', 'user_id', 'role')

class ProjectSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(many=True, read_only=True, source='memberships')
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'owner', 'members', 'tasks_count', 'created_at')
        read_only_fields = ('owner', 'created_at')

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)
