# app/signals.py
from __future__ import annotations

from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver


def _iter_file_fields(instance: models.Model):
    """
    Retorna todos os campos FileField/ImageField de uma instância.
    """
    for field in instance._meta.get_fields():
        # só campos concretos na model (não relações)
        if isinstance(field, models.FileField):
            yield field


def _delete_file(file_field):
    """
    Apaga o arquivo físico do storage, se existir.
    """
    if not file_field:
        return
    try:
        storage = file_field.storage
        name = file_field.name
        if name and storage.exists(name):
            storage.delete(name)
    except Exception:
        # Evita quebrar delete/save por causa de storage.
        # Se quiser logar, coloque um logger aqui.
        pass


@receiver(post_delete)
def delete_files_on_instance_delete(sender, instance, **kwargs):
    """
    Quando a instância é deletada, apaga todos os arquivos dela.
    """
    for field in _iter_file_fields(instance):
        _delete_file(getattr(instance, field.name, None))


@receiver(pre_save)
def delete_old_files_on_change(sender, instance, **kwargs):
    """
    Antes de salvar, se um FileField/ImageField mudou (inclusive virou None por "remover?"),
    apaga o arquivo antigo do storage.
    """
    if not instance.pk:
        return  # criação, não tem antigo

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    for field in _iter_file_fields(instance):
        field_name = field.name

        old_file = getattr(old, field_name, None)
        new_file = getattr(instance, field_name, None)

        old_name = getattr(old_file, "name", None) if old_file else None
        new_name = getattr(new_file, "name", None) if new_file else None

        # mudou (inclui caso "remover?" => new_name == None/"")
        if old_name and old_name != new_name:
            _delete_file(old_file)
