from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
from .models import Préstamo, Pago, MetodoPago, PlanPago
from .forms import PagoForm, PrestamoForm, MetodoPagoForm
from clientes.models import Cliente
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
def dashboard(request):
    """
    Dashboard principal del sistema con estadísticas y resumen.
    """
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Estadísticas generales
    total_prestamos = Préstamo.objects.count()
    prestamos_activos = Préstamo.objects.filter(estado='Activo').count()
    prestamos_pagados = Préstamo.objects.filter(estado='Pagado').count()
    total_clientes = Cliente.objects.count()
    
    # Montos
    monto_total_prestado = Préstamo.objects.aggregate(
        total=Sum('monto_solicitado')
    )['total'] or 0
    
    monto_total_pagado = Pago.objects.aggregate(
        total=Sum('monto_pagado')
    )['total'] or 0
    
    # Préstamos recientes
    prestamos_recientes = Préstamo.objects.select_related('cliente', 'tasa_interes').order_by('-fecha_creacion')[:5]
    
    # Pagos recientes
    pagos_recientes = Pago.objects.select_related('prestamo', 'metodo_pago').order_by('-fecha_pago')[:5]
    
    # Estadísticas por mes (últimos 6 meses)
    meses_stats = []
    for i in range(6):
        fecha = timezone.now() - timedelta(days=30*i)
        mes_prestamos = Préstamo.objects.filter(
            fecha_creacion__year=fecha.year,
            fecha_creacion__month=fecha.month
        ).count()
        mes_pagos = Pago.objects.filter(
            fecha_pago__year=fecha.year,
            fecha_pago__month=fecha.month
        ).count()
        
        meses_stats.append({
            'mes': fecha.strftime('%b %Y'),
            'prestamos': mes_prestamos,
            'pagos': mes_pagos
        })
    
    meses_stats.reverse()  # Mostrar del más antiguo al más reciente
    
    context = {
        'titulo_pagina': 'Dashboard',
        'total_prestamos': total_prestamos,
        'prestamos_activos': prestamos_activos,
        'prestamos_pagados': prestamos_pagados,
        'total_clientes': total_clientes,
        'monto_total_prestado': monto_total_prestado,
        'monto_total_pagado': monto_total_pagado,
        'prestamos_recientes': prestamos_recientes,
        'pagos_recientes': pagos_recientes,
        'meses_stats': meses_stats,
    }
    
    return render(request, 'prestamos/dashboard.html', context)

@login_required # Protege la vista, requiere que el usuario esté logueado
def lista_prestamos(request):
    """
    Muestra una lista paginada de todos los préstamos con filtro de búsqueda.
    """
    # Obtener parámetros de búsqueda
    query = request.GET.get('q')
    
    # Optimizamos cargando el cliente relacionado en la misma consulta
    prestamos_list = Préstamo.objects.select_related('cliente', 'tasa_interes').order_by('-fecha_emision')
    
    # Aplicar filtro de búsqueda si existe
    if query:
        prestamos_list = prestamos_list.filter(
            models.Q(cliente__nombres__icontains=query) |
            models.Q(cliente__apellidos__icontains=query) |
            models.Q(cliente__numero_documento__icontains=query) |
            models.Q(id__icontains=query)
        )
    
    # Configurar paginación
    paginator = Paginator(prestamos_list, 15)  # Mostrar 15 préstamos por página
    page = request.GET.get('page')
    
    try:
        prestamos = paginator.page(page)
    except PageNotAnInteger:
        # Si la página no es un entero, entregar la primera página
        prestamos = paginator.page(1)
    except EmptyPage:
        # Si la página está fuera de rango, entregar la última página
        prestamos = paginator.page(paginator.num_pages)
    
    context = {
        'prestamos': prestamos,
        'query': query,
        'titulo_pagina': 'Lista de Préstamos'
    }
    return render(request, 'prestamos/lista_prestamos.html', context)

@login_required # Protege también la vista de detalle
def detalle_prestamo(request, pk):
    """
    Muestra los detalles de un préstamo específico, incluyendo su plan de pagos.
    'pk' es la llave primaria (el UUID del préstamo) que viene de la URL.
    """
    # Usamos get_object_or_404 para manejar el caso de que el ID no exista
    # select_related('cliente', 'tasa_interes', 'creado_por') optimiza la carga de objetos relacionados (uno a uno o muchos a uno)
    # prefetch_related('plan_pagos') optimiza la carga de todas las cuotas asociadas (uno a muchos o muchos a muchos)
    prestamo = get_object_or_404(
        Préstamo.objects.select_related('cliente', 'tasa_interes', 'creado_por')
                         .prefetch_related('plan_pagos'), # Carga el plan de pagos eficientemente
        pk=pk
    )

    # Calcular estadísticas del préstamo
    cuotas = prestamo.plan_pagos.all()
    cuotas_pagadas = cuotas.filter(estado='Pagada').count()
    total_pagado = sum(cuota.monto_pagado for cuota in cuotas)
    saldo_pendiente = prestamo.monto_total_pagar - total_pagado
    
    # Pasamos el objeto 'prestamo' (que ahora incluye el plan de pagos) a la plantilla
    context = {
        'prestamo': prestamo,
        'cuotas_pagadas': cuotas_pagadas,
        'total_pagado': total_pagado,
        'saldo_pendiente': saldo_pendiente,
        'titulo_pagina': f"Detalle Préstamo ...{str(prestamo.id)[:8]}" # Título para base.html
        }
    return render(request, 'prestamos/detalle_prestamo.html', context)

