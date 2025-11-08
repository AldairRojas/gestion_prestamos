import uuid
from django.db import models
from django.utils import timezone

# Importamos modelos de este mismo paquete
from core.models import TimestampModel

class Mora(TimestampModel):
    """
    Registra los cargos por mora generados si una cuota del PlanPago
    no se paga a tiempo.
    """
    ESTADO_MORA_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Pagada', 'Pagada'),
        ('Cancelada', 'Cancelada'), # Si se cancela la cuota/préstamo
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cuota_plan = models.ForeignKey(
        'prestamos.PlanPago',
        on_delete=models.CASCADE, # Si se borra la cuota, se borra la mora asociada
        related_name="moras",
        verbose_name="Cuota Vencida"
    )
    monto_mora = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto de la Mora"
    )
    fecha_generacion = models.DateField(
        default=timezone.now,
        verbose_name="Fecha de Generación"
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_MORA_CHOICES,
        default='Pendiente',
        verbose_name="Estado de la Mora"
    )
    # Podríamos añadir un ForeignKey a Pago si una mora se paga específicamente
    # pago_asociado = models.ForeignKey(Pago, ...)

    def __str__(self):
        cuota_num = self.cuota_plan.numero_cuota if self.cuota_plan else 'N/A'
        return f"Mora de {self.monto_mora} para Cuota {cuota_num}"

    class Meta:
        verbose_name = "Cargo por Mora"
        verbose_name_plural = "Cargos por Mora"
        ordering = ['cuota_plan', '-fecha_generacion'] # Ordenar por cuota y fecha