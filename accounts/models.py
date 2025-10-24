from django.db import models
from django.contrib.auth.models import AbstractUser
from core.models import TimestampModel  # <-- Importamos nuestra auditoría

class Perfil(TimestampModel):
    """
    Define los roles (ej. Administrador, Gestor) y sus permisos 
    dentro del sistema.
    """
    nombre = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Nombre del Perfil"
    )
    # --- Permisos ---
    puede_crear_prestamos = models.BooleanField(
        default=False, 
        verbose_name="Puede crear préstamos"
    )
    puede_registrar_pagos = models.BooleanField(
        default=True, 
        verbose_name="Puede registrar pagos"
    )
    puede_ver_reportes = models.BooleanField(
        default=False, 
        verbose_name="Puede ver reportes"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"


class Usuario(AbstractUser, TimestampModel):
    """
    Modelo de Usuario personalizado (Empleado) que hereda de AbstractUser 
    de Django y de nuestro TimestampModel.
    """
    # Sobrescribimos el email para que sea único
    email = models.EmailField(
        unique=True, 
        verbose_name="Correo electrónico"
    )
    
    # Campos adicionales del empleado
    nombre_completo = models.CharField(
        max_length=255, 
        verbose_name="Nombre completo"
    )
    perfil = models.ForeignKey(
        Perfil,
        on_delete=models.SET_NULL, # Si se borra el perfil, el usuario no se borra
        null=True,
        blank=True,
        verbose_name="Perfil"
    )

    # --- Configuración del modelo ---
    
    # Le decimos a Django que el campo 'email' será el usado para el login
    USERNAME_FIELD = 'email'
    
    # Campos requeridos al crear un superusuario (además de email y pass)
    REQUIRED_FIELDS = ['username', 'nombre_completo']

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Usuario (Empleado)"
        verbose_name_plural = "Usuarios (Empleados)"