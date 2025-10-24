# prestamos/admin.py
from django.contrib import admin
# Importamos todos los modelos desde el paquete 'models'
from .models import (
    TasaInteres, MetodoPago, CuentaBancaria, Préstamo,
    PlanPago, Pago, DetallePago, Mora
)

# Clases Admin simples para empezar (podemos personalizarlas luego)
class TasaInteresAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_tasa', 'valor_porcentaje', 'periodo')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

class CuentaBancariaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'banco', 'numero_cuenta', 'tipo_cuenta', 'es_principal')
    list_filter = ('banco', 'tipo_cuenta')
    search_fields = ('cliente__nombres', 'cliente__apellidos', 'numero_cuenta', 'cci')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

# Permite ver el plan de pagos directamente desde el Préstamo
class PlanPagoInline(admin.TabularInline):
    model = PlanPago
    extra = 0 # No mostrar formularios vacíos por defecto
    readonly_fields = ('numero_cuota', 'fecha_vencimiento', 'monto_capital', 'monto_interes', 'monto_total_cuota', 'estado', 'monto_pagado', 'saldo_pendiente', 'fecha_creacion', 'fecha_actualizacion') # Hacerlas de solo lectura aquí
    can_delete = False # No permitir borrar cuotas desde aquí
    ordering = ('numero_cuota',)

class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'monto_solicitado', 'numero_cuotas', 'estado', 'fecha_emision')
    search_fields = ('id__startswith', 'cliente__nombres', 'cliente__apellidos', 'cliente__numero_documento')
    list_filter = ('estado', 'frecuencia_pago', 'tasa_interes')
    date_hierarchy = 'fecha_emision'
    readonly_fields = ('monto_total_interes', 'monto_total_pagar', 'fecha_creacion', 'fecha_actualizacion', 'creado_por')
    inlines = [PlanPagoInline] # Mostrar el plan de pagos asociado

    # Podríamos añadir una acción para "Generar Plan de Pagos" si no lo hacemos automático al guardar

# Permite ver los detalles de aplicación desde el Pago
class DetallePagoInline(admin.TabularInline):
    model = DetallePago
    extra = 0
    readonly_fields = ('cuota_plan', 'monto_aplicado', 'fecha_creacion', 'fecha_actualizacion')
    can_delete = False

class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'prestamo', 'monto_pagado', 'fecha_pago', 'metodo_pago', 'registrado_por', 'distribuido')
    search_fields = ('id__startswith', 'prestamo__cliente__nombres', 'prestamo__cliente__apellidos', 'referencia')
    list_filter = ('metodo_pago', 'distribuido', 'fecha_pago')
    date_hierarchy = 'fecha_pago'
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'registrado_por')
    inlines = [DetallePagoInline]


# Registramos todos los modelos
admin.site.register(TasaInteres, TasaInteresAdmin)
admin.site.register(MetodoPago, MetodoPagoAdmin)
admin.site.register(CuentaBancaria, CuentaBancariaAdmin)
admin.site.register(Préstamo, PrestamoAdmin)
admin.site.register(Pago, PagoAdmin)
# Registramos los otros sin personalización por ahora
admin.site.register(PlanPago)
admin.site.register(DetallePago)
admin.site.register(Mora)