# accounts/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import CadastroForm


def cadastrar(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect("index")
    else:
        form = CadastroForm()

    return render(request, "accounts/cadastrar.html", {"form": form})
