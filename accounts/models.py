# accounts/models.py
from django.apps import apps
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_unidade_padrao(self):
        Unidade = apps.get_model("website", "Unidade")

        unidade = Unidade.objects.filter(codigo=1).order_by("id").first()

        if not unidade:
            unidade = Unidade.objects.create(
                codigo=1,
                nome="Matriz"
            )

        return unidade

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")

        email = self.normalize_email(email)

        if not extra_fields.get("unidade") and not extra_fields.get("unidade_id"):
            extra_fields["unidade"] = self.get_unidade_padrao()

        user = self.model(
            email=email,
            username=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    cpf = models.CharField(
        max_length=11,
        blank=False,
        null=False,
        validators=[
            RegexValidator(r"^[0-9]+$", "Use apenas números no CPF.")
        ],
    )

    email = models.EmailField(
        unique=True,
        blank=False,
        null=False,
    )

    unidade = models.ForeignKey(
        "website.Unidade",
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=False,
        blank=False,
        verbose_name="Unidade",
    )

    numero_cracha = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(r"^[0-9]+$", "Use apenas números no crachá.")
        ],
        verbose_name="Número do crachá",
        blank=False,
        null=False,
    )

    whatsapp = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                r"^\+?\d{10,15}$",
                "WhatsApp inválido. Ex: +5511999999999"
            )
        ],
        verbose_name="WhatsApp",
        blank=False,
        null=False,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["cpf", "numero_cracha", "whatsapp"]

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.cpf})"