from django import forms
from django.contrib.auth import get_user_model
from .models import Project

User = get_user_model()


class ProjectForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label='Участники проекта',
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    member_role = forms.ChoiceField(
        label='Роль выбранных участников',
        choices=(
            ('manager', 'Менеджер проекта'),
            ('member', 'Участник'),
            ('observer', 'Наблюдатель'),
        ),
        required=False,
        initial='member',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название проекта'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание проекта'}),
        }

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        users = User.objects.order_by('username')
        if current_user and current_user.is_authenticated:
            users = users.exclude(pk=current_user.pk)
        self.fields['members'].queryset = users
