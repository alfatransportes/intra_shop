# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("email",)

    list_display = (
        "email",
        "numero_cracha",
        "whatsapp",
        "unidade",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "email",
        "numero_cracha",
        "whatsapp",
        "unidade__nome",
        "unidade__codigo",
    )

    list_filter = (
        "is_staff",
        "is_active",
        "unidade",
    )

    autocomplete_fields = ("unidade",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {
            "fields": (
                "numero_cracha",
                "whatsapp",
                "unidade",
            )
        }),
        ("Permissões", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Datas importantes", {
            "fields": (
                "last_login",
                "date_joined",
            )
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
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

    readonly_fields = ("last_login", "date_joined")
