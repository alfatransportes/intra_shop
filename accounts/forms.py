# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class CadastroForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "numero_cracha", "whatsapp", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        return email
