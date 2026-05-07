from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label='Email', required=False)
    phone = forms.CharField(label='Телефон', max_length=20, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Логин',
            'email': 'Email',
            'phone': 'Телефон',
            'password1': 'Пароль',
            'password2': 'Повторите пароль',
        }
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': placeholders.get(name, field.label),
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'observer'
        if commit:
            user.save()
        return user
