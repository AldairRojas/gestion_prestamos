from django.core.management.base import BaseCommand
from django.db import transaction
from prestamos.models import Préstamo, Pago, PlanPago, DetallePago, MetodoPago, TasaInteres
from clientes.models import Cliente, Direccion, TipoDocumento
from accounts.models import Usuario, Perfil


class Command(BaseCommand):
    help = 'Limpia todos los datos de prueba del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma que realmente quieres eliminar todos los datos',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  ADVERTENCIA: Este comando eliminará TODOS los datos del sistema.\n'
                    'Incluye: Préstamos, Pagos, Clientes, Usuarios, etc.\n\n'
                    'Si estás seguro, ejecuta el comando con --confirm'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING('🧹 Iniciando limpieza de datos...')
        )

        try:
            with transaction.atomic():
                # Eliminar en orden para respetar las foreign keys
                
                # 1. Eliminar detalles de pagos
                detalle_count = DetallePago.objects.count()
                DetallePago.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {detalle_count} detalles de pagos')

                # 2. Eliminar pagos
                pago_count = Pago.objects.count()
                Pago.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {pago_count} pagos')

                # 3. Eliminar planes de pago
                plan_count = PlanPago.objects.count()
                PlanPago.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {plan_count} planes de pago')

                # 4. Eliminar préstamos
                prestamo_count = Préstamo.objects.count()
                Préstamo.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {prestamo_count} préstamos')

                # 5. Eliminar direcciones de clientes
                direccion_count = Direccion.objects.count()
                Direccion.objects.all().delete()
                self.stdout.write(f'✅ Eliminadas {direccion_count} direcciones')

                # 6. Eliminar clientes
                cliente_count = Cliente.objects.count()
                Cliente.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {cliente_count} clientes')

                # 7. Eliminar tipos de documento
                tipo_doc_count = TipoDocumento.objects.count()
                TipoDocumento.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {tipo_doc_count} tipos de documento')

                # 8. Eliminar métodos de pago
                metodo_count = MetodoPago.objects.count()
                MetodoPago.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {metodo_count} métodos de pago')

                # 9. Eliminar tasas de interés
                tasa_count = TasaInteres.objects.count()
                TasaInteres.objects.all().delete()
                self.stdout.write(f'✅ Eliminadas {tasa_count} tasas de interés')

                # 10. Eliminar usuarios (excepto superusuarios)
                usuario_count = Usuario.objects.filter(is_superuser=False).count()
                Usuario.objects.filter(is_superuser=False).delete()
                self.stdout.write(f'✅ Eliminados {usuario_count} usuarios (se mantuvieron los superusuarios)')

                # 11. Eliminar perfiles
                perfil_count = Perfil.objects.count()
                Perfil.objects.all().delete()
                self.stdout.write(f'✅ Eliminados {perfil_count} perfiles')

            self.stdout.write(
                self.style.SUCCESS(
                    '\n🎉 ¡Limpieza completada exitosamente!\n'
                    'Todos los datos de prueba han sido eliminados.\n'
                    'El sistema está listo para uso en producción.'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error durante la limpieza: {str(e)}')
            )
            raise