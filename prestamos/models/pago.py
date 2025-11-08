import uuid
from decimal import Decimal, ROUND_HALF_UP
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
            from datetime import date
            from dateutil.relativedelta import relativedelta

            # Fecha del pago para verificar si es anticipado (Ley N.º 29571 de Perú)
            fecha_pago_date = self.fecha_pago.date() if hasattr(self.fecha_pago, 'date') else self.fecha_pago

            # Obtener cuotas pendientes o parcialmente pagadas, ordenadas por número
            # Si se proporcionaron IDs de cuotas específicas (como atributo temporal _cuotas_ids),
            # usar solo esas cuotas
            cuotas_ids = getattr(self, '_cuotas_ids', None) or kwargs.get('cuotas_ids', None)
            if cuotas_ids:
                # Filtrar solo las cuotas específicas seleccionadas
                cuotas_pendientes = PlanPago.objects.filter(
                    prestamo=prestamo_asociado,
                    id__in=cuotas_ids,
                    estado__in=['Pendiente', 'Vencida', 'Pagada Parcialmente']
                ).order_by('numero_cuota')
            else:
                # Comportamiento original: todas las cuotas pendientes
                cuotas_pendientes = PlanPago.objects.filter(
                    prestamo=prestamo_asociado,
                    estado__in=['Pendiente', 'Vencida', 'Pagada Parcialmente']
                ).order_by('numero_cuota')

            # Primero, calcular todos los ajustes de intereses antes de distribuir
            # Esto nos permite saber el monto real necesario y ajustar el pago si es necesario
            monto_real_necesario = Decimal('0.00')
            
            for cuota in cuotas_pendientes:
                saldo_cuota_temp = cuota.saldo_pendiente
                if saldo_cuota_temp <= Decimal('0.00'):
                    continue
                    
                # Verificar si será anticipado
                es_pago_anticipado = fecha_pago_date < cuota.fecha_vencimiento
                
                if es_pago_anticipado and cuota.monto_interes > 0:
                    # Buscar la cuota anterior (sin filtrar por estado, solo por número)
                    cuota_anterior_temp = PlanPago.objects.filter(
                        prestamo=prestamo_asociado,
                        numero_cuota__lt=cuota.numero_cuota
                    ).order_by('-numero_cuota').first()
                    
                    if cuota_anterior_temp:
                        fecha_base_interes_temp = cuota_anterior_temp.fecha_vencimiento
                    else:
                        fecha_base_interes_temp = prestamo_asociado.fecha_emision
                    
                    dias_transcurridos_temp = (fecha_pago_date - fecha_base_interes_temp).days
                    dias_periodo_total_temp = (cuota.fecha_vencimiento - fecha_base_interes_temp).days
                    
                    # Aplicar la ley si hay un período válido
                    if dias_periodo_total_temp > 0:
                        # Si se paga antes o el mismo día que comienza el período, interés = 0
                        # (aún no ha comenzado el período de la cuota, no hay intereses generados)
                        if dias_transcurridos_temp <= 0:
                            interes_proporcional_temp = Decimal('0.00')
                        else:
                            proporcion_interes_temp = Decimal(str(dias_transcurridos_temp)) / Decimal(str(dias_periodo_total_temp))
                            interes_proporcional_temp = (cuota.monto_interes * proporcion_interes_temp).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        
                        monto_total_cuota_temp = cuota.monto_capital + interes_proporcional_temp
                        monto_pagado_anterior_temp = cuota.monto_pagado or Decimal('0.00')
                        saldo_cuota_temp = monto_total_cuota_temp - monto_pagado_anterior_temp
                
                if saldo_cuota_temp > Decimal('0.00'):
                    monto_real_necesario += saldo_cuota_temp
                    
                # Si ya tenemos suficiente para cubrir el monto pagado, no necesitamos seguir
                if monto_real_necesario >= monto_a_distribuir:
                    break
            
            # Ajustar el monto del pago si hay diferencia por intereses reducidos
            # Solo ajustamos si el monto real necesario es menor que el monto pagado
            if monto_real_necesario < monto_a_distribuir:
                monto_ajustado = monto_real_necesario
                # Actualizar el monto_pagado del pago
                Pago.objects.filter(pk=self.pk).update(monto_pagado=monto_ajustado)
                monto_a_distribuir = monto_ajustado
                self.monto_pagado = monto_ajustado
            
            # Ahora distribuir el monto (ya ajustado si fue necesario)
            # Si se proporcionaron cuotas específicas, solo distribuir entre esas cuotas
            # y no continuar si el monto se agota o si hay un exceso
            for cuota in cuotas_pendientes:
                if monto_a_distribuir <= Decimal('0.00'):
                    # Si se proporcionaron cuotas específicas y ya no hay monto para distribuir,
                    # no continuar con otras cuotas
                    break # Salir si ya distribuimos todo el monto

                saldo_cuota_original = cuota.saldo_pendiente
                if saldo_cuota_original <= Decimal('0.00'):
                    continue # Pasar a la siguiente cuota

                # Verificar si el pago es anticipado (Ley N.º 29571 - Art. 85)
                # Si se paga antes del vencimiento, solo se cobran intereses hasta la fecha del pago
                es_pago_anticipado = fecha_pago_date < cuota.fecha_vencimiento
                interes_original = cuota.monto_interes
                
                if es_pago_anticipado and cuota.monto_interes > 0:
                    # Calcular intereses proporcionales solo hasta la fecha del pago (Ley N.º 29571 - Art. 85)
                    # La fecha base es el inicio del período de la cuota: fecha de vencimiento de la cuota anterior

                    
                    # Obtener la fecha base para calcular intereses
                    # Buscar la cuota anterior (sin filtrar por estado, solo por número de cuota)
                    cuota_anterior = PlanPago.objects.filter(
                        prestamo=prestamo_asociado,
                        numero_cuota__lt=cuota.numero_cuota
                    ).order_by('-numero_cuota').first()
                    
                    if cuota_anterior:
                        # Para cuotas posteriores, el período comienza cuando vence la cuota anterior
                        fecha_base_interes = cuota_anterior.fecha_vencimiento
                    else:
                        # Para la primera cuota, el período comienza en la fecha de emisión
                        fecha_base_interes = prestamo_asociado.fecha_emision
                    
                    # Calcular días transcurridos desde la fecha base hasta la fecha del pago
                    dias_transcurridos = (fecha_pago_date - fecha_base_interes).days
                    
                    # Calcular días totales del período de la cuota (desde fecha base hasta vencimiento)
                    dias_periodo_total = (cuota.fecha_vencimiento - fecha_base_interes).days
                    
                    # Aplicar la ley: si el pago es antes del vencimiento y hay un período válido
                    if dias_periodo_total > 0:
                        # Si se paga antes de que comience el período 
                        # No hay intereses generados porque el período aún no ha comenzado
                        if dias_transcurridos <= 0:
                            interes_proporcional = Decimal('0.00')
                        else:
                            # Calcular interés proporcional solo hasta la fecha del pago
                            proporcion_interes = Decimal(str(dias_transcurridos)) / Decimal(str(dias_periodo_total))
                            interes_proporcional = (cuota.monto_interes * proporcion_interes).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        
                        # Recalcular el monto total de la cuota con interés reducido
                        nuevo_monto_total_cuota = cuota.monto_capital + interes_proporcional
                        
                        # Actualizar la cuota con el interés reducido ANTES de calcular el saldo
                        # Esto asegura que los valores se guarden correctamente
                        cuota.monto_interes = interes_proporcional
                        cuota.monto_total_cuota = nuevo_monto_total_cuota
                        
                        # Si la cuota ya tenía pagos parciales, ajustar el saldo
                        monto_pagado_anterior = cuota.monto_pagado or Decimal('0.00')
                        nuevo_saldo_cuota = nuevo_monto_total_cuota - monto_pagado_anterior
                        
                        # Actualizar el saldo a distribuir
                        saldo_cuota = nuevo_saldo_cuota
                    else:
                        # Si no se cumple la condición, usar el saldo original
                        saldo_cuota = saldo_cuota_original
                else:
                    saldo_cuota = saldo_cuota_original

                monto_aplicar_a_cuota = min(monto_a_distribuir, saldo_cuota)
                
                # Si se proporcionaron cuotas específicas y hay un exceso después de cubrir estas cuotas,
                # NO distribuir el exceso a otras cuotas no seleccionadas
                # En este caso, solo aplicamos lo que corresponde a las cuotas seleccionadas

                if es_pago_anticipado and interes_original != cuota.monto_interes:
                    # Los valores ya están actualizados arriba (monto_interes y monto_total_cuota)
                    # Guardamos estos cambios primero
                    PlanPago.objects.filter(pk=cuota.pk).update(
                        monto_interes=cuota.monto_interes,
                        monto_total_cuota=cuota.monto_total_cuota
                    )
                    # Refrescar la instancia de la base de datos
                    cuota.refresh_from_db(fields=['monto_interes', 'monto_total_cuota'])

                # Creamos el registro del detalle del pago
                DetallePago.objects.create(
                    pago=self,
                    cuota_plan=cuota,
                    monto_aplicado=monto_aplicar_a_cuota
                )

                # Actualizamos la cuota (sumamos al monto pagado)
                # Ahora el monto_total_cuota ya está actualizado 
                cuota.monto_pagado = (cuota.monto_pagado or Decimal('0.00')) + monto_aplicar_a_cuota
                
                # Guardar la cuota 
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