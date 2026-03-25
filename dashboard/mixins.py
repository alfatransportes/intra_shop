from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class DashboardPermissionMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_staff:
            raise PermissionDenied("Apenas administradores podem acessar o painel.")

        return super().dispatch(request, *args, **kwargs)