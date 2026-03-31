from datetime import datetime
from decimal import Decimal
from io import BytesIO
from urllib.parse import quote

import qrcode
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (Count, DecimalField, ExpressionWrapper, F, Sum,
                              Value)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from website.models import (Carrinho, FormaPagamento, NivelAvaria, Produto,
                            ProdutoImagem, RegraParcelamentoVale, Tipo,
                            Unidade, Venda, VendaItem)

from .forms import (FormaPagamentoForm, NivelAvariaForm, ProdutoForm,
                    ProdutoImagemForm, ProdutoImagemFormSet,
                    RegraParcelamentoValeForm, TipoForm, UnidadeForm,
                    VendaStatusForm)
from .mixins import DashboardPermissionMixin
from .utils import enviar_email_status_venda_cliente


class PainelControleView(DashboardPermissionMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pedidos = Venda.objects.all()
        vendas_pendentes_qs = pedidos.filter(status=Venda.Status.PENDENTE)
        vendas_aprovadas_qs = pedidos.filter(status=Venda.Status.APROVADA)
        vendas_canceladas_qs = pedidos.filter(status=Venda.Status.CANCELADA)

        context["total_produtos"] = Produto.objects.count()
        context["total_pedidos"] = pedidos.count()
        context["vendas_pendentes"] = vendas_pendentes_qs.count()
        context["vendas_aprovadas"] = vendas_aprovadas_qs.count()
        context["vendas_canceladas"] = vendas_canceladas_qs.count()
        context["carrinhos_fechados"] = Carrinho.objects.filter(status=Carrinho.Status.FECHADO).count()

        context["valor_total_geral"] = (
            pedidos.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        )

        context["valor_total_aprovado"] = (
            vendas_aprovadas_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        )

        context["valor_total_pendente"] = (
            vendas_pendentes_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        )

        context["valor_total_cancelado"] = (
            vendas_canceladas_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        )

        valor_mercadoria = Produto.objects.aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("quantidade") * F("valor_venda"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Decimal("0.00"),
            )
        )["total"]

        context["valor_total_mercadoria"] = valor_mercadoria or Decimal("0.00")

        context["produtos_sem_estoque"] = Produto.objects.filter(quantidade=0).count()
        context["produtos_com_estoque"] = Produto.objects.filter(quantidade__gt=0).count()

        context["ultimas_vendas"] = (
            pedidos.select_related("usuario", "forma_pagamento")
            .order_by("-criado_em")[:5]
        )

        return context


class DashboardBaseListView(DashboardPermissionMixin, ListView):
    template_name = "dashboard/crud/list.html"
    context_object_name = "items"
    paginate_by = 20
    ordering = ["nome"]

    page_title = ""
    page_subtitle = ""
    create_url_name = ""
    empty_message = "Nenhum item cadastrado."

    columns = []  # ex: [{"label": "Nome", "field": "nome"}]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["page_subtitle"] = self.page_subtitle
        context["create_url_name"] = self.create_url_name
        context["empty_message"] = self.empty_message
        context["columns"] = self.columns
        return context


class DashboardBaseFormViewMixin(DashboardPermissionMixin):
    template_name = "dashboard/crud/form.html"
    page_title_create = ""
    page_title_update = ""
    page_subtitle = ""
    cancel_url_name = ""
    success_message = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = (
            self.page_title_update if getattr(self, "object", None) else self.page_title_create
        )
        context["page_subtitle"] = self.page_subtitle
        context["cancel_url_name"] = self.cancel_url_name
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


class DashboardBaseCreateView(DashboardBaseFormViewMixin, CreateView):
    pass


class DashboardBaseUpdateView(DashboardBaseFormViewMixin, UpdateView):
    pass


