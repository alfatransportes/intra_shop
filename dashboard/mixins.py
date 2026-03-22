from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class DashboardPermissionMixin(LoginRequiredMixin):
    login_url = "login"

    def dispatch(self, request, *args, **kwargs):
        # Ajuste esta regra conforme seu model de usuário
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Exemplo:
        # se tiver campo is_staff, use ele
        if not getattr(request.user, "is_staff", True):
            raise PermissionDenied("Você não tem permissão para acessar o painel.")

        return super().dispatch(request, *args, **kwargs)