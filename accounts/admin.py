from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class UserAdminCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "cpf", "unidade", "numero_cracha", "whatsapp")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Já existe um usuário com este e-mail.")
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("As senhas não conferem.")

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()
        user.username = user.email
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class UserAdminChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Senha")

    class Meta:
        model = User
        fields = "__all__"

    def clean_password(self):
        return self.initial["password"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserAdminCreationForm
    form = UserAdminChangeForm
    model = User

    list_display = ("email", "cpf", "numero_cracha", "unidade", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "unidade")

    ordering = ("email",)
    search_fields = ("email", "cpf", "numero_cracha", "whatsapp")

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Dados pessoais", {"fields": ("cpf", "numero_cracha", "whatsapp", "unidade")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "cpf",
                "numero_cracha",
                "whatsapp",
                "unidade",
                "password1",
                "password2",
                "is_staff",
                "is_superuser",
                "is_active",
            ),
        }),
    )