class DashboardBaseDeleteView(DashboardPermissionMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"
    success_message = ""

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


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


class ProdutoManageView(DashboardPermissionMixin, TemplateView):
    template_name = "dashboard/produtos/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = None
        pk = kwargs.get("pk")
        if pk:
            self.object = Produto.objects.filter(pk=pk).first()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, data=None, files=None):
        return ProdutoForm(data=data, files=files, instance=self.object)

    def get_formset(self, data=None, files=None):
        if not self.object:
            return ProdutoImagemFormSet(prefix="imagens")
        return ProdutoImagemFormSet(
            data=data,
            files=files,
            instance=self.object,
            prefix="imagens",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
        context["form"] = kwargs.get("form") or self.get_form()
        context["formset"] = kwargs.get("formset") or self.get_formset()
        context["open_images_modal"] = kwargs.get("open_images_modal", False)
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        form_type = request.POST.get("form_type", "produto")

        # Cadastro novo: só salva dados do produto
        if not self.object:
            form = self.get_form(data=request.POST, files=request.FILES)

            if form.is_valid():
                self.object = form.save()
                messages.success(request, "Produto cadastrado com sucesso.")
                return redirect("dashboard_produto_update", pk=self.object.pk)

            return self.render_to_response(
                self.get_context_data(form=form, formset=self.get_formset())
            )

        # Edição: submit separado por tipo
        if form_type == "imagens":
            return self.handle_images_form(request)

        return self.handle_product_form(request)

    def handle_product_form(self, request):
        form = self.get_form(data=request.POST, files=request.FILES)
        formset = self.get_formset()

        if form.is_valid():
            self.object = form.save()

            # Segurança extra: se ficou sem imagens, não deixa ativo
            if self.object.ativo and not self.object.imagens.exists():
                self.object.ativo = False
                self.object.save(update_fields=["ativo"])

            messages.success(request, "Dados do produto salvos com sucesso.")
            return redirect("dashboard_produto_update", pk=self.object.pk)

        messages.error(request, "Corrija os erros no formulário do produto.")
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )

    def handle_images_form(self, request):
        form = self.get_form()
        formset = self.get_formset(data=request.POST, files=request.FILES)

        if formset.is_valid():
            with transaction.atomic():
                formset.save()

                principais = [
                    f for f in formset.forms
                    if getattr(f, "cleaned_data", None)
                    and not f.cleaned_data.get("DELETE", False)
                    and f.cleaned_data.get("principal")
                ]

                if len(principais) == 1:
                    imagem_principal = principais[0].instance
                    self.object.imagens.exclude(pk=imagem_principal.pk).update(principal=False)

                # Se não houver nenhuma imagem restante, força produto inativo
                if not self.object.imagens.exists() and self.object.ativo:
                    self.object.ativo = False
                    self.object.save(update_fields=["ativo"])

            messages.success(request, "Imagens salvas com sucesso.")
            return redirect("dashboard_produto_update", pk=self.object.pk)

        messages.error(request, "Corrija os erros no formulário de imagens.")
        return self.render_to_response(
            self.get_context_data(
                form=form,
                formset=formset,
                open_images_modal=True,
            )
        )


class ProdutoDeleteView(DeleteView):
    model = Produto
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard_produto_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        possui_venda = self.object.itens_venda.exists()
        possui_carrinho = self.object.itens_carrinho.exists()

        if possui_venda or possui_carrinho:
            self.object.ativo = False
            self.object.save(update_fields=["ativo"])
            messages.warning(
                request,
                "O produto já está vinculado a registros e não pode ser excluído. "
                "Ele foi apenas desativado."
            )
        else:
            self.object.delete()
            messages.success(request, "Produto excluído com sucesso.")

        return redirect(self.success_url)


@xframe_options_exempt
def produto_qrcode_pdf(request, pk):
    produto = get_object_or_404(Produto, pk=pk)

    url_detalhe = request.build_absolute_uri(
        reverse("detalhe_produto", args=[produto.pk])
    )

    # Gera o QRCode em memória
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
    )
    qr.add_data(url_detalhe)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # PDF em memória
    pdf_buffer = BytesIO()

    # Tamanho da etiqueta / página
    page_width = 80 * mm
    page_height = 100 * mm

    c = canvas.Canvas(pdf_buffer, pagesize=(page_width, page_height))
    c.setTitle(f"QR Code - {produto.nome}")
    margem = 8 * mm
    y_top = page_height - margem

    # Título / nome do produto
    nome = produto.nome or "Produto"
    fonte_nome = "Helvetica-Bold"
    tamanho_nome = 11

    max_text_width = page_width - (2 * margem)

    # quebra simples em até 2 linhas
    palavras = nome.split()
    linhas = []
    linha_atual = ""

    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        if stringWidth(teste, fonte_nome, tamanho_nome) <= max_text_width:
            linha_atual = teste
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra

    if linha_atual:
        linhas.append(linha_atual)

    linhas = linhas[:2]
    if len(linhas) == 2 and len(palavras) > 0:
        # se sobrou conteúdo, corta discretamente
        while stringWidth(linhas[-1] + "...", fonte_nome, tamanho_nome) > max_text_width and len(linhas[-1]) > 1:
            linhas[-1] = linhas[-1][:-1]
        if len(" ".join(palavras)) > len(" ".join(linhas)):
            linhas[-1] += "..."

    c.setFont(fonte_nome, tamanho_nome)
    y = y_top

    for linha in linhas:
        text_width = stringWidth(linha, fonte_nome, tamanho_nome)
        x = (page_width - text_width) / 2
        c.drawString(x, y, linha)
        y -= 5.5 * mm

    y -= 2 * mm

    # QR centralizado
    qr_size = 48 * mm
    qr_x = (page_width - qr_size) / 2
    qr_y = y - qr_size

    c.drawImage(
        ImageReader(qr_buffer),
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask='auto',
    )

    # legenda pequena
    legenda = "Escaneie para ver detalhes"
    c.setFont("Helvetica", 8)
    legenda_width = stringWidth(legenda, "Helvetica", 8)
    c.drawString((page_width - legenda_width) / 2, qr_y - 6 * mm, legenda)

    c.showPage()
    c.save()

    pdf_buffer.seek(0)

    filename = f"qrcode-produto-{produto.pk}.pdf"
    safe_filename = quote(filename)

    response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{safe_filename}"'
    return response


