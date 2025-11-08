import uuid
from decimal import Decimal, ROUND_HALF_UP # Para cálculos precisos
from django.db import models
from django.conf import settings # Para importar nuestro Usuario personalizado
from django.utils import timezone
from dateutil.relativedelta import relativedelta # Para sumar meses/semanas etc.
from django.db import transaction # Para asegurar que todo se guarde junto

# Importamos modelos de otras apps y de este mismo paquete
from core.models import TimestampModel
from clientes.models import Cliente
from .tasa_interes import TasaInteres


class Préstamo(TimestampModel):
    """
    Representa el préstamo otorgado a un cliente. Es el núcleo del sistema.
    """
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente de Desembolso'), # Antes de generar el plan
        ('Activo', 'Activo'), # Desembolsado y con cuotas pendientes
        ('En Atraso', 'En Atraso'),
        ('Pagado', 'Pagado Completamente'),
        ('Cancelado', 'Cancelado'), # Si se anula antes del desembolso
    ]
    FRECUENCIA_PAGO_CHOICES = [
        ('Semanal', 'Semanal'),
        ('Quincenal', 'Quincenal'),
        ('Mensual', 'Mensual'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_prestamo = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="Número de Préstamo",
        help_text="Número secuencial del préstamo"
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT, # No borrar cliente si tiene préstamos
        related_name="prestamos",
        verbose_name="Cliente"
    )
    tasa_interes = models.ForeignKey(
        TasaInteres,
        on_delete=models.PROTECT, # No borrar tasa si se está usando
        verbose_name="Tasa de Interés Aplicada"
    )
    monto_solicitado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Solicitado"
    )
    numero_cuotas = models.PositiveIntegerField(
        verbose_name="Número de Cuotas"
    )
    frecuencia_pago = models.CharField(
        max_length=10,
        choices=FRECUENCIA_PAGO_CHOICES,
        default='Mensual',
        verbose_name="Frecuencia de Pago"
    )
    fecha_emision = models.DateField(
        default=timezone.now,
        verbose_name="Fecha de Emisión (Desembolso)"
    )
    fecha_primer_pago = models.DateField(
        verbose_name="Fecha del Primer Pago"
    )
    monto_total_interes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0, # Se calculará después
        verbose_name="Monto Total de Intereses",
        editable=False # Campo calculado
    )
    monto_total_pagar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0, # Se calculará después
        verbose_name="Monto Total a Pagar",
        editable=False # Campo calculado
    )
    garantia_descripcion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Descripción de la Garantía"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Activo',
        verbose_name="Estado del Préstamo"
    )
    # Quién registró el préstamo
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Referencia a nuestro Usuario (Empleado)
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Permitir nulo si el usuario se borra o no se especifica
        related_name='prestamos_creados',
        verbose_name="Creado por"
    )

    def __str__(self):
        cliente_nombre = self.cliente.nombre_completo if self.cliente else "Cliente no asignado"
        # Usamos el número de préstamo si existe, sino el UUID truncado
        if self.numero_prestamo:
            return f"Préstamo #{self.numero_prestamo} - {cliente_nombre} (S/ {self.monto_solicitado})"
        else:
            return f"Préstamo ...{str(self.id)[:8]} - {cliente_nombre} (S/ {self.monto_solicitado})"

    # --- LÓGICA DE NEGOCIO ---
    @transaction.atomic # Asegura que o se crea el préstamo y todas las cuotas, o nada
    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para calcular el plan de pagos 
        automáticamente al crear un préstamo nuevo.
        """
        # Verificar si es nuevo usando el campo 'fecha_creacion' que se llena automáticamente
        es_nuevo = not hasattr(self, 'fecha_creacion') or self.fecha_creacion is None

        # --- 0. Asignar número de préstamo si es nuevo y no tiene uno ---
        if es_nuevo and not self.numero_prestamo:
            # Obtener el último número de préstamo
            from django.db.models import Max
            ultimo_prestamo = Préstamo.objects.aggregate(Max('numero_prestamo'))
            ultimo_numero = ultimo_prestamo['numero_prestamo__max']
            self.numero_prestamo = (ultimo_numero or 0) + 1

        # --- 1. Calcular Totales (Solo si es nuevo) ---
        if es_nuevo:
            # Calcular intereses basado en la frecuencia de pago del préstamo
            if self.tasa_interes.tipo_tasa == 'Simple':
                
                # Convertir la tasa de interés según el período de la tasa
                tasa_porcentaje = self.tasa_interes.valor_porcentaje / Decimal('100')
                
                # Ajustar la tasa según el período de la tasa de interés
                if self.tasa_interes.periodo == 'Anual':
                    # Si la tasa es anual, la convertimos según la frecuencia de pago
                    if self.frecuencia_pago == 'Mensual':
                        tasa_ajustada = tasa_porcentaje / Decimal('12')
                    elif self.frecuencia_pago == 'Quincenal':
                        tasa_ajustada = tasa_porcentaje / Decimal('24')
                    elif self.frecuencia_pago == 'Semanal':
                        tasa_ajustada = tasa_porcentaje / Decimal('52')
                    else:
                        tasa_ajustada = tasa_porcentaje
                elif self.tasa_interes.periodo == 'Mensual':
                    # Si la tasa es mensual, la ajustamos según la frecuencia de pago
                    if self.frecuencia_pago == 'Quincenal':
                        tasa_ajustada = tasa_porcentaje / Decimal('2')
                    elif self.frecuencia_pago == 'Semanal':
                        tasa_ajustada = tasa_porcentaje / Decimal('4')
                    else:
                        tasa_ajustada = tasa_porcentaje
                else:
                    # Para otros períodos, usar la tasa directamente
                    tasa_ajustada = tasa_porcentaje
                
                # Calcular interés por cuota
                interes_por_cuota = (self.monto_solicitado * tasa_ajustada).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                
                # Calcular totales
                self.monto_total_interes = interes_por_cuota * self.numero_cuotas
                self.monto_total_pagar = self.monto_solicitado + self.monto_total_interes
                
                # Marcar estado como Activo al crear el plan
                self.estado = 'Activo'
            else:
                # Por ahora, lanzamos un error si no es simple
                raise ValueError("Cálculo solo implementado para Tasa Simple")

        # --- 2. Guardar el Préstamo (para tener un ID) ---
        # Guardamos el préstamo (sea nuevo o actualización)
        super().save(*args, **kwargs)

        # --- 3. Generar Plan de Pagos (Solo si es nuevo y se calcularon intereses) ---
        if es_nuevo and self.monto_total_pagar > 0:
            
            # Calculamos capital por cuota
            capital_por_cuota = (self.monto_solicitado / self.numero_cuotas).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Recalculamos interés por cuota basado en el total (más preciso)
            interes_por_cuota = (self.monto_total_interes / self.numero_cuotas).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            monto_total_cuota = capital_por_cuota + interes_por_cuota

            fecha_cuota = self.fecha_primer_pago

            # Para el ajuste de redondeo
            total_capital_asignado = Decimal('0.00')
            total_interes_asignado = Decimal('0.00')

            for i in range(1, self.numero_cuotas + 1):
                
                # Valores por defecto
                capital_cuota_actual = capital_por_cuota
                interes_cuota_actual = interes_por_cuota
                monto_total_cuota_actual = monto_total_cuota

                # Ajuste para la última cuota para evitar errores de redondeo
                if i == self.numero_cuotas:
                    capital_cuota_actual = self.monto_solicitado - total_capital_asignado
                    interes_cuota_actual = self.monto_total_interes - total_interes_asignado
                    monto_total_cuota_actual = capital_cuota_actual + interes_cuota_actual
                else:
                    total_capital_asignado += capital_cuota_actual
                    total_interes_asignado += interes_cuota_actual

                from .plan_pago import PlanPago
                PlanPago.objects.create(
                    prestamo=self,
                    numero_cuota=i,
                    fecha_vencimiento=fecha_cuota,
                    monto_capital=capital_cuota_actual,
                    monto_interes=interes_cuota_actual,
                    monto_total_cuota=monto_total_cuota_actual,
                    estado='Pendiente',
                    monto_pagado=0,
                    saldo_pendiente=monto_total_cuota_actual # Inicialmente, el saldo es el total
                )

                # Calcular la fecha de la siguiente cuota
                if self.frecuencia_pago == 'Mensual':
                    fecha_cuota += relativedelta(months=1)
                elif self.frecuencia_pago == 'Quincenal':
                    fecha_cuota += relativedelta(weeks=2)
                elif self.frecuencia_pago == 'Semanal':
                    fecha_cuota += relativedelta(weeks=1)


    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_emision'] # Mostrar los más recientes primero