@login_required
def registrar_pago(request, pk):
    """
    Permite registrar un pago para un préstamo específico.
    """
    prestamo = get_object_or_404(
        Préstamo.objects.select_related('cliente', 'tasa_interes'),
        pk=pk
    )
    
    # Verificar que el préstamo esté activo
    if prestamo.estado != 'Activo':
        messages.error(request, f'No se pueden registrar pagos para préstamos en estado: {prestamo.get_estado_display()}')
        return redirect('prestamos:detalle_prestamo', pk=prestamo.id)
    
    if request.method == 'POST':
        form = PagoForm(request.POST, prestamo=prestamo)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Obtener las cuotas seleccionadas y calcular el monto total
                    cuotas_seleccionadas = form.cleaned_data['cuotas_a_pagar']
                    monto_total = form.cleaned_data['monto_calculado']
                    metodo_pago = form.cleaned_data['metodo_pago']
                    referencia = form.cleaned_data.get('referencia', '')
                    
                    # Crear el pago con fecha automática
                    pago = Pago.objects.create(
                        prestamo=prestamo,
                        monto_pagado=monto_total,
                        metodo_pago=metodo_pago,
                        referencia=referencia,
                        registrado_por=request.user,
                        fecha_pago=timezone.now()  # Fecha automática
                    )
                    
                    # Marcar las cuotas seleccionadas como pagadas
                    PlanPago.objects.filter(
                        id__in=cuotas_seleccionadas,
                        prestamo=prestamo
                    ).update(
                        estado='Pagada',
                        monto_pagado=models.F('monto_total_cuota'),
                        saldo_pendiente=0
                    )
                    
                    # Verificar si el préstamo está completamente pagado
                    cuotas_pendientes = PlanPago.objects.filter(
                        prestamo=prestamo
                    ).exclude(estado='Pagada').exists()
                    
                    if not cuotas_pendientes:
                        # Actualizar el estado del préstamo a 'Pagado'
                        Préstamo.objects.filter(pk=prestamo.pk).update(estado='Pagado')
                    
                    messages.success(request, f'Pago de S/ {monto_total:.2f} registrado exitosamente.')
                    return redirect('prestamos:detalle_prestamo', pk=prestamo.id)
                    
            except Exception as e:
                messages.error(request, f'Error al registrar el pago: {str(e)}')
    else:
        form = PagoForm(prestamo=prestamo)
    
    # Obtener información del préstamo para mostrar en el contexto
    cuotas_pendientes = PlanPago.objects.filter(
        prestamo=prestamo,
        estado__in=['Pendiente', 'Vencida', 'Pagada Parcialmente']
    ).order_by('numero_cuota')
    
    # Calcular total pendiente
    total_pendiente = sum(cuota.saldo_pendiente for cuota in cuotas_pendientes)
    
    context = {
        'prestamo': prestamo,
        'form': form,
        'cuotas_pendientes': cuotas_pendientes,
        'total_pendiente': total_pendiente,
        'titulo_pagina': f'Registrar Pago - Préstamo ...{str(prestamo.id)[:8]}'
    }
    
    return render(request, 'prestamos/registrar_pago.html', context)


@login_required
def crear_prestamo(request):
    """
    Permite crear un nuevo préstamo.
    """
    if request.method == 'POST':
        form = PrestamoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear el préstamo
                    prestamo = form.save(commit=False)
                    prestamo.creado_por = request.user
                    prestamo.save()
                    
                    messages.success(request, f'Préstamo de S/ {prestamo.monto_solicitado} creado exitosamente para {prestamo.cliente.nombre_completo}.')
                    return redirect('prestamos:detalle_prestamo', pk=prestamo.id)
                    
            except Exception as e:
                messages.error(request, f'Error al crear el préstamo: {str(e)}')
    else:
        form = PrestamoForm()
    
    context = {
        'form': form,
        'titulo_pagina': 'Crear Nuevo Préstamo'
    }
    
    return render(request, 'prestamos/crear_prestamo.html', context)


