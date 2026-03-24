from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)

from website.models import (Carrinho, FormaPagamento, NivelAvaria, Produto,
                            ProdutoImagem, RegraParcelamentoVale, Tipo,
                            Unidade, Venda)

from .forms import (FormaPagamentoForm, NivelAvariaForm, ProdutoForm,
                    ProdutoImagemForm, RegraParcelamentoValeForm, TipoForm,
                    UnidadeForm, VendaStatusForm)
from .mixins import DashboardPermissionMixin


class PainelControleView(DashboardPermissionMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_produtos"] = Produto.objects.count()
        context["total_vendas"] = Venda.objects.count()
        context["vendas_pendentes"] = Venda.objects.filter(status="PENDENTE").count()
        context["vendas_aprovadas"] = Venda.objects.filter(status="APROVADA").count()
        context["vendas_canceladas"] = Venda.objects.filter(status="CANCELADA").count()
        context["carrinhos_abertos"] = Carrinho.objects.filter(status="ABERTO").count()
        context["valor_total_vendido"] = (
            Venda.objects.filter(status="APROVADA").aggregate(total=Sum("total"))["total"]
            or Decimal("0.00")
        )
        return context


# -------------------------
# PRODUTOS
# -------------------------
class ProdutoListView(DashboardPermissionMixin, ListView):
    model = Produto
    template_name = "dashboard/produtos/list.html"
    context_object_name = "produtos"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Produto.objects
            .select_related("unidade_prod", "tipo_prod", "nivel_ava_prod")
            .prefetch_related("imagens")
            .order_by("nome")
        )

        busca = self.request.GET.get("q")
        tipo = self.request.GET.get("tipo")

        if busca:
            queryset = queryset.filter(nome__icontains=busca)

        if tipo:
            queryset = queryset.filter(tipo_prod_id=tipo)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipos"] = Tipo.objects.filter(ativo=True).order_by("nome")
        context["q"] = self.request.GET.get("q", "")
        context["tipo_atual"] = self.request.GET.get("tipo", "")
        return context


