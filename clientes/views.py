from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Cliente, TipoDocumento, Direccion
from .forms import ClienteForm, DireccionForm, TipoDocumentoForm


@login_required
def lista_clientes(request):
    """
    Muestra una lista de todos los clientes con búsqueda y filtros.
    """
    clientes_list = Cliente.objects.select_related('tipo_documento').prefetch_related('direcciones').order_by('-fecha_creacion')
    
    # Búsqueda
    query = request.GET.get('q')
    if query:
        clientes_list = clientes_list.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(numero_documento__icontains=query) |
            Q(email__icontains=query)
        )
    
    # Filtro por tipo de documento
    tipo_doc = request.GET.get('tipo_documento')
    if tipo_doc and tipo_doc != '':
        try:
            clientes_list = clientes_list.filter(tipo_documento_id=int(tipo_doc))
        except (ValueError, TypeError):
            # Si el valor no es un entero válido, ignorar el filtro
            pass
    
    # Obtener tipos de documento para el filtro
    tipos_documento = TipoDocumento.objects.all()
    
    context = {
        'clientes': clientes_list,
        'tipos_documento': tipos_documento,
        'query': query,
        'tipo_doc_selected': int(tipo_doc) if tipo_doc and tipo_doc != '' else None,
        'titulo_pagina': 'Lista de Clientes'
    }
    
    return render(request, 'clientes/lista_clientes.html', context)


@login_required
def detalle_cliente(request, pk):
    """
    Muestra los detalles de un cliente específico.
    """
    cliente = get_object_or_404(
        Cliente.objects.select_related('tipo_documento').prefetch_related('direcciones'),
        pk=pk
    )
    
    # Obtener préstamos del cliente
    prestamos = cliente.prestamos.select_related('tasa_interes').order_by('-fecha_emision')[:10]
    
    context = {
        'cliente': cliente,
        'prestamos': prestamos,
        'titulo_pagina': f'Detalle Cliente - {cliente.nombre_completo}'
    }
    
    return render(request, 'clientes/detalle_cliente.html', context)


@login_required
def crear_cliente(request):
    """
    Permite crear un nuevo cliente.
    """
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            try:
                cliente = form.save()
                messages.success(request, f'Cliente {cliente.nombre_completo} creado exitosamente.')
                return redirect('clientes:detalle_cliente', pk=cliente.id)
            except Exception as e:
                messages.error(request, f'Error al crear el cliente: {str(e)}')
    else:
        form = ClienteForm()
    
    context = {
        'form': form,
        'titulo_pagina': 'Crear Nuevo Cliente'
    }
    
    return render(request, 'clientes/crear_cliente.html', context)


@login_required
def editar_cliente(request, pk):
    """
    Permite editar un cliente existente.
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            try:
                cliente = form.save()
                messages.success(request, f'Cliente {cliente.nombre_completo} actualizado exitosamente.')
                return redirect('clientes:detalle_cliente', pk=cliente.id)
            except Exception as e:
                messages.error(request, f'Error al actualizar el cliente: {str(e)}')
    else:
        form = ClienteForm(instance=cliente)
    
    context = {
        'form': form,
        'cliente': cliente,
        'titulo_pagina': f'Editar Cliente - {cliente.nombre_completo}'
    }
    
    return render(request, 'clientes/editar_cliente.html', context)


@login_required
def agregar_direccion(request, cliente_id):
    """
    Permite agregar una nueva dirección a un cliente.
    """
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    
    if request.method == 'POST':
        form = DireccionForm(request.POST)
        if form.is_valid():
            try:
                direccion = form.save(commit=False)
                direccion.cliente = cliente
                direccion.save()
                messages.success(request, 'Dirección agregada exitosamente.')
                return redirect('clientes:detalle_cliente', pk=cliente.id)
            except Exception as e:
                messages.error(request, f'Error al agregar la dirección: {str(e)}')
    else:
        form = DireccionForm()
    
    context = {
        'form': form,
        'cliente': cliente,
        'titulo_pagina': f'Agregar Dirección - {cliente.nombre_completo}'
    }
    
    return render(request, 'clientes/agregar_direccion.html', context)


# ===== VISTAS PARA GESTIÓN DE TIPOS DE DOCUMENTO =====

@login_required
def lista_tipos_documento(request):
    """
    Muestra una lista de todos los tipos de documento.
    """
    tipos_documento = TipoDocumento.objects.all().order_by('nombre')
    
    context = {
        'tipos_documento': tipos_documento,
        'titulo_pagina': 'Tipos de Documento'
    }
    
    return render(request, 'clientes/lista_tipos_documento.html', context)


@login_required
def crear_tipo_documento(request):
    """
    Permite crear un nuevo tipo de documento.
    """
    if request.method == 'POST':
        form = TipoDocumentoForm(request.POST)
        if form.is_valid():
            try:
                tipo_documento = form.save()
                messages.success(request, f'Tipo de documento "{tipo_documento.nombre}" creado exitosamente.')
                return redirect('clientes:lista_tipos_documento')
            except Exception as e:
                messages.error(request, f'Error al crear el tipo de documento: {str(e)}')
    else:
        form = TipoDocumentoForm()
    
    context = {
        'form': form,
        'titulo_pagina': 'Crear Nuevo Tipo de Documento'
    }
    
    return render(request, 'clientes/crear_tipo_documento.html', context)


@login_required
def editar_tipo_documento(request, pk):
    """
    Permite editar un tipo de documento existente.
    """
    tipo_documento = get_object_or_404(TipoDocumento, pk=pk)
    
    if request.method == 'POST':
        form = TipoDocumentoForm(request.POST, instance=tipo_documento)
        if form.is_valid():
            try:
                tipo_documento = form.save()
                messages.success(request, f'Tipo de documento "{tipo_documento.nombre}" actualizado exitosamente.')
                return redirect('clientes:lista_tipos_documento')
            except Exception as e:
                messages.error(request, f'Error al actualizar el tipo de documento: {str(e)}')
    else:
        form = TipoDocumentoForm(instance=tipo_documento)
    
    context = {
        'form': form,
        'tipo_documento': tipo_documento,
        'titulo_pagina': f'Editar Tipo de Documento - {tipo_documento.nombre}'
    }
    
    return render(request, 'clientes/editar_tipo_documento.html', context)


@login_required
def eliminar_tipo_documento(request, pk):
    """
    Permite eliminar un tipo de documento.
    """
    tipo_documento = get_object_or_404(TipoDocumento, pk=pk)
    
    # Verificar si el tipo está siendo usado por algún cliente
    clientes_con_tipo = Cliente.objects.filter(tipo_documento=tipo_documento).count()
    
    if request.method == 'POST':
        try:
            nombre_tipo = tipo_documento.nombre
            tipo_documento.delete()
            messages.success(request, f'Tipo de documento "{nombre_tipo}" eliminado exitosamente.')
            return redirect('clientes:lista_tipos_documento')
        except Exception as e:
            messages.error(request, f'Error al eliminar el tipo de documento: {str(e)}')
    
    context = {
        'tipo_documento': tipo_documento,
        'clientes_con_tipo': clientes_con_tipo,
        'titulo_pagina': f'Eliminar Tipo de Documento - {tipo_documento.nombre}'
    }
    
    return render(request, 'clientes/eliminar_tipo_documento.html', context)


###asdasdasdasdsa###asdasdasdasdsa
###asdasdasdasdsa
###asdasdasdasdsa
###asdasdasdasdsa
###asdasdasdasdsa
###asdasdasdasdsa
