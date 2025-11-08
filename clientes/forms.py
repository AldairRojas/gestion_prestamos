from django import forms
from django.core.exceptions import ValidationError
from .models import Cliente, TipoDocumento, Direccion


class ClienteForm(forms.ModelForm):
    """
    Formulario para crear y editar clientes.
    """
    
    class Meta:
        model = Cliente
        fields = ['tipo_documento', 'numero_documento', 'nombres', 'apellidos', 'email', 'telefono']
        widgets = {
            'tipo_documento': forms.Select(attrs={
                'class': 'form-select'
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento'
            }),
            'nombres': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombres del cliente'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellidos del cliente'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono'
            })
        }
        labels = {
            'tipo_documento': 'Tipo de Documento',
            'numero_documento': 'Número de Documento',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar el queryset para tipo_documento
        self.fields['tipo_documento'].queryset = TipoDocumento.objects.all().order_by('nombre')
        
        # Hacer email y teléfono opcionales
        self.fields['email'].required = False
        self.fields['telefono'].required = False
    
    def clean_numero_documento(self):
        """
        Validar que el número de documento sea único.
        """
        numero_doc = self.cleaned_data.get('numero_documento')
        
        if numero_doc:
            # Limpiar espacios en blanco
            numero_doc = numero_doc.strip()
            
            # Verificar unicidad (excluyendo la instancia actual si estamos editando)
            queryset = Cliente.objects.filter(numero_documento=numero_doc)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('Ya existe un cliente con este número de documento.')
            
            # Validar longitud
            if len(numero_doc) > 20:
                raise ValidationError('El número de documento no puede exceder 20 caracteres.')
        
        return numero_doc
    
    def clean_email(self):
        """
        Validar que el email sea único si se proporciona.
        """
        email = self.cleaned_data.get('email')
        
        if email:
            # Limpiar espacios en blanco
            email = email.strip().lower()
            
            # Verificar unicidad (excluyendo la instancia actual si estamos editando)
            queryset = Cliente.objects.filter(email=email)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('Ya existe un cliente con este correo electrónico.')
        
        return email
    
    def clean_nombres(self):
        """
        Limpiar y validar los nombres.
        """
        nombres = self.cleaned_data.get('nombres')
        
        if nombres:
            # Limpiar espacios en blanco y capitalizar
            nombres = ' '.join(nombres.strip().split())
            nombres = nombres.title()
            
            # Validar longitud
            if len(nombres) > 200:
                raise ValidationError('Los nombres no pueden exceder 200 caracteres.')
        
        return nombres
    
    def clean_apellidos(self):
        """
        Limpiar y validar los apellidos.
        """
        apellidos = self.cleaned_data.get('apellidos')
        
        if apellidos:
            # Limpiar espacios en blanco y capitalizar
            apellidos = ' '.join(apellidos.strip().split())
            apellidos = apellidos.title()
            
            # Validar longitud
            if len(apellidos) > 200:
                raise ValidationError('Los apellidos no pueden exceder 200 caracteres.')
        
        return apellidos
    
    def clean_telefono(self):
        """
        Limpiar y validar el teléfono.
        """
        telefono = self.cleaned_data.get('telefono')
        
        if telefono:
            # Limpiar espacios en blanco
            telefono = telefono.strip()
            
            # Validar que solo contenga números, espacios, +, -, (, )
            import re
            if not re.match(r'^[\d\s\+\-\(\)]+$', telefono):
                raise ValidationError('El teléfono solo puede contener números, espacios, +, -, ( y ).')
            
            # Validar longitud
            if len(telefono) > 20:
                raise ValidationError('El teléfono no puede exceder 20 caracteres.')
        
        return telefono


class DireccionForm(forms.ModelForm):
    """
    Formulario para agregar direcciones a clientes.
    """
    
    class Meta:
        model = Direccion
        fields = ['direccion_linea_1', 'distrito', 'ciudad', 'es_principal']
        widgets = {
            'direccion_linea_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección completa'
            }),
            'distrito': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Distrito'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'es_principal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'direccion_linea_1': 'Dirección',
            'distrito': 'Distrito',
            'ciudad': 'Ciudad',
            'es_principal': '¿Es dirección principal?'
        }
    
    def clean_direccion_linea_1(self):
        """
        Limpiar y validar la dirección.
        """
        direccion = self.cleaned_data.get('direccion_linea_1')
        
        if direccion:
            # Limpiar espacios en blanco
            direccion = ' '.join(direccion.strip().split())
            
            # Validar longitud
            if len(direccion) > 255:
                raise ValidationError('La dirección no puede exceder 255 caracteres.')
        
        return direccion
    
    def clean_distrito(self):
        """
        Limpiar y validar el distrito.
        """
        distrito = self.cleaned_data.get('distrito')
        
        if distrito:
            # Limpiar espacios en blanco y capitalizar
            distrito = ' '.join(distrito.strip().split())
            distrito = distrito.title()
            
            # Validar longitud
            if len(distrito) > 100:
                raise ValidationError('El distrito no puede exceder 100 caracteres.')
        
        return distrito
    
    def clean_ciudad(self):
        """
        Limpiar y validar la ciudad.
        """
        ciudad = self.cleaned_data.get('ciudad')
        
        if ciudad:
            # Limpiar espacios en blanco y capitalizar
            ciudad = ' '.join(ciudad.strip().split())
            ciudad = ciudad.title()
            
            # Validar longitud
            if len(ciudad) > 100:
                raise ValidationError('La ciudad no puede exceder 100 caracteres.')
        
        return ciudad


class TipoDocumentoForm(forms.ModelForm):
    """
    Formulario para crear y editar tipos de documento.
    """
    
    class Meta:
        model = TipoDocumento
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: DNI, RUC, Pasaporte, etc.'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del tipo de documento'
            })
        }
        labels = {
            'nombre': 'Nombre del Tipo de Documento',
            'descripcion': 'Descripción'
        }
    
    def clean_nombre(self):
        """
        Limpiar y validar el nombre del tipo de documento.
        """
        nombre = self.cleaned_data.get('nombre')
        
        if nombre:
            # Limpiar espacios en blanco y capitalizar
            nombre = ' '.join(nombre.strip().split())
            nombre = nombre.title()
            
            # Validar longitud
            if len(nombre) > 50:
                raise ValidationError('El nombre no puede exceder 50 caracteres.')
            
            # Verificar unicidad (excluyendo la instancia actual si estamos editando)
            queryset = TipoDocumento.objects.filter(nombre=nombre)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('Ya existe un tipo de documento con este nombre.')
        
        return nombre
    
    def clean_descripcion(self):
        """
        Limpiar y validar la descripción.
        """
        descripcion = self.cleaned_data.get('descripcion')
        
        if descripcion:
            # Limpiar espacios en blanco
            descripcion = descripcion.strip()
            
            # Validar longitud
            if len(descripcion) > 255:
                raise ValidationError('La descripción no puede exceder 255 caracteres.')
        
        return descripcion