# -------------------------
# TIPOS
# -------------------------
class TipoListView(DashboardBaseListView):
    model = Tipo
    ordering = ["nome"]
    page_title = "Tipos"
    page_subtitle = "Gerencie os tipos cadastrados."
    create_url_name = "dashboard_tipo_create"
    empty_message = "Nenhum tipo cadastrado."
    columns = [
        {"label": "Nome", "field": "nome"},
    ]


class TipoCreateView(DashboardBaseCreateView):
    model = Tipo
    form_class = TipoForm
    success_url = reverse_lazy("dashboard_tipo_list")
    page_title_create = "Novo tipo"
    page_title_update = "Editar tipo"
    page_subtitle = "Preencha os dados do tipo."
    cancel_url_name = "dashboard_tipo_list"
    success_message = "Tipo cadastrado com sucesso."


class TipoUpdateView(DashboardBaseUpdateView):
    model = Tipo
    form_class = TipoForm
    success_url = reverse_lazy("dashboard_tipo_list")
    page_title_create = "Novo tipo"
    page_title_update = "Editar tipo"
    page_subtitle = "Preencha os dados do tipo."
    cancel_url_name = "dashboard_tipo_list"
    success_message = "Tipo atualizado com sucesso."


class TipoDeleteView(DashboardBaseDeleteView):
    model = Tipo
    success_url = reverse_lazy("dashboard_tipo_list")
    success_message = "Tipo excluído com sucesso."

# -------------------------
# UNIDADES
# -------------------------
class UnidadeListView(DashboardBaseListView):
    model = Unidade
    ordering = ["nome"]
    page_title = "Unidades"
    page_subtitle = "Gerencie as unidades cadastradas."
    create_url_name = "dashboard_unidade_create"
    empty_message = "Nenhuma unidade cadastrada."
    columns = [
        {"label": "Nome", "field": "nome"},
    ]


class UnidadeCreateView(DashboardBaseCreateView):
    model = Unidade
    form_class = UnidadeForm
    success_url = reverse_lazy("dashboard_unidade_list")
    page_title_create = "Nova unidade"
    page_title_update = "Editar unidade"
    page_subtitle = "Preencha os dados da unidade."
    cancel_url_name = "dashboard_unidade_list"
    success_message = "Unidade cadastrada com sucesso."


class UnidadeUpdateView(DashboardBaseUpdateView):
    model = Unidade
    form_class = UnidadeForm
    success_url = reverse_lazy("dashboard_unidade_list")
    page_title_create = "Nova unidade"
    page_title_update = "Editar unidade"
    page_subtitle = "Preencha os dados da unidade."
    cancel_url_name = "dashboard_unidade_list"
    success_message = "Unidade atualizada com sucesso."


class UnidadeDeleteView(DashboardBaseDeleteView):
    model = Unidade
    success_url = reverse_lazy("dashboard_unidade_list")
    success_message = "Unidade excluída com sucesso."


