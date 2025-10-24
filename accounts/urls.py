from django.urls import path
# Importaremos las vistas de autenticación de Django y las nuestras
from django.contrib.auth import views as auth_views
from . import views # Vistas de nuestra app 'accounts'

app_name = 'accounts'

urlpatterns = [
    # Usamos LoginView de Django, pero le decimos que use nuestra plantilla
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html'
        ), name='login'),

    # Usamos LogoutView de Django (no necesita plantilla)
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Perfil del usuario
    path('perfil/', views.perfil_usuario, name='perfil'),
    path('cambiar-password/', views.cambiar_password, name='cambiar_password'),
]