from django.shortcuts import render


def painel_controle(request):

    return render(
        request,
        "dashboard/dashboard.html"
    )