class ProdutoCreateView(DashboardPermissionMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = "dashboard/produtos/form.html"
    success_url = reverse_lazy("dashboard_produto_list")

    def form_valid(self, form):
        messages.success(self.request, "Produto cadastrado com sucesso.")
        return super().form_valid(form)


class ProdutoUpdateView(DashboardPermissionMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = "dashboard/produtos/form.html"
    success_url = reverse_lazy("dashboard_produto_list")

    def form_valid(self, form):
        messages.success(self.request, "Produto atualizado com sucesso.")
        return super().form_valid(form)


class ProdutoDeleteView(DashboardPermissionMixin, DeleteView):
    model = Produto
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_produto_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Produto excluído com sucesso.")
        return super().delete(request, *args, **kwargs)


# -------------------------
# TIPOS
# -------------------------
class TipoListView(DashboardPermissionMixin, ListView):
    model = Tipo
    template_name = "dashboard/tipos/list.html"
    context_object_name = "tipos"
    paginate_by = 20
    ordering = ["nome"]


class TipoCreateView(DashboardPermissionMixin, CreateView):
    model = Tipo
    form_class = TipoForm
    template_name = "dashboard/tipos/form.html"
    success_url = reverse_lazy("dashboard_tipo_list")

    def form_valid(self, form):
        messages.success(self.request, "Tipo cadastrado com sucesso.")
        return super().form_valid(form)


class TipoUpdateView(DashboardPermissionMixin, UpdateView):
    model = Tipo
    form_class = TipoForm
    template_name = "dashboard/tipos/form.html"
    success_url = reverse_lazy("dashboard_tipo_list")

    def form_valid(self, form):
        messages.success(self.request, "Tipo atualizado com sucesso.")
        return super().form_valid(form)


class TipoDeleteView(DashboardPermissionMixin, DeleteView):
    model = Tipo
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_tipo_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Tipo excluído com sucesso.")
        return super().delete(request, *args, **kwargs)


# -------------------------
# UNIDADES
# -------------------------
class UnidadeListView(DashboardPermissionMixin, ListView):
    model = Unidade
    template_name = "dashboard/unidades/list.html"
    context_object_name = "unidades"
    paginate_by = 20
    ordering = ["nome"]


class UnidadeCreateView(DashboardPermissionMixin, CreateView):
    model = Unidade
    form_class = UnidadeForm
    template_name = "dashboard/unidades/form.html"
    success_url = reverse_lazy("dashboard_unidade_list")

    def form_valid(self, form):
        messages.success(self.request, "Unidade cadastrada com sucesso.")
        return super().form_valid(form)


class UnidadeUpdateView(DashboardPermissionMixin, UpdateView):
    model = Unidade
    form_class = UnidadeForm
    template_name = "dashboard/unidades/form.html"
    success_url = reverse_lazy("dashboard_unidade_list")

    def form_valid(self, form):
        messages.success(self.request, "Unidade atualizada com sucesso.")
        return super().form_valid(form)


class UnidadeDeleteView(DashboardPermissionMixin, DeleteView):
    model = Unidade
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_unidade_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Unidade excluída com sucesso.")
        return super().delete(request, *args, **kwargs)


# -------------------------
# NÍVEIS DE AVARIA
# -------------------------
class NivelAvariaListView(DashboardPermissionMixin, ListView):
    model = NivelAvaria
    template_name = "dashboard/niveis-avaria/list.html"
    context_object_name = "niveis"
    paginate_by = 20
    ordering = ["nome"]


class NivelAvariaCreateView(DashboardPermissionMixin, CreateView):
    model = NivelAvaria
    form_class = NivelAvariaForm
    template_name = "dashboard/niveis-avaria/form.html"
    success_url = reverse_lazy("dashboard_nivel_avaria_list")

    def form_valid(self, form):
        messages.success(self.request, "Nível de avaria cadastrado com sucesso.")
        return super().form_valid(form)


class NivelAvariaUpdateView(DashboardPermissionMixin, UpdateView):
    model = NivelAvaria
    form_class = NivelAvariaForm
    template_name = "dashboard/niveis-avaria/form.html"
    success_url = reverse_lazy("dashboard_nivel_avaria_list")

    def form_valid(self, form):
        messages.success(self.request, "Nível de avaria atualizado com sucesso.")
        return super().form_valid(form)


class NivelAvariaDeleteView(DashboardPermissionMixin, DeleteView):
    model = NivelAvaria
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_nivel_avaria_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Nível de avaria excluído com sucesso.")
        return super().delete(request, *args, **kwargs)


# -------------------------
# VENDAS
# -------------------------
class VendaListView(DashboardPermissionMixin, ListView):
    model = Venda
    template_name = "dashboard/vendas/list.html"
    context_object_name = "vendas"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Venda.objects
            .select_related("usuario", "forma_pagamento")
            .prefetch_related("itens")
            .order_by("-criado_em")
        )

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_atual"] = self.request.GET.get("status", "")
        return context


class VendaDetailView(DashboardPermissionMixin, DetailView):
    model = Venda
    template_name = "dashboard/vendas/detail.html"
    context_object_name = "venda"

    def get_queryset(self):
        return (
            Venda.objects
            .select_related("usuario", "forma_pagamento")
            .prefetch_related("itens__produto")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = VendaStatusForm(instance=self.object)
        return context


class VendaUpdateStatusView(DashboardPermissionMixin, UpdateView):
    model = Venda
    form_class = VendaStatusForm
    template_name = "dashboard/vendas/detail.html"
    context_object_name = "venda"

    def get_success_url(self):
        return reverse_lazy("dashboard_venda_list")

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Status da venda atualizado com sucesso.")
        return redirect(self.get_success_url())
    

class ProdutoImagemListView(DashboardPermissionMixin, ListView):
    model = ProdutoImagem
    template_name = "dashboard/produto-imagens/list.html"
    context_object_name = "imagens"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            ProdutoImagem.objects
            .select_related("produto")
            .order_by("produto__nome", "ordem", "id")
        )

        produto_id = self.request.GET.get("produto")
        if produto_id:
            queryset = queryset.filter(produto_id=produto_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["produtos"] = Produto.objects.order_by("nome")
        context["produto_atual"] = self.request.GET.get("produto", "")

        produto_id = self.request.GET.get("produto")
        context["produto_selecionado"] = None
        if produto_id:
            context["produto_selecionado"] = Produto.objects.filter(pk=produto_id).first()

        return context

class ProdutoImagemCreateView(DashboardPermissionMixin, CreateView):
    model = ProdutoImagem
    form_class = ProdutoImagemForm
    template_name = "dashboard/produto-imagens/form.html"
    success_url = reverse_lazy("dashboard_produto_imagem_list")

    def get_initial(self):
        initial = super().get_initial()
        produto_id = self.request.GET.get("produto")
        if produto_id:
            initial["produto"] = produto_id
        return initial

    def get_success_url(self):
        if self.object and self.object.produto_id:
            return f"{reverse_lazy('dashboard_produto_imagem_list')}?produto={self.object.produto_id}"
        return reverse_lazy("dashboard_produto_imagem_list")

    def form_valid(self, form):
        messages.success(self.request, "Imagem cadastrada com sucesso.")
        return super().form_valid(form)


class ProdutoImagemUpdateView(DashboardPermissionMixin, UpdateView):
    model = ProdutoImagem
    form_class = ProdutoImagemForm
    template_name = "dashboard/produto-imagens/form.html"
    success_url = reverse_lazy("dashboard_produto_imagem_list")

    def form_valid(self, form):
        messages.success(self.request, "Imagem atualizada com sucesso.")
        return super().form_valid(form)


class ProdutoImagemDeleteView(DashboardPermissionMixin, DeleteView):
    model = ProdutoImagem
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_produto_imagem_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Imagem excluída com sucesso.")
        return super().delete(request, *args, **kwargs)
    

class FormaPagamentoListView(DashboardPermissionMixin, ListView):
    model = FormaPagamento
    template_name = "dashboard/formas-pagamento/list.html"
    context_object_name = "formas_pagamento"
    paginate_by = 20
    ordering = ["codigo"]


class FormaPagamentoCreateView(DashboardPermissionMixin, CreateView):
    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = "dashboard/formas-pagamento/form.html"
    success_url = reverse_lazy("dashboard_forma_pagamento_list")

    def form_valid(self, form):
        messages.success(self.request, "Forma de pagamento cadastrada com sucesso.")
        return super().form_valid(form)


class FormaPagamentoUpdateView(DashboardPermissionMixin, UpdateView):
    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = "dashboard/formas-pagamento/form.html"
    success_url = reverse_lazy("dashboard_forma_pagamento_list")

    def form_valid(self, form):
        messages.success(self.request, "Forma de pagamento atualizada com sucesso.")
        return super().form_valid(form)


class FormaPagamentoDeleteView(DashboardPermissionMixin, DeleteView):
    model = FormaPagamento
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_forma_pagamento_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.venda_set.exists():
            self.object.ativa = False
            self.object.save(update_fields=["ativa"])
            messages.warning(
                request,
                "Forma de pagamento já utilizada em vendas. Ela foi inativada em vez de excluída."
            )
        else:
            self.object.delete()
            messages.success(request, "Forma de pagamento excluída com sucesso.")

        return redirect(self.success_url)
    

class RegraParcelamentoValeListView(DashboardPermissionMixin, ListView):
    model = RegraParcelamentoVale
    template_name = "dashboard/regras-vale/list.html"
    context_object_name = "regras"
    paginate_by = 20
    ordering = ["minimo"]


class RegraParcelamentoValeCreateView(DashboardPermissionMixin, CreateView):
    model = RegraParcelamentoVale
    form_class = RegraParcelamentoValeForm
    template_name = "dashboard/regras-vale/form.html"
    success_url = reverse_lazy("dashboard_regra_vale_list")

    def form_valid(self, form):
        messages.success(self.request, "Regra de parcelamento cadastrada com sucesso.")
        return super().form_valid(form)


class RegraParcelamentoValeUpdateView(DashboardPermissionMixin, UpdateView):
    model = RegraParcelamentoVale
    form_class = RegraParcelamentoValeForm
    template_name = "dashboard/regras-vale/form.html"
    success_url = reverse_lazy("dashboard_regra_vale_list")

    def form_valid(self, form):
        messages.success(self.request, "Regra de parcelamento atualizada com sucesso.")
        return super().form_valid(form)


class RegraParcelamentoValeDeleteView(DashboardPermissionMixin, DeleteView):
    model = RegraParcelamentoVale
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_regra_vale_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Regra de parcelamento excluída com sucesso.")
        return super().delete(request, *args, **kwargs)