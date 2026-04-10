from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from website.models import Produto

from .forms_produto_rapido import (ProdutoImagemRapidoFormSet,
                                   ProdutoRapidoForm,
                                   ProdutoVariacaoRapidoFormSet)


class DashboardPermissionMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)


class ProdutoRapidoBaseView(DashboardPermissionMixin):
    model = Produto
    form_class = ProdutoRapidoForm
    template_name = "dashboard/produtos/form_rapido.html"
    success_url = reverse_lazy("dashboard_produto_list")

    def get_formsets(self, data=None, files=None, instance=None):
        return {
            "image_formset": ProdutoImagemRapidoFormSet(
                data=data,
                files=files,
                instance=instance,
                prefix="imagens",
            ),
            "variation_formset": ProdutoVariacaoRapidoFormSet(
                data=data,
                files=files,
                instance=instance,
                prefix="variacoes",
            ),
        }

    def build_status_cards(self, produto, image_formset=None, variation_formset=None, posted_usa_variacoes=None):
        usa_variacoes = posted_usa_variacoes
        if usa_variacoes is None:
            usa_variacoes = bool(getattr(produto, "usa_variacoes", False))

        has_images = False
        has_valid_variations = False
        reason = ""

        if image_formset is not None and image_formset.is_bound:
            for form in image_formset.forms:
                if not hasattr(form, "cleaned_data"):
                    continue
                if form.cleaned_data.get("DELETE"):
                    continue
                imagem = form.cleaned_data.get("imagem") or getattr(form.instance, "imagem", None)
                if imagem:
                    has_images = True
                    break
        else:
            has_images = bool(produto and produto.pk and produto.imagens.exists())

        if usa_variacoes:
            if variation_formset is not None and variation_formset.is_bound:
                for form in variation_formset.forms:
                    if not hasattr(form, "cleaned_data"):
                        continue
                    if form.cleaned_data.get("DELETE"):
                        continue
                    ativo = bool(form.cleaned_data.get("ativo"))
                    quantidade = int(form.cleaned_data.get("quantidade") or 0)
                    if ativo and quantidade > 0:
                        has_valid_variations = True
                        break
            else:
                has_valid_variations = bool(
                    produto and produto.pk and produto.tem_variacoes_ativas_com_estoque
                )
        else:
            has_valid_variations = True

        can_publish = True
        if not has_images:
            can_publish = False
            reason = "Adicione ao menos uma imagem."
        elif usa_variacoes and not has_valid_variations:
            can_publish = False
            reason = "Cadastre ao menos uma variação ativa com estoque."
        elif (not usa_variacoes) and int(getattr(produto, "quantidade", 0) or 0) <= 0:
            can_publish = False
            reason = "Informe quantidade maior que zero."

        return {
            "has_images": has_images,
            "has_valid_variations": has_valid_variations,
            "can_publish": can_publish,
            "reason": reason,
        }

    def get_context_data_custom(self, form, image_formset, variation_formset, object_=None, posted_usa_variacoes=None):
        produto_ref = object_ or getattr(form, "instance", None)
        status_cards = self.build_status_cards(
            produto=produto_ref,
            image_formset=image_formset,
            variation_formset=variation_formset,
            posted_usa_variacoes=posted_usa_variacoes,
        )
        return {
            "form": form,
            "image_formset": image_formset,
            "variation_formset": variation_formset,
            "object": object_,
            "status_cards": status_cards,
        }

    def get_requested_action(self):
        return self.request.POST.get("action", "draft")

    def bind_form_with_action(self, instance):
        data = self.request.POST.copy()
        action = data.get("action", "draft")

        # publicação é decidida pelo botão, não por checkbox confuso
        if action == "publish":
            data["ativo"] = "on"
        else:
            data["ativo"] = ""

        form = self.form_class(data, self.request.FILES, instance=instance)
        formsets = self.get_formsets(
            data=data,
            files=self.request.FILES,
            instance=instance,
        )
        return form, formsets, action

    def save_everything(self, form, image_formset, variation_formset, action):
        with transaction.atomic():
            produto = form.save(commit=False)

            # salva sempre primeiro como rascunho
            produto.ativo = False

            if produto.usa_variacoes:
                produto.quantidade = 0

            produto.save()

            image_formset.instance = produto
            variation_formset.instance = produto

            image_formset.save()
            variation_formset.save()

            produto.refresh_from_db()

            if action == "publish":
                ok, reason = produto.pode_ativar()
                if ok:
                    produto.ativo = True
                    produto.save(update_fields=["ativo"])
                    messages.success(self.request, "Produto salvo e publicado com sucesso.")
                else:
                    produto.ativo = False
                    produto.save(update_fields=["ativo"])
                    messages.warning(
                        self.request,
                        f"Produto salvo como rascunho. Motivo: {reason}"
                    )
            else:
                messages.success(self.request, "Produto salvo como rascunho.")

        return produto

    def redirect_after_save(self, produto, action):
        if action == "new":
            return redirect("dashboard_produto_create_rapido")
        return redirect("dashboard_produto_update_rapido", pk=produto.pk)


class ProdutoRapidoCreateView(ProdutoRapidoBaseView, CreateView):
    def get(self, request, *args, **kwargs):
        temp_produto = Produto(usa_variacoes=False, quantidade=0, ativo=False)
        form = self.form_class(instance=temp_produto)
        formsets = self.get_formsets(instance=temp_produto)

        context = self.get_context_data_custom(
            form=form,
            image_formset=formsets["image_formset"],
            variation_formset=formsets["variation_formset"],
            object_=None,
            posted_usa_variacoes=False,
        )
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temp_produto = Produto()
        form, formsets, action = self.bind_form_with_action(temp_produto)
        image_formset = formsets["image_formset"]
        variation_formset = formsets["variation_formset"]

        valid = form.is_valid() and image_formset.is_valid() and variation_formset.is_valid()
        if not valid:
            context = self.get_context_data_custom(
                form=form,
                image_formset=image_formset,
                variation_formset=variation_formset,
                object_=None,
                posted_usa_variacoes=bool(request.POST.get("usa_variacoes")),
            )
            messages.error(request, "Corrija os erros do formulário.")
            return render(request, self.template_name, context)

        produto = self.save_everything(form, image_formset, variation_formset, action)
        return self.redirect_after_save(produto, action)


class ProdutoRapidoUpdateView(ProdutoRapidoBaseView, UpdateView):
    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        form = self.form_class(instance=obj)
        formsets = self.get_formsets(instance=obj)

        context = self.get_context_data_custom(
            form=form,
            image_formset=formsets["image_formset"],
            variation_formset=formsets["variation_formset"],
            object_=obj,
            posted_usa_variacoes=obj.usa_variacoes,
        )
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        form, formsets, action = self.bind_form_with_action(obj)
        image_formset = formsets["image_formset"]
        variation_formset = formsets["variation_formset"]

        valid = form.is_valid() and image_formset.is_valid() and variation_formset.is_valid()
        if not valid:
            context = self.get_context_data_custom(
                form=form,
                image_formset=image_formset,
                variation_formset=variation_formset,
                object_=obj,
                posted_usa_variacoes=bool(request.POST.get("usa_variacoes")),
            )
            messages.error(request, "Corrija os erros do formulário.")
            return render(request, self.template_name, context)

        produto = self.save_everything(form, image_formset, variation_formset, action)
        return self.redirect_after_save(produto, action)