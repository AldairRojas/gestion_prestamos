from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone
from .models import Pago, MetodoPago, Préstamo, TasaInteres
from clientes.models import Cliente


class PagoForm(forms.Form):
    """
    Formulario simplificado para registrar pagos de préstamos.
    """
    
    def __init__(self, *args, **kwargs):
        self.prestamo = kwargs.pop('prestamo', None)
        super().__init__(*args, **kwargs)
        
        # Campo para número de cuotas a pagar
        if self.prestamo:
            from .models import PlanPago
            cuotas_pendientes = PlanPago.objects.filter(
                prestamo=self.prestamo,
                estado__in=['Pendiente', 'Vencida', 'Pagada Parcialmente']
            ).order_by('numero_cuota')
            
            # Crear opciones para el número de cuotas
            cuotas_choices = [('', 'Seleccione...')]
            for i in range(1, min(len(cuotas_pendientes) + 1, 11)):  # Máximo 10 cuotas
                cuotas_choices.append((i, f"{i} cuota{'s' if i > 1 else ''}"))
            
            self.fields['numero_cuotas_pagar'] = forms.ChoiceField(
                choices=cuotas_choices,
                widget=forms.Select(attrs={
                    'class': 'form-select',
                    'required': True
                }),
                label='Número de Cuotas a Pagar',
                help_text='Seleccione cuántas cuotas desea pagar (empezando por la primera pendiente).'
            )
        
        # Método de pago
        self.fields['metodo_pago'] = forms.ModelChoiceField(
            queryset=MetodoPago.objects.filter(activo=True),
            widget=forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            label='Método de Pago',
            empty_label='Seleccione un método de pago...'
        )
        
        # Referencia (opcional)
        self.fields['referencia'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de operación, voucher, etc.'
            }),
            label='Referencia/Número de Operación'
        )
    
    def clean_numero_cuotas_pagar(self):
        """
        Validar que se haya seleccionado un número de cuotas válido.
        """
        numero_cuotas = self.cleaned_data.get('numero_cuotas_pagar')
        
        if not numero_cuotas or numero_cuotas == '':
            raise ValidationError('Debe seleccionar el número de cuotas a pagar.')
        
        return int(numero_cuotas)
    
    def clean(self):
        """
        Validación general del formulario.
        """
        cleaned_data = super().clean()
        numero_cuotas = cleaned_data.get('numero_cuotas_pagar')
        
        if numero_cuotas and self.prestamo:
            # Calcular el monto total de las primeras N cuotas
            from .models import PlanPago
            cuotas_pendientes = PlanPago.objects.filter(
                prestamo=self.prestamo,
                estado__in=['Pendiente', 'Vencida', 'Pagada Parcialmente']
            ).order_by('numero_cuota')[:numero_cuotas]
            
            if len(cuotas_pendientes) < numero_cuotas:
                raise ValidationError('No hay suficientes cuotas pendientes para el número seleccionado.')
            
            monto_total = sum(cuota.saldo_pendiente for cuota in cuotas_pendientes)
            
            # Agregar el monto calculado a los datos limpios para usar en la vista
            cleaned_data['monto_calculado'] = monto_total
            cleaned_data['cuotas_a_pagar'] = [cuota.id for cuota in cuotas_pendientes]
        
        return cleaned_data


