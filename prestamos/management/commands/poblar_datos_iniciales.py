from django.core.management.base import BaseCommand
from django.db import transaction
from prestamos.models import MetodoPago, TasaInteres
from clientes.models import TipoDocumento
from accounts.models import Perfil


class Command(BaseCommand):
    help = 'Pobla el sistema con datos iniciales básicos'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🌱 Poblando sistema con datos iniciales...')
        )

        try:
            with transaction.atomic():
                # Crear tipos de documento
                tipos_documento = [
                    {'nombre': 'DNI', 'descripcion': 'Documento Nacional de Identidad'},
                    {'nombre': 'RUC', 'descripcion': 'Registro Único de Contribuyentes'},
                    {'nombre': 'Pasaporte', 'descripcion': 'Pasaporte'},
                    {'nombre': 'Carné de Extranjería', 'descripcion': 'Carné de Extranjería'},
                ]
                
                for tipo_data in tipos_documento:
                    tipo, created = TipoDocumento.objects.get_or_create(
                        nombre=tipo_data['nombre'],
                        defaults={'descripcion': tipo_data['descripcion']}
                    )
                    if created:
                        self.stdout.write(f'✅ Creado tipo de documento: {tipo.nombre}')

                # Crear métodos de pago
                metodos_pago = [
                    'Efectivo',
                    'Transferencia Bancaria',
                    'Depósito Bancario',
                    'Cheque',
                ]
                
                for metodo_nombre in metodos_pago:
                    metodo, created = MetodoPago.objects.get_or_create(
                        nombre=metodo_nombre,
                        defaults={'activo': True}
                    )
                    if created:
                        self.stdout.write(f'✅ Creado método de pago: {metodo.nombre}')

                # Crear tasas de interés
                tasas_interes = [
                    {'nombre': 'Tasa Personal', 'tipo_tasa': 'Simple', 'valor_porcentaje': 15.00, 'periodo': 'Anual'},
                    {'nombre': 'Tasa Comercial', 'tipo_tasa': 'Simple', 'valor_porcentaje': 12.00, 'periodo': 'Anual'},
                    {'nombre': 'Tasa Microempresa', 'tipo_tasa': 'Simple', 'valor_porcentaje': 18.00, 'periodo': 'Anual'},
                    {'nombre': 'Tasa Emergencia', 'tipo_tasa': 'Simple', 'valor_porcentaje': 25.00, 'periodo': 'Anual'},
                ]
                
                for tasa_data in tasas_interes:
                    tasa, created = TasaInteres.objects.get_or_create(
                        nombre=tasa_data['nombre'],
                        defaults=tasa_data
                    )
                    if created:
                        self.stdout.write(f'✅ Creada tasa de interés: {tasa.nombre}')

                # Crear perfiles de usuario
                perfiles = [
                    {
                        'nombre': 'Administrador',
                        'puede_crear_prestamos': True,
                        'puede_registrar_pagos': True,
                        'puede_ver_reportes': True,
                    },
                    {
                        'nombre': 'Gestor de Préstamos',
                        'puede_crear_prestamos': True,
                        'puede_registrar_pagos': True,
                        'puede_ver_reportes': False,
                    },
                    {
                        'nombre': 'Cajero',
                        'puede_crear_prestamos': False,
                        'puede_registrar_pagos': True,
                        'puede_ver_reportes': False,
                    },
                ]
                
                for perfil_data in perfiles:
                    perfil, created = Perfil.objects.get_or_create(
                        nombre=perfil_data['nombre'],
                        defaults=perfil_data
                    )
                    if created:
                        self.stdout.write(f'✅ Creado perfil: {perfil.nombre}')

            self.stdout.write(
                self.style.SUCCESS(
                    '\n🎉 ¡Datos iniciales creados exitosamente!\n'
                    'El sistema está listo para comenzar a operar.'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al crear datos iniciales: {str(e)}')
            )
            raise
