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
            for erro in form.non_field_errors():
                messages.error(request, erro)

            for campo, erros in form.errors.items():
                if campo != "__all__":
                    for erro in erros:
                        messages.error(request, f"{campo}: {erro}")
    else:
        form = CadastroForm()

    return render(request, "accounts/cadastrar.html", {"form": form})
