from django.urls import path

from . import views

urlpatterns = [

    # -------------------------
    # Home / produtos
    # -------------------------
    path("painel-controle/", views.painel_controle, name="painel_controle"),
]