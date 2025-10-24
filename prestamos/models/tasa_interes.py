from django.db import models
from core.models import TimestampModel

class TasaInteres(TimestampModel):
    """
    Define las diferentes tasas de interés aplicables a los préstamos.
    """
    TIPO_TASA_CHOICES = [
        ('Simple', 'Simple'),
        ('Compuesto', 'Compuesto'), # Aunque podríamos no usarlo inicialmente
    ]
    PERIODO_CHOICES = [
        ('Diario', 'Diario'),
        ('Semanal', 'Semanal'),
        ('Quincenal', 'Quincenal'),
        ('Mensual', 'Mensual'),
        ('Anual', 'Anual'),
    ]

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre de la Tasa"
    )
    tipo_tasa = models.CharField(
        max_length=10,
        choices=TIPO_TASA_CHOICES,
        default='Simple',
        verbose_name="Tipo de Tasa"
    )
    valor_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Valor en Porcentaje (%)"
    )
    periodo = models.CharField(
        max_length=10,
        choices=PERIODO_CHOICES,
        default='Mensual',
        verbose_name="Periodo de Aplicación"
    )

    def __str__(self):
        return f"{self.nombre} ({self.valor_porcentaje}% {self.periodo})"

    class Meta:
        verbose_name = "Tasa de Interés"
        verbose_name_plural = "Tasas de Interés"