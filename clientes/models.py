from django.db import models
from core.models import TimestampModel  # <-- Importamos nuestra auditoría

class TipoDocumento(TimestampModel):
    """
    Almacena los tipos de documentos de identidad 
    (ej: DNI, RUC, Pasaporte).
    """
    nombre = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Nombre del Documento"
    )
    descripcion = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Descripción"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documento"


class Cliente(TimestampModel):
    """
    Guarda la información central de la persona 
    que recibe el préstamo.
    """
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT, # Prohíbe borrar un tipo si un cliente lo usa
        verbose_name="Tipo de Documento"
    )
    numero_documento = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Número de Documento"
    )
    nombres = models.CharField(
        max_length=200, 
        verbose_name="Nombres"
    )
    apellidos = models.CharField(
        max_length=200, 
        verbose_name="Apellidos"
    )
    email = models.EmailField(
        max_length=254, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="Correo Electrónico"
    )
    telefono = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        verbose_name="Teléfono"
    )
    
    # Campo calculado para búsquedas fáciles
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"


class Direccion(TimestampModel):
    """
    Almacena una o más direcciones para un cliente.
    """
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE, # Si se borra el cliente, se borran sus direcciones
        related_name="direcciones",
        verbose_name="Cliente"
    )
    direccion_linea_1 = models.CharField(
        max_length=255, 
        verbose_name="Dirección"
    )
    distrito = models.CharField(
        max_length=100, 
        verbose_name="Distrito"
    )
    ciudad = models.CharField(
        max_length=100, 
        verbose_name="Ciudad"
    )
    es_principal = models.BooleanField(
        default=True, 
        verbose_name="¿Es dirección principal?"
    )

    def __str__(self):
        return f"{self.direccion_linea_1}, {self.distrito} - {self.cliente.nombres}"

    class Meta:
        verbose_name = "Dirección"
        verbose_name_plural = "Direcciones"