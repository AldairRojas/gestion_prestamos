import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings # Para importar nuestro Usuario personalizado
from django.utils import timezone
from django.db import transaction
from .detalle_pago import DetallePago

# Importamos modelos necesarios
from core.models import TimestampModel
from .metodo_pago import MetodoPago
# Importamos PlanPago y DetallePago para la lógica de distribución
# Usamos texto para PlanPago para evitar posible importación circular si PlanPago importara Pago
# from .plan_pago import PlanPago # Comentado

class Pago(TimestampModel):
    """
    Registra un evento de pago realizado por un cliente para un préstamo.
    Un solo pago puede cubrir varias cuotas o parte de ellas.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prestamo = models.ForeignKey(
        'prestamos.Préstamo',
        on_delete=models.PROTECT, # No borrar préstamo si tiene pagos
        related_name="pagos",
        verbose_name="Préstamo Asociado"
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Pagado"
    )
    fecha_pago = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha y Hora del Pago"
    )
    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT, # No borrar método si se usó
        verbose_name="Método de Pago"
    )
    referencia = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Referencia (Nro. Operación)"
    )
    # Quién registró el pago
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Referencia a nuestro Usuario (Empleado)
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Permitir nulo
        related_name='pagos_registrados',
        verbose_name="Registrado por"
    )
    # Campo para indicar si el pago ya fue distribuido en las cuotas
    distribuido = models.BooleanField(default=False, editable=False)

    def __str__(self):
        # Accedemos al ID del préstamo de forma segura
        prestamo_id_corto = str(self.prestamo_id)[:8] if self.prestamo_id else 'N/A'
        pago_id_corto = str(self.id)[:8]
        return f"Pago ...{pago_id_corto} de {self.monto_pagado} (Préstamo: ...{prestamo_id_corto})"

    # --- LÓGICA DE NEGOCIO ---
    @transaction.atomic # Asegura que el pago y sus detalles se guarden juntos
    def save(self, *args, **kwargs):
        """
        Sobrescribe save para distribuir el monto pagado entre las cuotas
        pendientes del préstamo asociado, solo al crear un nuevo pago.
        """
        # Verificar si es un pago nuevo y si aún no ha sido distribuido
        # Usamos el campo 'fecha_creacion' para detectar si es nuevo
        es_nuevo_y_no_distribuido = not hasattr(self, 'fecha_creacion') or self.fecha_creacion is None

        # --- 1. Guardar el Pago Primero ---
        # Siempre guardamos el pago para tener un ID y registrar el evento
        # Si es una actualización, solo guardamos los cambios normales
        super().save(*args, **kwargs)

        # --- 2. Distribuir el Monto (Solo si es nuevo y no distribuido) ---
        if es_nuevo_y_no_distribuido:
            monto_a_distribuir = self.monto_pagado
            prestamo_asociado = self.prestamo # Obtenemos el préstamo ligado a este pago

            if not prestamo_asociado:
                # Considerar lanzar un error o manejar esta situación
                return # Salir si no hay préstamo

            # Importamos PlanPago AQUI dentro para evitar importación circular al inicio
            from .plan_pago import PlanPago

            # Obtener cuotas pendientes o parcialmente pagadas, ordenadas por número
            cuotas_pendientes = PlanPago.objects.filter(
                prestamo=prestamo_asociado,
                estado__in=['Pendiente', 'Vencida', 'Pagada Parcialmente']
            ).order_by('numero_cuota')

            for cuota in cuotas_pendientes:
                if monto_a_distribuir <= Decimal('0.00'):
                    break # Salir si ya distribuimos todo el monto

                saldo_cuota = cuota.saldo_pendiente
                if saldo_cuota <= Decimal('0.00'):
                    continue # Pasar a la siguiente cuota

                monto_aplicar_a_cuota = min(monto_a_distribuir, saldo_cuota)

                # Creamos el registro del detalle del pago
                DetallePago.objects.create(
                    pago=self,
                    cuota_plan=cuota,
                    monto_aplicado=monto_aplicar_a_cuota
                )

                # Actualizamos la cuota (sumamos al monto pagado)
                # El método save() de PlanPago se encargará de recalcular saldo y estado
                cuota.monto_pagado = (cuota.monto_pagado or Decimal('0.00')) + monto_aplicar_a_cuota
                cuota.save()

                # Reducimos el monto que queda por distribuir
                monto_a_distribuir -= monto_aplicar_a_cuota

            # Marcamos el pago como distribuido para no volver a procesarlo
            # Usamos update() para evitar llamar a save() de este mismo objeto otra vez
            Pago.objects.filter(pk=self.pk).update(distribuido=True)
            # Actualizamos el estado en la instancia actual por si se usa después en la misma petición
            self.distribuido = True

            # --- Opcional: Actualizar estado del préstamo ---
            # Verificamos si AHORA todas las cuotas están pagadas
            if not PlanPago.objects.filter(prestamo=prestamo_asociado).exclude(estado='Pagada').exists():
               # Importar Préstamo aquí para evitar importación circular
               from .prestamo import Préstamo
               prestamo_asociado.estado = 'Pagado'
               # Usamos update() también aquí para eficiencia y evitar posibles recursiones
               Préstamo.objects.filter(pk=prestamo_asociado.pk).update(estado='Pagado')
               # Actualizamos la instancia local por si acaso
               prestamo_asociado.refresh_from_db(fields=['estado'])




    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_pago'] # Mostrar los más recientes primero