# -------------------------
# NÍVEIS DE AVARIA
# -------------------------
class NivelAvariaListView(DashboardBaseListView):
    model = NivelAvaria
    ordering = ["nome"]
    page_title = "Níveis de avaria"
    page_subtitle = "Gerencie os níveis de avaria cadastrados."
    create_url_name = "dashboard_nivel_avaria_create"
    empty_message = "Nenhum nível de avaria cadastrado."
    columns = [
        {"label": "Nome", "field": "nome"},
    ]


class NivelAvariaCreateView(DashboardBaseCreateView):
    model = NivelAvaria
    form_class = NivelAvariaForm
    success_url = reverse_lazy("dashboard_nivel_avaria_list")
    page_title_create = "Novo nível de avaria"
    page_title_update = "Editar nível de avaria"
    page_subtitle = "Preencha os dados do nível de avaria."
    cancel_url_name = "dashboard_nivel_avaria_list"
    success_message = "Nível de avaria cadastrado com sucesso."


class NivelAvariaUpdateView(DashboardBaseUpdateView):
    model = NivelAvaria
    form_class = NivelAvariaForm
    success_url = reverse_lazy("dashboard_nivel_avaria_list")
    page_title_create = "Novo nível de avaria"
    page_title_update = "Editar nível de avaria"
    page_subtitle = "Preencha os dados do nível de avaria."
    cancel_url_name = "dashboard_nivel_avaria_list"
    success_message = "Nível de avaria atualizado com sucesso."


class NivelAvariaDeleteView(DashboardBaseDeleteView):
    model = NivelAvaria
    success_url = reverse_lazy("dashboard_nivel_avaria_list")
    success_message = "Nível de avaria excluído com sucesso."



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
        mes = self.request.GET.get("mes")
        ano = self.request.GET.get("ano")

        if status:
            queryset = queryset.filter(status=status)

        if mes:
            queryset = queryset.filter(criado_em__month=mes)

        if ano:
            queryset = queryset.filter(criado_em__year=ano)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ano_atual = timezone.now().year
        context["status_atual"] = self.request.GET.get("status", "")
        context["mes_atual"] = self.request.GET.get("mes", "")
        context["ano_atual"] = self.request.GET.get("ano", "")
        context["status_choices"] = Venda._meta.get_field("status").choices
        context["meses"] = [
            (1, "Janeiro"),
            (2, "Fevereiro"),
            (3, "Março"),
            (4, "Abril"),
            (5, "Maio"),
            (6, "Junho"),
            (7, "Julho"),
            (8, "Agosto"),
            (9, "Setembro"),
            (10, "Outubro"),
            (11, "Novembro"),
            (12, "Dezembro"),
        ]
        context["anos"] = range(ano_atual - 1, ano_atual + 1)
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

        comprovante = None
        if self.object.forma_pagamento and self.object.forma_pagamento.codigo == "PIX":
            comprovante = self.object.comprovante_pix
        elif self.object.forma_pagamento and self.object.forma_pagamento.codigo == "VALE":
            comprovante = self.object.comprovante_vale

        comprovante_url = comprovante.url if comprovante else ""
        comprovante_nome = str(comprovante).lower() if comprovante else ""

        context["comprovante"] = comprovante
        context["comprovante_url"] = comprovante_url
        context["comprovante_is_pdf"] = comprovante_nome.endswith(".pdf")
        context["comprovante_is_image"] = comprovante_nome.endswith((".png", ".jpg", ".jpeg", ".webp"))
        return context


