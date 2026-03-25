# accounts/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import (StyledAuthenticationForm, StyledPasswordChangeForm,
                    StyledPasswordResetForm, StyledSetPasswordForm)

urlpatterns = [
    path("cadastrar/", views.cadastrar, name="cadastrar"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=StyledAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # ESQUECI SENHA
    path(
        "senha/reset/",
        auth_views.PasswordResetView.as_view(
            form_class=StyledPasswordResetForm,
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.txt",
            html_email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),

    path(
        "senha/reset/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),

    path(
        "senha/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=StyledSetPasswordForm,
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),

    path(
        "senha/reset/feito/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),

    # ALTERAR SENHA (LOGADO)
    path(
        "senha/alterar/",
        auth_views.PasswordChangeView.as_view(
            form_class=StyledPasswordChangeForm,
            template_name="accounts/password_change_form.html",
            success_url=reverse_lazy("password_change_done"),
        ),
        name="password_change",
    ),

    path(
        "senha/alterar/feito/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="password_change_done",
    ),
]
