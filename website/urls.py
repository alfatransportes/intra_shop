from django.urls import path

from . import views, views_carrinho, views_checkout

urlpatterns = [
    path("", views.index, name="index"),
    path("produto/<int:pk>/", views.detalhe_produto, name="detalhe_produto"),

    path("carrinho/", views_carrinho.carrinho_detail, name="carrinho_detail"),
    path("carrinho/add/<int:pk>/", views_carrinho.carrinho_add, name="carrinho_add"),
    path("carrinho/update/<int:item_id>/", views_carrinho.carrinho_update, name="carrinho_update"),
    path("carrinho/remove/<int:item_id>/", views_carrinho.carrinho_remove, name="carrinho_remove"),

    path("checkout/", views_checkout.checkout, name="checkout"),
    path("checkout/confirmar/<int:forma_id>/", views_checkout.checkout_confirmar, name="checkout_confirmar"),

    path("venda/<int:pk>/", views_checkout.venda_detalhe, name="venda_detalhe"),
]
