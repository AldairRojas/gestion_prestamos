import uuid
from decimal import Decimal
from django.db import models
from core.models import TimestampModel

class PlanPago(TimestampModel):
    """
    Almacena cada cuota individual del cronograma de pagos de un préstamo.
    Se genera automáticamente al crear/aprobar un Préstamo.
    """
    ESTADO_CUOTA_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Pagada', 'Pagada'),
        ('Vencida', 'Vencida'),
        ('Pagada Parcialmente', 'Pagada Parcialmente'),
        ('Cancelada', 'Cancelada'), # Si se cancela el préstamo
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prestamo = models.ForeignKey(
        'prestamos.Préstamo',
        on_delete=models.CASCADE, # Si se borra el préstamo, se borra su plan
        related_name="plan_pagos",
        verbose_name="Préstamo"
    )
    numero_cuota = models.PositiveIntegerField(
        verbose_name="Número de Cuota"
    )
    fecha_vencimiento = models.DateField(
        verbose_name="Fecha de Vencimiento"
    )
    monto_capital = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Capital"
    )
    monto_interes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Interés"
    )
    monto_total_cuota = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Total Cuota"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CUOTA_CHOICES,
        default='Pendiente',
        verbose_name="Estado de la Cuota"
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Monto Pagado de esta Cuota"
    )
    saldo_pendiente = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0, # Se calculará
        verbose_name="Saldo Pendiente de esta Cuota",
        editable=False # Campo calculado
    )

    def save(self, *args, **kwargs):
        # Asegurarse de que monto_pagado no sea None
        monto_pagado = self.monto_pagado or Decimal('0.00')
        self.saldo_pendiente = self.monto_total_cuota - monto_pagado

        # Actualizar estado basado en saldo
        if self.estado != 'Cancelada': # No cambiar estado si ya está cancelada
            if self.saldo_pendiente <= 0:
                self.estado = 'Pagada'
                self.saldo_pendiente = Decimal('0.00') # Asegurar que no sea negativo
            elif monto_pagado > 0:
                self.estado = 'Pagada Parcialmente'
            else: # monto_pagado es 0
                # Podríamos añadir lógica para 'Vencida' aquí comparando con timezone.now().date()
                # Pero es mejor hacerlo en una tarea separada o al consultar
                if self.estado not in ['Pendiente', 'Vencida']: # Si estaba pagada/parcial y se revierte pago
                    self.estado = 'Pendiente' # Volver a pendiente

        super().save(*args, **kwargs)

    def calcular_mora(self):
        """
        Calcula la mora si la cuota está vencida.
        """
        from django.utils import timezone
        from decimal import Decimal
        
        if self.estado == 'Vencida' and self.saldo_pendiente > 0:
            dias_vencido = (timezone.now().date() - self.fecha_vencimiento).days
            if dias_vencido > 0:
                # Calcular mora: 5% del saldo pendiente por cada mes vencido
                meses_vencido = dias_vencido / 30
                tasa_mora = Decimal('0.05')  # 5% mensual
                mora = self.saldo_pendiente * tasa_mora * Decimal(str(meses_vencido))
                return mora.quantize(Decimal('0.01'))
        return Decimal('0.00')

    def __str__(self):
        # Accedemos al id a través de self.prestamo_id que Django crea automáticamente
        num_cuotas_total = self.prestamo.numero_cuotas if self.prestamo_id else 'N/A'
        prestamo_id = str(self.prestamo_id)[:8] if self.prestamo_id else 'N/A' # Usamos self.prestamo_id
        return f"Cuota {self.numero_cuota}/{num_cuotas_total} (Préstamo: ...{prestamo_id})"

    class Meta:
        verbose_name = "Cuota del Plan de Pago"
        verbose_name_plural = "Plan de Pagos"
        # Asegura que no haya dos cuotas con el mismo número para el mismo préstamo
        unique_together = ('prestamo', 'numero_cuota')
        ordering = ['prestamo', 'numero_cuota']