@login_required
def reportes(request):
    """
    Vista para mostrar reportes básicos del sistema.
    """
    from django.db.models import Sum, Count, Avg
    from datetime import datetime, timedelta
    
    # Estadísticas generales
    total_prestamos = Préstamo.objects.count()
    prestamos_activos = Préstamo.objects.filter(estado='Activo').count()
    prestamos_vencidos = Préstamo.objects.filter(estado='En Atraso').count()
    
    # Montos
    monto_total_prestado = Préstamo.objects.aggregate(
        total=Sum('monto_solicitado')
    )['total'] or 0
    
    monto_total_pagado = Pago.objects.aggregate(
        total=Sum('monto_pagado')
    )['total'] or 0
    
    # Préstamos por estado
    prestamos_por_estado = Préstamo.objects.values('estado').annotate(
        cantidad=Count('id'),
        monto_total=Sum('monto_solicitado')
    ).order_by('estado')
    
    # Top 5 clientes con más préstamos
    top_clientes = Cliente.objects.annotate(
        total_prestamos=Count('prestamos'),
        monto_total=Sum('prestamos__monto_solicitado')
    ).order_by('-total_prestamos')[:5]
    
    # Préstamos por mes (últimos 6 meses)
    meses_stats = []
    for i in range(6):
        fecha = timezone.now() - timedelta(days=30*i)
        mes_prestamos = Préstamo.objects.filter(
            fecha_creacion__year=fecha.year,
            fecha_creacion__month=fecha.month
        ).count()
        mes_monto = Préstamo.objects.filter(
            fecha_creacion__year=fecha.year,
            fecha_creacion__month=fecha.month
        ).aggregate(total=Sum('monto_solicitado'))['total'] or 0
        
        meses_stats.append({
            'mes': fecha.strftime('%b %Y'),
            'prestamos': mes_prestamos,
            'monto': mes_monto
        })
    
    meses_stats.reverse()
    
    context = {
        'titulo_pagina': 'Reportes del Sistema',
        'total_prestamos': total_prestamos,
        'prestamos_activos': prestamos_activos,
        'prestamos_vencidos': prestamos_vencidos,
        'monto_total_prestado': monto_total_prestado,
        'monto_total_pagado': monto_total_pagado,
        'prestamos_por_estado': prestamos_por_estado,
        'top_clientes': top_clientes,
        'meses_stats': meses_stats,
    }
    
    return render(request, 'prestamos/reportes.html', context)


@login_required
def lista_metodos_pago(request):
    metodos = MetodoPago.objects.all().order_by('-fecha_creacion')
    
    context = {
        'metodos': metodos,
        'titulo_pagina': 'Métodos de Pago'
    }
    
    return render(request, 'prestamos/lista_metodos_pago.html', context)


@login_required
def crear_metodo_pago(request):
    """
    Permite crear un nuevo método de pago.
    """
    if request.method == 'POST':
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            try:
                metodo = form.save()
                messages.success(request, f'Método de pago "{metodo.nombre}" creado exitosamente.')
                return redirect('prestamos:lista_metodos_pago')
            except Exception as e:
                messages.error(request, f'Error al crear el método de pago: {str(e)}')
    else:
        form = MetodoPagoForm()
    
    context = {
        'form': form,
        'titulo_pagina': 'Crear Nuevo Método de Pago'
    }
    
    return render(request, 'prestamos/crear_metodo_pago.html', context)


@login_required
def editar_metodo_pago(request, pk):
    """
    Permite editar un método de pago existente.
    """
    metodo = get_object_or_404(MetodoPago, pk=pk)
    
    if request.method == 'POST':
        form = MetodoPagoForm(request.POST, instance=metodo)
        if form.is_valid():
            try:
                metodo = form.save()
                messages.success(request, f'Método de pago "{metodo.nombre}" actualizado exitosamente.')
                return redirect('prestamos:lista_metodos_pago')
            except Exception as e:
                messages.error(request, f'Error al actualizar el método de pago: {str(e)}')
    else:
        form = MetodoPagoForm(instance=metodo)
    
    context = {
        'form': form,
        'metodo': metodo,
        'titulo_pagina': f'Editar Método de Pago - {metodo.nombre}'
    }
    
    return render(request, 'prestamos/editar_metodo_pago.html', context)


@login_required
def eliminar_metodo_pago(request, pk):
    """
    Permite eliminar un método de pago.
    """
    metodo = get_object_or_404(MetodoPago, pk=pk)
    
    # Verificar si el método está siendo usado en algún pago
    pagos_con_metodo = Pago.objects.filter(metodo_pago=metodo).count()
    
    if request.method == 'POST':
        try:
            nombre_metodo = metodo.nombre
            metodo.delete()
            messages.success(request, f'Método de pago "{nombre_metodo}" eliminado exitosamente.')
            return redirect('prestamos:lista_metodos_pago')
        except Exception as e:
            messages.error(request, f'Error al eliminar el método de pago: {str(e)}')
    
    context = {
        'metodo': metodo,
        'pagos_con_metodo': pagos_con_metodo,
        'titulo_pagina': f'Eliminar Método de Pago - {metodo.nombre}'
    }
    
    return render(request, 'prestamos/eliminar_metodo_pago.html', context)