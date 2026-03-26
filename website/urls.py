from django.urls import path

from . import views, views_carrinho, views_checkout

urlpatterns = [

    # -------------------------
    # Home / produtos
    # -------------------------
    path("", views.index, name="index"),
    path("produto/<int:pk>/", views.detalhe_produto, name="detalhe_produto"),


    # -------------------------
    # Carrinho
    # -------------------------
    path("carrinho/", views_carrinho.carrinho_detail, name="carrinho_detail"),
    path("carrinho/add/<int:pk>/", views_carrinho.carrinho_add, name="carrinho_add"),
    path("carrinho/update/<int:item_id>/", views_carrinho.carrinho_update, name="carrinho_update"),
    path("carrinho/remove/<int:item_id>/", views_carrinho.carrinho_remove, name="carrinho_remove"),


    # -------------------------
    # Checkout
    # -------------------------
    path("checkout/", views_checkout.checkout, name="checkout"),


    # -------------------------
    # Pix
    # -------------------------
    path("pix/<int:pk>/", views_checkout.pix_pagar, name="pix_pagar"),
    path(
        "pix/<int:pk>/comprovante/",
        views_checkout.enviar_comprovante_pix,
        name="enviar_comprovante_pix",
    ),


    # -------------------------
    # Compras
    # -------------------------
    path("compras/", views_checkout.minhas_compras, name="minhas_compras"),

    path(
        "pedido/<int:pk>/",
        views_checkout.venda_detalhe,
        name="venda_detalhe",
    ),
    path("pedido/<int:pk>/rastrear-json/", views_checkout.rastrear_encomenda_json, name="rastrear_encomenda_json"),


    # -------------------------
    # Favoritos
    # -------------------------
    path(
        "favoritar/<int:produto_id>/",
        views.favorito_toggle,
        name="favorito_toggle"
    ),

    path(
        "favoritos/",
        views.meus_favoritos,
        name="meus_favoritos"
    ),
]