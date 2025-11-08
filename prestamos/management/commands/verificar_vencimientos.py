from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from prestamos.models import PlanPago, Préstamo
from django.db.models import Q

class Command(BaseCommand):
    help = 'Verifica préstamos vencidos y actualiza estados'

    def handle(self, *args, **options):
        """
        Comando para verificar préstamos vencidos y generar alertas.
        """
        hoy = timezone.now().date()
        
        # Buscar cuotas vencidas
        cuotas_vencidas = PlanPago.objects.filter(
            fecha_vencimiento__lt=hoy,
            estado='Pendiente'
        )
        
        # Actualizar estado de cuotas vencidas
        cuotas_actualizadas = 0
        for cuota in cuotas_vencidas:
            cuota.estado = 'Vencida'
            cuota.save()
            cuotas_actualizadas += 1
        
        # Buscar préstamos que deben cambiar a "En Atraso"
        prestamos_en_atraso = Préstamo.objects.filter(
            estado='Activo',
            plan_pagos__estado='Vencida'
        ).distinct()
        
        prestamos_actualizados = 0
        for prestamo in prestamos_en_atraso:
            prestamo.estado = 'En Atraso'
            prestamo.save()
            prestamos_actualizados += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Verificación completada:\n'
                f'   - Cuotas vencidas actualizadas: {cuotas_actualizadas}\n'
                f'   - Préstamos en atraso actualizados: {prestamos_actualizados}'
            )
        )
