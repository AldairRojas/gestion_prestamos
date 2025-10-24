from django.db import models
from core.models import TimestampModel

class MetodoPago(TimestampModel):
    """
    Define las formas en que el cliente puede pagar (Efectivo, Transferencia, etc.).
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre del Método"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="¿Está activo?"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"