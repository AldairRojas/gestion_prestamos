from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import Usuario, Perfil

class UsuarioForm(UserChangeForm):
    """
    Formulario para editar el perfil del usuario.
    """
    
    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'email', 'perfil']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'perfil': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'nombre_completo': 'Nombre Completo',
            'email': 'Correo Electrónico',
            'perfil': 'Perfil de Usuario'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que el email sea de solo lectura
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['email'].help_text = 'El correo electrónico no se puede cambiar.'
        
        # Filtrar solo perfiles activos
        self.fields['perfil'].queryset = Perfil.objects.all().order_by('nombre')
