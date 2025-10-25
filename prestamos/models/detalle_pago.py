from django.db import models
from decimal import Decimal

# Importamos modelos de este mismo paquete, PERO SIN importar Pago directamente
from core.models import TimestampModel
# from .pago import Pago # <-- ELIMINAMOS ESTA LÍNEA

class DetallePago(TimestampModel):
    """
    Modelo "puente" que indica cuánto de un Pago específico se aplicó
    a una Cuota específica del PlanPago.
    """
    pago = models.ForeignKey(
        'prestamos.Pago', # <-- CAMBIO AQUÍ: Usamos el texto 'app_name.ModelName'
        on_delete=models.CASCADE, # Si se borra el pago, se borra su detalle
        related_name="detalles",
        verbose_name="Pago"
    )
    cuota_plan = models.ForeignKey(
        'prestamos.PlanPago',
        on_delete=models.PROTECT, # No borrar cuota si tiene pagos aplicados
        related_name="pagos_aplicados",
        verbose_name="Cuota Afectada"
    )
    monto_aplicado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Aplicado a esta Cuota"
    )

    def __str__(self):
        # Usamos self.pago_id (que Django crea) para evitar la importación directa
        pago_id_corto = str(self.pago_id)[:8] if self.pago_id else 'N/A'
        cuota_num = self.cuota_plan.numero_cuota if self.cuota_plan_id else 'N/A' # Usamos cuota_plan_id
        return f"{self.monto_aplicado} (Pago: ...{pago_id_corto}) -> Cuota {cuota_num}"

    class Meta:
        verbose_name = "Detalle de Aplicación de Pago"
        verbose_name_plural = "Detalles de Aplicación de Pagos"
        # Evitar duplicados: no aplicar el mismo pago a la misma cuota dos veces
        unique_together = ('pago', 'cuota_plan')