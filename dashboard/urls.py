from django.urls import path

from .views import (FormaPagamentoCreateView, FormaPagamentoDeleteView,
                    FormaPagamentoListView, FormaPagamentoUpdateView,
                    NivelAvariaCreateView, NivelAvariaDeleteView,
                    NivelAvariaListView, NivelAvariaUpdateView,
                    PainelControleView, ProdutoDeleteView, ProdutoListView,
                    ProdutoManageView, RegraParcelamentoValeCreateView,
                    RegraParcelamentoValeDeleteView,
                    RegraParcelamentoValeListView,
                    RegraParcelamentoValeUpdateView, TipoCreateView,
                    TipoDeleteView, TipoListView, TipoUpdateView,
                    UnidadeCreateView, UnidadeDeleteView, UnidadeListView,
                    UnidadeUpdateView, VendaDetailView, VendaExportXlsxView,
                    VendaListView, VendaUpdateStatusView, produto_qrcode_pdf)

urlpatterns = [
    path("painel-controle/", PainelControleView.as_view(), name="painel_controle"),

    path("painel-controle/produtos/", ProdutoListView.as_view(), name="dashboard_produto_list"),
    path("painel-controle/produtos/novo/", ProdutoManageView.as_view(), name="dashboard_produto_create"),
    path("painel-controle/produtos/<int:pk>/editar/", ProdutoManageView.as_view(), name="dashboard_produto_update"),
    path("painel-controle/produtos/<int:pk>/excluir/", ProdutoDeleteView.as_view(), name="dashboard_produto_delete"),


    path(
        "dashboard/produtos/<int:pk>/qrcode/pdf/",
        produto_qrcode_pdf,
        name="dashboard_produto_qrcode_pdf",
    ),

    path("painel-controle/tipos/", TipoListView.as_view(), name="dashboard_tipo_list"),
    path("painel-controle/tipos/novo/", TipoCreateView.as_view(), name="dashboard_tipo_create"),
    path("painel-controle/tipos/<int:pk>/editar/", TipoUpdateView.as_view(), name="dashboard_tipo_update"),
    path("painel-controle/tipos/<int:pk>/excluir/", TipoDeleteView.as_view(), name="dashboard_tipo_delete"),

    path("painel-controle/unidades/", UnidadeListView.as_view(), name="dashboard_unidade_list"),
    path("painel-controle/unidades/nova/", UnidadeCreateView.as_view(), name="dashboard_unidade_create"),
    path("painel-controle/unidades/<int:pk>/editar/", UnidadeUpdateView.as_view(), name="dashboard_unidade_update"),
    path("painel-controle/unidades/<int:pk>/excluir/", UnidadeDeleteView.as_view(), name="dashboard_unidade_delete"),

    path("painel-controle/niveis-avaria/", NivelAvariaListView.as_view(), name="dashboard_nivel_avaria_list"),
    path("painel-controle/niveis-avaria/novo/", NivelAvariaCreateView.as_view(), name="dashboard_nivel_avaria_create"),
    path("painel-controle/niveis-avaria/<int:pk>/editar/", NivelAvariaUpdateView.as_view(), name="dashboard_nivel_avaria_update"),
    path("painel-controle/niveis-avaria/<int:pk>/excluir/", NivelAvariaDeleteView.as_view(), name="dashboard_nivel_avaria_delete"),

    path("painel-controle/vendas/", VendaListView.as_view(), name="dashboard_venda_list"),
    path("painel-controle/vendas/<int:pk>/", VendaDetailView.as_view(), name="dashboard_venda_detail"),
    path("painel-controle/vendas/<int:pk>/status/", VendaUpdateStatusView.as_view(), name="dashboard_venda_update_status"),
    path("painel-controle/vendas/exportar/", VendaExportXlsxView.as_view(), name="dashboard_venda_export_xlsx"),

    path("painel-controle/formas-pagamento/", FormaPagamentoListView.as_view(), name="dashboard_forma_pagamento_list"),
    path("painel-controle/formas-pagamento/nova/", FormaPagamentoCreateView.as_view(), name="dashboard_forma_pagamento_create"),
    path("painel-controle/formas-pagamento/<int:pk>/editar/", FormaPagamentoUpdateView.as_view(), name="dashboard_forma_pagamento_update"),
    path("painel-controle/formas-pagamento/<int:pk>/excluir/", FormaPagamentoDeleteView.as_view(), name="dashboard_forma_pagamento_delete"),

    path("painel-controle/regras-vale/", RegraParcelamentoValeListView.as_view(), name="dashboard_regra_vale_list"),
    path("painel-controle/regras-vale/nova/", RegraParcelamentoValeCreateView.as_view(), name="dashboard_regra_vale_create"),
    path("painel-controle/regras-vale/<int:pk>/editar/", RegraParcelamentoValeUpdateView.as_view(), name="dashboard_regra_vale_update"),
    path("painel-controle/regras-vale/<int:pk>/excluir/", RegraParcelamentoValeDeleteView.as_view(), name="dashboard_regra_vale_delete"),
]