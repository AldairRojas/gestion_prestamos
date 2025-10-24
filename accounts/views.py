from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UsuarioForm

@login_required
def perfil_usuario(request):
    """
    Vista para mostrar y editar el perfil del usuario.
    """
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('accounts:perfil')
    else:
        form = UsuarioForm(instance=request.user)
    
    context = {
        'form': form,
        'titulo_pagina': 'Mi Perfil'
    }
    
    return render(request, 'accounts/perfil.html', context)

@login_required
def cambiar_password(request):
    """
    Vista para cambiar la contraseña del usuario.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Importante para mantener la sesión
            messages.success(request, 'Contraseña actualizada exitosamente.')
            return redirect('accounts:perfil')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'titulo_pagina': 'Cambiar Contraseña'
    }
    
    return render(request, 'accounts/cambiar_password.html', context)
