"""
URL configuration for proyecto_prestamos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include # Asegúrate de importar include
from django.views.generic import RedirectView # Para redirigir la raíz al login
from django.conf import settings # Para archivos estáticos/media
from django.conf.urls.static import static # Para archivos estáticos/media
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.http import HttpResponseRedirect

def home_redirect(request):
    """
    Vista que redirige a los usuarios autenticados al dashboard
    y a los no autenticados al login.
    """
    if request.user.is_authenticated:
        return redirect('prestamos:dashboard')
    else:
        return redirect('accounts:login')

urlpatterns = [
    # URL para el panel de administración de Django
    path('admin/', admin.site.urls),

    # Redirigir la página raíz ('/') basado en el estado de autenticación
    path('', home_redirect, name='home'),

    # Incluir las URLs de la app 'accounts' (para login, logout, etc.)
    # Busca el archivo accounts/urls.py y usa su namespace 'accounts'
    path('accounts/', include('accounts.urls', namespace='accounts')),

    # Incluir las URLs de la app 'prestamos' (lista, detalle, etc.)
    # Busca el archivo prestamos/urls.py y usa su namespace 'prestamos'
    path('prestamos/', include('prestamos.urls', namespace='prestamos')),

    # Incluir las URLs de la app 'clientes'
    path('clientes/', include('clientes.urls', namespace='clientes')),
]

# --- Configuración para servir archivos estáticos y media durante el desarrollo (DEBUG=True) ---
if settings.DEBUG:
    # Si tienes archivos subidos por usuarios (MEDIA_ROOT), esto los sirve
    # Asegúrate de haber definido MEDIA_URL y MEDIA_ROOT en settings.py
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Si tienes una carpeta 'static' en la raíz del proyecto (junto a manage.py)
    # y quieres que Django la sirva directamente (además de las de las apps), usa esto.
    # Necesitarás definir STATICFILES_DIRS en settings.py para que funcione bien.
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()

    # La línea para STATIC_URL generalmente no es necesaria aquí si usas staticfiles_urlpatterns
    # o si APP_DIRS=True en TEMPLATES (Django buscará en las carpetas 'static' de cada app).
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
