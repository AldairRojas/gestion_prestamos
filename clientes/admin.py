from django.contrib import admin
from .models import TipoDocumento, Cliente, Direccion

# Permite editar Direcciones directamente desde la vista de Cliente
class DireccionInline(admin.StackedInline): # O TabularInline para un formato más compacto
    model = Direccion
    extra = 1 # Cuántos formularios de dirección vacíos mostrar

class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'tipo_documento', 'numero_documento', 'email', 'telefono')
    search_fields = ('nombres', 'apellidos', 'numero_documento', 'email')
    list_filter = ('tipo_documento',)
    inlines = [DireccionInline] # Añade las direcciones al formulario de Cliente
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

admin.site.register(TipoDocumento)
admin.site.register(Cliente, ClienteAdmin)
# No registramos Direccion directamente, se maneja a través de Cliente
# admin.site.register(Direccion) # Opcional si quieres una vista separada para Direcciones