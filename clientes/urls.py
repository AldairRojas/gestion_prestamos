from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    # Lista de clientes
    path('', views.lista_clientes, name='lista_clientes'),
    
    # Detalle de cliente
    path('<int:pk>/', views.detalle_cliente, name='detalle_cliente'),
    
    # Crear cliente
    path('crear/', views.crear_cliente, name='crear_cliente'),
    
    # Editar cliente
    path('<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    
    # Agregar dirección
    path('<int:cliente_id>/agregar-direccion/', views.agregar_direccion, name='agregar_direccion'),
    
    # URLs para gestión de tipos de documento
    path('tipos-documento/', views.lista_tipos_documento, name='lista_tipos_documento'),
    path('tipos-documento/crear/', views.crear_tipo_documento, name='crear_tipo_documento'),
    path('tipos-documento/<int:pk>/editar/', views.editar_tipo_documento, name='editar_tipo_documento'),
    path('tipos-documento/<int:pk>/eliminar/', views.eliminar_tipo_documento, name='eliminar_tipo_documento'),
]