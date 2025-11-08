from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from .models import Préstamo, Pago, MetodoPago, PlanPago, TasaInteres
from .forms import PagoForm, PrestamoForm, MetodoPagoForm, TasaInteresForm
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
    
    # Calcular saldo pendiente total sumando los saldos pendientes de todas las cuotas
    from .models import PlanPago
    saldo_pendiente_total = PlanPago.objects.aggregate(
        total=Sum('saldo_pendiente')
    )['total'] or 0
    
    context = {
        'titulo_pagina': 'Dashboard',
        'total_prestamos': total_prestamos,
        'prestamos_activos': prestamos_activos,
        'prestamos_pagados': prestamos_pagados,
        'total_clientes': total_clientes,
        'monto_total_prestado': monto_total_prestado,
        'monto_total_pagado': monto_total_pagado,
        'saldo_pendiente_total': saldo_pendiente_total,
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
    # El saldo pendiente debe calcularse sumando los saldos pendientes de cada cuota
    # (ya que los montos pueden haber cambiado por pagos anticipados con intereses reducidos)
    saldo_pendiente = sum(cuota.saldo_pendiente for cuota in cuotas)
    # Calcular intereses reales pagados (pueden ser menores si hubo pagos anticipados)
    total_intereses_real = sum(cuota.monto_interes for cuota in cuotas)
    # Calcular monto total real a pagar (sumando el monto_total_cuota de cada cuota)
    monto_total_real = sum(cuota.monto_total_cuota for cuota in cuotas)
    
    # Pasamos el objeto 'prestamo' (que ahora incluye el plan de pagos) a la plantilla
    context = {
        'prestamo': prestamo,
        'cuotas_pagadas': cuotas_pagadas,
        'total_pagado': total_pagado,
        'saldo_pendiente': saldo_pendiente,
        'total_intereses_real': total_intereses_real,
        'monto_total_real': monto_total_real,
        'titulo_pagina': f"Detalle Préstamo #{prestamo.numero_prestamo}" # Título para base.html
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
                    # El método save() del modelo Pago manejará automáticamente:
                    # - La distribución del monto entre las cuotas
                    # - La aplicación de la ley peruana (intereses proporcionales en pagos anticipados)
                    # Establecemos los IDs de cuotas como atributo temporal antes de crear el pago
                    pago = Pago(
                        prestamo=prestamo,
                        monto_pagado=monto_total,
                        metodo_pago=metodo_pago,
                        referencia=referencia,
                        registrado_por=request.user,
                        fecha_pago=timezone.now()  # Fecha automática
                    )
                    # Establecer los IDs de cuotas como atributo temporal para que save() los use
                    pago._cuotas_ids = cuotas_seleccionadas
                    # Guardar el pago - save() leerá _cuotas_ids y distribuirá solo entre esas cuotas
                    pago.save()
                    
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
        'titulo_pagina': f'Registrar Pago - Préstamo #{prestamo.numero_prestamo}'
    }
    
    return render(request, 'prestamos/registrar_pago.html', context)


@login_required
def crear_prestamo(request):
    """
    Permite crear un nuevo préstamo con vista previa del plan de pagos.
    """
    # Verificar si estamos en el paso de confirmación
    if request.method == 'POST' and 'confirmar' in request.POST:
        # Si viene del formulario de confirmación, crear el préstamo
        # Recuperamos los datos del formulario original desde la sesión
        if 'prestamo_data' in request.session:
            try:
                from datetime import date
                prestamo_data = request.session['prestamo_data']
                with transaction.atomic():
                    # Convertir strings ISO de vuelta a objetos date
                    fecha_emision = date.fromisoformat(prestamo_data['fecha_emision']) if isinstance(prestamo_data['fecha_emision'], str) else prestamo_data['fecha_emision']
                    fecha_primer_pago = date.fromisoformat(prestamo_data['fecha_primer_pago']) if isinstance(prestamo_data['fecha_primer_pago'], str) else prestamo_data['fecha_primer_pago']
                    
                    # Crear el préstamo con los datos guardados
                    from .models import Préstamo
                    prestamo = Préstamo.objects.create(
                        cliente_id=prestamo_data['cliente_id'],
                        tasa_interes_id=prestamo_data['tasa_interes_id'],
                        monto_solicitado=Decimal(str(prestamo_data['monto_solicitado'])),
                        numero_cuotas=prestamo_data['numero_cuotas'],
                        frecuencia_pago=prestamo_data['frecuencia_pago'],
                        fecha_emision=fecha_emision,
                        fecha_primer_pago=fecha_primer_pago,
                        garantia_descripcion=prestamo_data.get('garantia_descripcion', ''),
                        creado_por=request.user
                    )
                    
                    # Limpiar la sesión
                    del request.session['prestamo_data']
                    
                    messages.success(request, f'Préstamo de S/ {prestamo.monto_solicitado:.2f} creado exitosamente para {prestamo.cliente.nombre_completo}.')
                    return redirect('prestamos:detalle_prestamo', pk=prestamo.id)
                    
            except Exception as e:
                messages.error(request, f'Error al crear el préstamo: {str(e)}')
        else:
            messages.error(request, 'Error: No se encontraron los datos del préstamo.')
            return redirect('prestamos:crear_prestamo')
    
    # Verificar si estamos en el paso de vista previa
    elif request.method == 'POST' and 'preview' in request.POST:
        form = PrestamoForm(request.POST)
        if form.is_valid():
            # Guardamos los datos en la sesión para confirmar después
            # Convertir fechas a strings ISO para evitar problemas de serialización JSON
            from datetime import date
            fecha_emision = form.cleaned_data['fecha_emision']
            fecha_primer_pago = form.cleaned_data['fecha_primer_pago']
            
            prestamo_data = {
                'cliente_id': form.cleaned_data['cliente'].id,
                'tasa_interes_id': form.cleaned_data['tasa_interes'].id,
                'monto_solicitado': float(form.cleaned_data['monto_solicitado']),
                'numero_cuotas': form.cleaned_data['numero_cuotas'],
                'frecuencia_pago': form.cleaned_data['frecuencia_pago'],
                'fecha_emision': fecha_emision.isoformat() if isinstance(fecha_emision, date) else str(fecha_emision),
                'fecha_primer_pago': fecha_primer_pago.isoformat() if isinstance(fecha_primer_pago, date) else str(fecha_primer_pago),
                'garantia_descripcion': form.cleaned_data.get('garantia_descripcion', ''),
            }
            request.session['prestamo_data'] = prestamo_data
            
            # Calcular el plan de pagos para mostrar en vista previa
            from .models import TasaInteres
            from dateutil.relativedelta import relativedelta
            
            tasa_interes = form.cleaned_data['tasa_interes']
            monto_solicitado = form.cleaned_data['monto_solicitado']
            numero_cuotas = form.cleaned_data['numero_cuotas']
            frecuencia_pago = form.cleaned_data['frecuencia_pago']
            fecha_primer_pago = form.cleaned_data['fecha_primer_pago']
            
            # Calcular intereses y totales
            if tasa_interes.tipo_tasa == 'Simple':
                tasa_porcentaje = tasa_interes.valor_porcentaje / Decimal('100')
                
                # Ajustar la tasa según el período
                if tasa_interes.periodo == 'Anual':
                    if frecuencia_pago == 'Mensual':
                        tasa_ajustada = tasa_porcentaje / Decimal('12')
                    elif frecuencia_pago == 'Quincenal':
                        tasa_ajustada = tasa_porcentaje / Decimal('24')
                    elif frecuencia_pago == 'Semanal':
                        tasa_ajustada = tasa_porcentaje / Decimal('52')
                    else:
                        tasa_ajustada = tasa_porcentaje
                elif tasa_interes.periodo == 'Mensual':
                    if frecuencia_pago == 'Quincenal':
                        tasa_ajustada = tasa_porcentaje / Decimal('2')
                    elif frecuencia_pago == 'Semanal':
                        tasa_ajustada = tasa_porcentaje / Decimal('4')
                    else:
                        tasa_ajustada = tasa_porcentaje
                else:
                    tasa_ajustada = tasa_porcentaje
                
                # Calcular interés por cuota
                interes_por_cuota = (monto_solicitado * tasa_ajustada).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                monto_total_interes = interes_por_cuota * numero_cuotas
                monto_total_pagar = monto_solicitado + monto_total_interes
                
                # Generar plan de pagos
                from .models import PlanPago
                capital_por_cuota = (monto_solicitado / numero_cuotas).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                plan_pagos = []
                
                fecha_cuota = fecha_primer_pago
                total_capital_asignado = Decimal('0.00')
                total_interes_asignado = Decimal('0.00')
                
                for i in range(1, numero_cuotas + 1):
                    if i == numero_cuotas:
                        capital_cuota = monto_solicitado - total_capital_asignado
                        interes_cuota = monto_total_interes - total_interes_asignado
                    else:
                        capital_cuota = capital_por_cuota
                        interes_cuota = interes_por_cuota
                        total_capital_asignado += capital_cuota
                        total_interes_asignado += interes_cuota
                    
                    total_cuota = capital_cuota + interes_cuota
                    plan_pagos.append({
                        'numero_cuota': i,
                        'fecha_vencimiento': fecha_cuota,
                        'capital': capital_cuota,
                        'interes': interes_cuota,
                        'total': total_cuota
                    })
                    
                    # Calcular siguiente fecha
                    if frecuencia_pago == 'Mensual':
                        fecha_cuota += relativedelta(months=1)
                    elif frecuencia_pago == 'Quincenal':
                        fecha_cuota += relativedelta(weeks=2)
                    elif frecuencia_pago == 'Semanal':
                        fecha_cuota += relativedelta(weeks=1)
            
            context = {
                'form': form,
                'plan_pagos': plan_pagos,
                'monto_solicitado': monto_solicitado,
                'monto_total_interes': monto_total_interes,
                'monto_total_pagar': monto_total_pagar,
                'numero_cuotas': numero_cuotas,
                'titulo_pagina': 'Vista Previa - Plan de Pagos'
            }
            
            return render(request, 'prestamos/vista_previa_prestamo.html', context)
    
    # Paso inicial: mostrar formulario
    elif request.method == 'POST':
        form = PrestamoForm(request.POST)
        if not form.is_valid():
            context = {
                'form': form,
                'titulo_pagina': 'Crear Nuevo Préstamo'
            }
            return render(request, 'prestamos/crear_prestamo.html', context)
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
    
    # Calcular saldo pendiente total sumando los saldos pendientes de todas las cuotas
    from .models import PlanPago
    saldo_pendiente_total = PlanPago.objects.aggregate(
        total=Sum('saldo_pendiente')
    )['total'] or 0
    
    # Calcular intereses reales pagados sumando los intereses de todas las cuotas
    total_intereses_real = PlanPago.objects.aggregate(
        total=Sum('monto_interes')
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
        'saldo_pendiente_total': saldo_pendiente_total,
        'total_intereses_real': total_intereses_real,
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


# ===== VISTAS PARA GESTIÓN DE TASAS DE INTERÉS =====

@login_required
def lista_tasas_interes(request):
    """
    Muestra una lista de todas las tasas de interés.
    """
    tasas = TasaInteres.objects.all().order_by('nombre')
    
    context = {
        'tasas': tasas,
        'titulo_pagina': 'Tasas de Interés'
    }
    
    return render(request, 'prestamos/lista_tasas_interes.html', context)


@login_required
def crear_tasa_interes(request):
    """
    Permite crear una nueva tasa de interés.
    """
    if request.method == 'POST':
        form = TasaInteresForm(request.POST)
        if form.is_valid():
            try:
                tasa = form.save()
                messages.success(request, f'Tasa de interés "{tasa.nombre}" creada exitosamente.')
                return redirect('prestamos:lista_tasas_interes')
            except Exception as e:
                messages.error(request, f'Error al crear la tasa de interés: {str(e)}')
    else:
        form = TasaInteresForm()
    
    context = {
        'form': form,
        'titulo_pagina': 'Crear Nueva Tasa de Interés'
    }
    
    return render(request, 'prestamos/crear_tasa_interes.html', context)


@login_required
def editar_tasa_interes(request, pk):
    """
    Permite editar una tasa de interés existente.
    """
    tasa = get_object_or_404(TasaInteres, pk=pk)
    
    if request.method == 'POST':
        form = TasaInteresForm(request.POST, instance=tasa)
        if form.is_valid():
            try:
                tasa = form.save()
                messages.success(request, f'Tasa de interés "{tasa.nombre}" actualizada exitosamente.')
                return redirect('prestamos:lista_tasas_interes')
            except Exception as e:
                messages.error(request, f'Error al actualizar la tasa de interés: {str(e)}')
    else:
        form = TasaInteresForm(instance=tasa)
    
    context = {
        'form': form,
        'tasa': tasa,
        'titulo_pagina': f'Editar Tasa de Interés - {tasa.nombre}'
    }
    
    return render(request, 'prestamos/editar_tasa_interes.html', context)


@login_required
def eliminar_tasa_interes(request, pk):
    """
    Permite eliminar una tasa de interés.
    """
    tasa = get_object_or_404(TasaInteres, pk=pk)
    
    # Verificar si la tasa está siendo usada en algún préstamo
    prestamos_con_tasa = Préstamo.objects.filter(tasa_interes=tasa).count()
    
    if request.method == 'POST':
        try:
            nombre_tasa = tasa.nombre
            tasa.delete()
            messages.success(request, f'Tasa de interés "{nombre_tasa}" eliminada exitosamente.')
            return redirect('prestamos:lista_tasas_interes')
        except Exception as e:
            messages.error(request, f'Error al eliminar la tasa de interés: {str(e)}')
    
    context = {
        'tasa': tasa,
        'prestamos_con_tasa': prestamos_con_tasa,
        'titulo_pagina': f'Eliminar Tasa de Interés - {tasa.nombre}'
    }
    
    return render(request, 'prestamos/eliminar_tasa_interes.html', context)