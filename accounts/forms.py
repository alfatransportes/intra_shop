import requests
from django import forms
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm,
                                       PasswordResetForm, SetPasswordForm,
                                       UserCreationForm)

from .models import User
from .utils import consultar_usuario_liberado


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Já existe um usuário cadastrado com este e-mail.")

        return email

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        cpf = cleaned_data.get("cpf")

        if not email or not cpf:
            return cleaned_data

        try:
            usuario_liberado = consultar_usuario_liberado(email, cpf)

            if not usuario_liberado:
                raise forms.ValidationError(
                    "Seu CPF e e-mail não possuem liberação para cadastro."
                )

        except requests.RequestException:
            raise forms.ValidationError(
                "Não foi possível validar sua liberação no momento."
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()
        user.username = user.email

        if commit:
            user.save()

        return user


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Seu e-mail",
            "autocomplete": "email",
        })

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["new_password1"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Nova senha",
            "autocomplete": "new-password",
        })

        self.fields["new_password2"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Confirmar nova senha",
            "autocomplete": "new-password",
        })


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["old_password"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Senha atual",
            "autocomplete": "current-password",
        })

        self.fields["new_password1"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Nova senha",
            "autocomplete": "new-password",
        })

        self.fields["new_password2"].widget.attrs.update({
            "class": "form-control rounded-5",
            "placeholder": "Confirmar nova senha",
            "autocomplete": "new-password",
        })