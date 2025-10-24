from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Perfil, Usuario

# Personalización básica para el modelo Usuario en el admin
class CustomUserAdmin(UserAdmin):
    model = Usuario
    list_display = ('email', 'nombre_completo', 'perfil', 'is_staff', 'is_active',)
    list_filter = ('is_staff', 'is_active', 'perfil',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('nombre_completo', 'perfil')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'fecha_creacion', 'fecha_actualizacion')}),
    )
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'last_login') # Heredados de TimestampModel y User
    search_fields = ('email', 'nombre_completo',)
    ordering = ('email',)

    # Necesario porque cambiamos USERNAME_FIELD a email
    # (asegúrate de que AbstractUser no define estos para evitar colisiones)
    # Podríamos necesitar ajustar esto si da problemas
    # filter_horizontal = ('groups', 'user_permissions',) # Descomentar si usas groups/permissions directamente


admin.site.register(Usuario, CustomUserAdmin)
admin.site.register(Perfil)