class PrestamoForm(forms.ModelForm):
    """
    Formulario para crear y editar préstamos.
    """
    
    class Meta:
        model = Préstamo
        fields = ['cliente', 'tasa_interes', 'monto_solicitado', 'numero_cuotas', 
                 'frecuencia_pago', 'fecha_emision', 'fecha_primer_pago', 'garantia_descripcion']
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tasa_interes': forms.Select(attrs={
                'class': 'form-select'
            }),
            'monto_solicitado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'max': '500000.00',
                'placeholder': '0.00'
            }),
            'numero_cuotas': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '120',
                'placeholder': '12'
            }),
            'frecuencia_pago': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha_emision': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'fecha_primer_pago': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'garantia_descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la garantía (opcional)'
            })
        }
        labels = {
            'cliente': 'Cliente',
            'tasa_interes': 'Tasa de Interés',
            'monto_solicitado': 'Monto Solicitado (S/)',
            'numero_cuotas': 'Número de Cuotas',
            'frecuencia_pago': 'Frecuencia de Pago',
            'fecha_emision': 'Fecha de Emisión',
            'fecha_primer_pago': 'Fecha del Primer Pago',
            'garantia_descripcion': 'Descripción de la Garantía'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo clientes activos
        self.fields['cliente'].queryset = Cliente.objects.all().order_by('nombres', 'apellidos')
        
        # Filtrar solo tasas de interés activas
        self.fields['tasa_interes'].queryset = TasaInteres.objects.all().order_by('nombre')
        
        # Hacer garantía opcional
        self.fields['garantia_descripcion'].required = False
        
        # Establecer fechas por defecto
        if not self.instance.pk:  # Solo para nuevos préstamos
            self.fields['fecha_emision'].initial = timezone.now().date()
            # Fecha del primer pago por defecto: un mes después
            from dateutil.relativedelta import relativedelta
            self.fields['fecha_primer_pago'].initial = timezone.now().date() + relativedelta(months=1)
    
    def clean_monto_solicitado(self):
        """
        Validar que el monto sea positivo y razonable.
        """
        monto = self.cleaned_data.get('monto_solicitado')
        
        if monto is not None:
            if monto <= 0:
                raise ValidationError('El monto debe ser mayor a 0.')
            
            # Validar que no exceda 500,000
            if monto > Decimal('500000.00'):
                raise ValidationError('El monto no puede exceder S/ 500,000.00')
            
            # Validar monto mínimo
            if monto < Decimal('100.00'):
                raise ValidationError('El monto mínimo es S/ 100.00')
        
        return monto
    
    def clean_numero_cuotas(self):
        """
        Validar que el número de cuotas sea razonable.
        """
        cuotas = self.cleaned_data.get('numero_cuotas')
        
        if cuotas is not None:
            if cuotas < 1:
                raise ValidationError('El número de cuotas debe ser al menos 1.')
            
            if cuotas > 120:
                raise ValidationError('El número máximo de cuotas es 120.')
        
        return cuotas
    
    def clean_fecha_primer_pago(self):
        """
        Validar que la fecha del primer pago sea posterior a la fecha de emisión.
        """
        fecha_emision = self.cleaned_data.get('fecha_emision')
        fecha_primer_pago = self.cleaned_data.get('fecha_primer_pago')
        
        if fecha_emision and fecha_primer_pago:
            if fecha_primer_pago <= fecha_emision:
                raise ValidationError('La fecha del primer pago debe ser posterior a la fecha de emisión.')
        
        return fecha_primer_pago
    
    def clean_garantia_descripcion(self):
        """
        Limpiar y validar la descripción de la garantía.
        """
        garantia = self.cleaned_data.get('garantia_descripcion')
        
        if garantia:
            # Limpiar espacios en blanco
            garantia = garantia.strip()
            
            # Validar longitud
            if len(garantia) > 1000:
                raise ValidationError('La descripción de la garantía no puede exceder 1000 caracteres.')
        
        return garantia


class MetodoPagoForm(forms.ModelForm):
    """
    Formulario para crear y editar métodos de pago.
    """
    
    class Meta:
        model = MetodoPago
        fields = ['nombre', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Transferencia Bancaria, Yape, Plin, etc.'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'nombre': 'Nombre del Método de Pago',
            'activo': '¿Está activo?'
        }
    
    def clean_nombre(self):
        """
        Limpiar y validar el nombre del método de pago.
        """
        nombre = self.cleaned_data.get('nombre')
        
        if nombre:
            # Limpiar espacios en blanco y capitalizar
            nombre = ' '.join(nombre.strip().split())
            nombre = nombre.title()
            
            # Validar longitud
            if len(nombre) > 100:
                raise ValidationError('El nombre no puede exceder 100 caracteres.')
            
            # Verificar unicidad (excluyendo la instancia actual si estamos editando)
            queryset = MetodoPago.objects.filter(nombre=nombre)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('Ya existe un método de pago con este nombre.')
        
        return nombre