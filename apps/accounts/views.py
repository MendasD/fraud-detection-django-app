from django.contrib.auth import views as auth_views, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views import View
from .models import User


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ['first_name', 'last_name', 'email', 'phone', 'department', 'avatar', 'receive_alerts']
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('dashboard:index') # reverse_lazy permet de résoudre l'url plus tard, pas directement au chargement du fichier

    def get_object(self):
        return self.request.user
