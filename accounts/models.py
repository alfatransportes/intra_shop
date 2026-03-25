# accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models

from website.models import Unidade


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    cpf = models.CharField(max_length=11, blank=True, null=True, validators=[RegexValidator(r"^[0-9]+$", "Use apenas números no CPF.")])
    email = models.EmailField(unique=True, blank=False, null=False)

    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=False,
        blank=False,
        verbose_name="Unidade",
    )

    numero_cracha = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r"^[0-9]+$", "Use apenas números no crachá.")],
        verbose_name="Número do crachá",
        blank=True, null=True
    )

    whatsapp = models.CharField(
        max_length=20,
        validators=[RegexValidator(r"^\+?\d{10,15}$", "WhatsApp inválido. Ex: +5511999999999")],
        verbose_name="WhatsApp",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["numero_cracha", "whatsapp"]

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.cpf})"
