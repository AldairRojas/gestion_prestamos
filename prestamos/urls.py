from django.urls import path
from . import views # Importa las vistas (lista_prestamos, detalle_prestamo) de la app prestamos

# Define un namespace para esta app. Es MUY importante para {% url ... %}
app_name = 'prestamos'

urlpatterns = [
    # URL para el dashboard. Se accederá como /prestamos/
    path('', views.dashboard, name='dashboard'),
    
    # URL para la lista de préstamos. Se accederá como /prestamos/lista/
    path('lista/', views.lista_prestamos, name='lista_prestamos'),

    # URL para ver el detalle de un préstamo específico.
    # Se accederá como /prestamos/uuid-del-prestamo/
    # <uuid:pk> captura el ID (UUID) del préstamo desde la URL y lo pasa a la vista como 'pk'
    path('<uuid:pk>/', views.detalle_prestamo, name='detalle_prestamo'),

    # URL para registrar un pago
    path('<uuid:pk>/registrar-pago/', views.registrar_pago, name='registrar_pago'),
    
    # URL para crear un préstamo
    path('crear/', views.crear_prestamo, name='crear_prestamo'),
    
    # URLs para métodos de pago
    path('reportes/', views.reportes, name='reportes'),
    path('metodos-pago/', views.lista_metodos_pago, name='lista_metodos_pago'),
    path('metodos-pago/crear/', views.crear_metodo_pago, name='crear_metodo_pago'),
    path('metodos-pago/<int:pk>/editar/', views.editar_metodo_pago, name='editar_metodo_pago'),
    path('metodos-pago/<int:pk>/eliminar/', views.eliminar_metodo_pago, name='eliminar_metodo_pago'),
]