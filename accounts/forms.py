# accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Float label precisa de placeholder e form-control
        self.fields["username"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "E-mail",
            "autocomplete": "username",
        })

        self.fields["password"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Senha",
            "autocomplete": "current-password",
        })


class CadastroForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "cpf",
            "email",
            "numero_cracha",
            "whatsapp",
            "unidade",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cpf"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Número do CPF",
        })

        self.fields["email"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "E-mail",
            "autocomplete": "email",
        })

        self.fields["numero_cracha"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Número do crachá",
        })

        self.fields["whatsapp"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "WhatsApp",
        })

        self.fields["unidade"].widget.attrs.update({
            "class": "form-select rounded-5",
        })

        self.fields["password1"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Senha",
            "autocomplete": "new-password",
        })

        self.fields["password2"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Confirmar senha",
            "autocomplete": "new-password",
        })

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)

        # usa o CPF como username
        user.username = self.cleaned_data["cpf"]

        if commit:
            user.save()

        return user