class VendaUpdateStatusView(DashboardPermissionMixin, UpdateView):
    model = Venda
    form_class = VendaStatusForm
    template_name = "dashboard/vendas/detail.html"
    context_object_name = "venda"

    def get_success_url(self):
        return reverse_lazy("dashboard_venda_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        status_anterior = Venda.objects.get(pk=form.instance.pk).status

        self.object = form.save()
        novo_status = self.object.status

        if (
            status_anterior != novo_status
            and novo_status in [Venda.Status.APROVADA, Venda.Status.CANCELADA, Venda.Status.CONCLUIDA]
        ):
            transaction.on_commit(
                lambda: enviar_email_status_venda_cliente(self.object)
            )

        messages.success(self.request, "Status da venda atualizado com sucesso.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível atualizar a venda. Verifique os campos abaixo.")
        return self.render_to_response(self.get_context_data(form=form))
    

class VendaExportXlsxView(DashboardPermissionMixin, View):
    def get_queryset(self):
        queryset = (
            Venda.objects
            .select_related("usuario", "forma_pagamento")
            .prefetch_related("itens__produto")
            .order_by("-criado_em")
        )

        status = self.request.GET.get("status")
        mes = self.request.GET.get("mes")
        ano = self.request.GET.get("ano")

        if status:
            queryset = queryset.filter(status=status)

        if mes:
            queryset = queryset.filter(criado_em__month=mes)

        if ano:
            queryset = queryset.filter(criado_em__year=ano)

        return queryset

    def get(self, request, *args, **kwargs):
        vendas = self.get_queryset()

        wb = Workbook()
        ws = wb.active
        ws.title = "Vendas"

        headers = [
            "ID Venda",
            "Data",
            "Comprador",
            "CPF",
            "E-mail",
            "Forma de Pagamento",
            "Parcelas",
            "Status",
            "Valor Total",
            "Observação",
            "Itens",
        ]

        ws.append(headers)

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for venda in vendas:
            usuario = venda.usuario

            # Ajuste aqui conforme o nome real do campo no seu model de usuário
            cpf = getattr(usuario, "cpf", "") or getattr(usuario, "username", "")

            itens_str = ", ".join([
                f"{item.produto.nome} (qtd: {item.quantidade}, unit: R$ {item.preco_unitario}, subtotal: R$ {item.subtotal})"
                for item in venda.itens.all()
            ])

            ws.append([
                venda.id,
                venda.criado_em.strftime("%d/%m/%Y %H:%M"),
                str(usuario),
                cpf,
                getattr(usuario, "email", ""),
                str(venda.forma_pagamento),
                venda.parcelas,
                venda.get_status_display(),
                float(venda.total or Decimal("0.00")),
                venda.observacao or "",
                itens_str,
            ])

        # Largura das colunas
        widths = {
            "A": 12,
            "B": 20,
            "C": 30,
            "D": 20,
            "E": 30,
            "F": 20,
            "G": 12,
            "H": 15,
            "I": 15,
            "J": 40,
            "K": 80,
        }
        for col, width in widths.items():
            ws.column_dimensions[col].width = width

        # Formata coluna de valor
        for row in range(2, ws.max_row + 1):
            ws[f"I{row}"].number_format = 'R$ #,##0.00'

        mes = request.GET.get("mes") or "todos"
        ano = request.GET.get("ano") or "todos"
        filename = f"vendas_{mes}_{ano}.xlsx"

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        wb.save(response)
        return response

# -------------------------
# IMAGENS DE PRODUTOS
# -------------------------

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
    
# -------------------------
# FORMAS DE PAGAMENTO
# -------------------------
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
    
# -------------------------
# REGRAS DE PARCELAMENTO DO VALE
# -------------------------
class RegraParcelamentoValeListView(DashboardBaseListView):
    model = RegraParcelamentoVale
    ordering = ["minimo"]
    page_title = "Regras de parcelamento"
    page_subtitle = "Gerencie as regras de parcelamento do vale."
    create_url_name = "dashboard_regra_vale_create"
    empty_message = "Nenhuma regra cadastrada."
    columns = [
        {"label": "Mínimo", "field": "minimo"},
        {"label": "Máximo", "field": "maximo"},
        {"label": "Parcelas", "field": "max_parcelas"},
    ]


class RegraParcelamentoValeCreateView(DashboardBaseCreateView):
    model = RegraParcelamentoVale
    form_class = RegraParcelamentoValeForm
    success_url = reverse_lazy("dashboard_regra_vale_list")
    page_title_create = "Nova regra de parcelamento"
    page_title_update = "Editar regra de parcelamento"
    page_subtitle = "Preencha os dados da regra."
    cancel_url_name = "dashboard_regra_vale_list"
    success_message = "Regra de parcelamento cadastrada com sucesso."


class RegraParcelamentoValeUpdateView(DashboardBaseUpdateView):
    model = RegraParcelamentoVale
    form_class = RegraParcelamentoValeForm
    success_url = reverse_lazy("dashboard_regra_vale_list")
    page_title_create = "Nova regra de parcelamento"
    page_title_update = "Editar regra de parcelamento"
    page_subtitle = "Preencha os dados da regra."
    cancel_url_name = "dashboard_regra_vale_list"
    success_message = "Regra de parcelamento atualizada com sucesso."


class RegraParcelamentoValeDeleteView(DashboardBaseDeleteView):
    model = RegraParcelamentoVale
    success_url = reverse_lazy("dashboard_regra_vale_list")
    success_message = "Regra de parcelamento excluída com sucesso."