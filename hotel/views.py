from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.utils import timezone
import json 


# ---- MODELS ---- #
from hotel.models import Reservas
from hotel.models import Categorias
from hotel.models import Habitaciones
from hotel.models import Registro_Huespedes
# --------------- #

# ---- FORMS ---- # 
from hotel.forms import ReservarForm
from hotel.forms import CategoriaForm
from hotel.forms import HabitacionForm
from hotel.forms import HuespedForm
# --------------- #

# ---- FACTURA ---- #
from hotel.models import Factura
# ----------------- #

def Dashboard(request):
    return render(request, 'dashboard.html')

#region ------ HABITACIONES ------ #
def ListarHabitaciones(request):
    habitaciones_list = Habitaciones.objects.select_related('tipo').order_by('numero')
    todas_categorias = Categorias.objects.all().order_by('tipo_hab')

    # --- Lógica de Búsqueda ---
    query = request.GET.get('q', '').strip()
    selected_categoria_id = request.GET.get('categoria_id', '').strip()
    status_filter = request.GET.get('status', 'all').strip().lower()

    if query:
        habitaciones_list = habitaciones_list.filter(
            Q(numero__icontains=query) |
            Q(tipo__tipo_hab__icontains=query) |
            Q(estado__icontains=query)
        )

    # --- Filtrado por Categoría ---
    if selected_categoria_id.isdigit():
        habitaciones_list = habitaciones_list.filter(tipo_id=int(selected_categoria_id))

    # --- Lógica de Filtrado por Estado ---
    valid_statuses = [choice[0].lower() for choice in Habitaciones.ESTADO_CHOICES]
    if status_filter != 'all' and status_filter in valid_statuses:
        habitaciones_list = habitaciones_list.filter(estado__iexact=status_filter)
        active_filter = status_filter
    else:
        active_filter = 'all'

    # --- OBTENER RESERVAS ASIGNABLES (CORREGIDO) ---
    # Lógica: Reservas que necesitan habitaciones (num_habt > 0)
    # y que AÚN NO tienen suficientes habitaciones asignadas.
    reservas_asignables = Reservas.objects.annotate(
        num_asignadas=Count('habitaciones_asignadas') # Contar cuántas tienen
    ).filter(
        # ---- ESTA ES LA LÍNEA CORREGIDA ----
        Q(num_habt__gt=F('num_asignadas')) | # Necesita más de las que tiene
        Q(num_habt__isnull=True, num_asignadas=0) # O necesita (implícitamente 1) y no tiene
    ).filter(
        confirmado='Confirmado', # Solo asignar reservas confirmadas
        check_out__gt=timezone.now() # Solo asignar reservas activas o futuras
    ).distinct().order_by('-id')
    
    habitacion_form = HabitacionForm()

    context = {
        'habitaciones': habitaciones_list,
        'reservas_asignables': reservas_asignables,
        'habitacion_form': habitacion_form,
        'todas_categorias': todas_categorias,
        'selected_categoria_id': selected_categoria_id,
        'active_filter': active_filter,
        'search_query': query,
    }
    return render(request, 'habitaciones/listarhabitaciones.html', context)


# --- VISTA AJAX PARA ACTUALIZAR ESTADO/RESERVA (SIMPLIFICADA) ---
def ActualizarHabitacionAJAX(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            habitacion_id = data.get('habitacion_id')
            nuevo_estado = data.get('estado')
            reserva_id_str = data.get('reserva_id')

            if not habitacion_id or not nuevo_estado:
                return JsonResponse({'status': 'error', 'message': 'Faltan datos requeridos.'}, status=400)

            habitacion = get_object_or_404(Habitaciones, pk=habitacion_id)
            reserva_a_asignar = None
            
            # --- VALIDACIÓN Y ASIGNACIÓN ---
            if reserva_id_str: 
                try:
                    # Usamos prefetch_related para cargar las habitaciones ya asignadas a esta reserva
                    reserva_a_asignar = Reservas.objects.prefetch_related('habitaciones_asignadas').get(pk=int(reserva_id_str))
                except (Reservas.DoesNotExist, ValueError):
                    return JsonResponse({'status': 'error', 'message': 'Reserva seleccionada no encontrada.'}, status=404)
            
                # --- VALIDACIÓN 1: LÍMITE (num_habt) ---
                limite = reserva_a_asignar.num_habt if reserva_a_asignar.num_habt is not None and reserva_a_asignar.num_habt > 0 else 1
                asignadas_actualmente = reserva_a_asignar.habitaciones_asignadas.count()
                esta_ya_asignada = habitacion in reserva_a_asignar.habitaciones_asignadas.all()

                if not esta_ya_asignada and asignadas_actualmente >= limite:
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Límite alcanzado. La Reserva #{reserva_a_asignar.id} solo permite {limite} hab. y ya tiene {asignadas_actualmente} asignada(s)."
                    }, status=400)

                # --- VALIDACIÓN 2: CONFLICTO DE FECHAS ---
                nueva_llegada = reserva_a_asignar.check_in
                nueva_salida = reserva_a_asignar.check_out

                reservas_en_conflicto = habitacion.reservas_asignadas.filter(
                    check_in__lt=nueva_salida, 
                    check_out__gt=nueva_llegada
                ).exclude(pk=reserva_a_asignar.id)

                if reservas_en_conflicto.exists():
                    conflicto = reservas_en_conflicto.first()
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Conflicto de fechas. Habitación {habitacion.numero} ya asignada a Reserva #{conflicto.id} ({conflicto.check_in.strftime('%d/%m/%y')} - {conflicto.check_out.strftime('%d/%m/%y')})."
                    }, status=400)
                
                # --- SIN CONFLICTO: ASIGNAR ---
                reserva_a_asignar.habitaciones_asignadas.add(habitacion)
                # Si se asigna una reserva, el estado debe ser 'Ocupada'
                habitacion.estado = 'Ocupada'
            
            # --- LÓGICA DE DESASIGNACIÓN/CAMBIO DE ESTADO ---
            else: # reserva_id_str es "" (Ninguna)
                habitacion.estado = nuevo_estado
                
                if habitacion.estado == 'Disponible' or habitacion.estado == 'Limpieza':
                    # Desasignar de reservas activas/futuras
                    reservas_a_quitar = habitacion.reservas_asignadas.filter(
                        check_out__gt=timezone.now()
                    )
                    for res in reservas_a_quitar:
                        res.habitaciones_asignadas.remove(habitacion)
            
            habitacion.save()

            # Preparamos la respuesta
            response_data = {
                'status': 'ok',
                'nuevo_estado': habitacion.get_estado_display(),
                'reserva_asignada': {
                    'id': reserva_a_asignar.id,
                    'nombre_huesped': f"{reserva_a_asignar.nombre} {reserva_a_asignar.apellido}"
                } if reserva_a_asignar else None
            }
            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Formato de datos inválido.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error interno: {str(e)}'}, status=500)
    else:
        return HttpResponseBadRequest("Método no permitido. Solo POST.")


# --- VISTA AJAX PARA DETALLES DE RESERVA (CONTEO) ---
def GetReservaDetallesAJAX(request, reserva_id):
    if request.method == 'GET':
        try:
            # prefetch_related es mejor para ManyToManyField
            reserva = get_object_or_404(Reservas.objects.prefetch_related('habitaciones_asignadas'), pk=reserva_id) 

            num_necesarias = reserva.num_habt if reserva.num_habt is not None and reserva.num_habt > 0 else 1
            # Contamos las habitaciones REALMENTE asignadas a esta reserva
            num_asignadas = reserva.habitaciones_asignadas.count() # Usamos la relación M2M

            return JsonResponse({
                'status': 'ok',
                'num_necesarias': num_necesarias,
                'num_asignadas': num_asignadas
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return HttpResponseBadRequest("Método no permitido. Solo GET.")

def RegistrarHabitaciones(request):
    if request.method == 'POST':
        form = HabitacionForm(request.POST)
        if form.is_valid():
            try:
                # Validar que el número de habitación no exista ya (si no pusiste unique=True en el modelo)
                numero = form.cleaned_data['numero']
                if Habitaciones.objects.filter(numero=numero).exists():
                    messages.error(request, f"La habitación número '{numero}' ya existe.")
                else:
                    form.save()
                    messages.success(request, f"Habitación '{numero}' guardada con éxito.")
                    # Redirige a la lista de habitaciones (asegúrate que 'habitaciones' es el name= de tu URL)
                    return redirect('habitaciones') 
            except Exception as e:
                messages.error(request, f"Error al guardar la habitación: {e}")
        else:
            # Si el form no es válido, se volverá a renderizar con errores
            messages.error(request, "Por favor corrige los errores en el formulario.")
            
    else: # Método GET
        # Crea una instancia vacía del formulario para mostrarla
        form = HabitacionForm()

    # Pasa el formulario (vacío o con errores) al contexto
    context = {'form': form}
    # Renderiza el template del formulario
    return render(request, 'habitaciones/registrarhabitaciones.html', context)
#endregion

#region ------ RESERVAS ------ #
# En views.py
def Reservar(request):
    
    if request.method == 'POST':
        form = ReservarForm(request.POST)
        
        if form.is_valid():
            # ** Bloque de éxito **
            reservar = form.save()
            messages.success(request, f"Reserva para {reservar.nombre} guardada con éxito.")
            # La redirección debe ser con 'return' para finalizar la vista
            return redirect('reservas') # <--- DEBE HABER UN RETURN AQUÍ
        
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
            
    else:
        # ** Bloque de petición GET (primera carga de la página) **
        form = ReservarForm()
    
    # Renderiza el template. Si el método fue POST y falló, el template recibe 'form' con errores.
    return render(request, 'reservas/reservar.html', {'form': form})


def ListarReservas(request):
    # Obtiene todas las reservas ordenadas por ID descendente (más nuevas primero)
    reservas = Reservas.objects.all().order_by('-id') 
    
    # Prepara el contexto para enviar al template
    context = {
        'reservas': reservas
    }
    
    # Renderiza el template pasándole el contexto
    return render(request, 'reservas/reservas.html', context)


def ConfirmarReserva(request, reserva_id):
    # Solo permitimos POST
    if request.method == 'POST':
        try:
            reserva = get_object_or_404(Reservas, pk=reserva_id)

            # Cambia el estado
            if reserva.confirmado == 'Confirmado':
                reserva.confirmado = 'Pendiente'
            else:
                reserva.confirmado = 'Confirmado'
            
            reserva.save()

            return JsonResponse({'status': 'ok', 'nuevo_estado': reserva.confirmado})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        # Si alguien intenta acceder vía GET, devuelve un error
        return HttpResponseBadRequest("Método no permitido")


def EditarReserva(request, reserva_id): 
    """
    Vista para editar una reserva existente, enfocada en la información de Huésped y Facturación.
    """
    # 1. Obtener la instancia de la reserva
    reserva = get_object_or_404(Reservas, pk=reserva_id)

    if request.method == 'POST':
        # 2. Rellenar el formulario con los datos enviados Y la instancia
        # Usamos ReservarForm para mantener la validación de fechas
        form = ReservarForm(request.POST, instance=reserva) 
        if form.is_valid():
            try:
                # La validación de fechas y campos opcionales ya está en el form
                form.save()
                messages.success(request, f"Reserva #{reserva.id} actualizada con éxito.")
                return redirect('reservas') # Redirigir a la lista
            except Exception as e:
                 messages.error(request, f"Error al actualizar la reserva: {e}")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
            
    else: # Método GET
        # 3. Si es GET, rellenar el formulario solo con la instancia
        form = ReservarForm(instance=reserva)

    context = {
        'form': form,
        'reserva': reserva # Pasamos la reserva por si queremos mostrar el nombre en el título
    }
    
    # 4. Renderiza un template que crearemos: editarreserva.html
    return render(request, 'reservas/editarreserva.html', context)
#endregion

#region ------ CATEGORIAS ------ #
def RegistroCategorias(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Categoría '{form.cleaned_data['tipo_hab']}' guardada con éxito.")
                # Redirigir a alguna página, ej: de vuelta al dashboard o a una lista de categorías (si la creamos)
                return redirect('dashboard') # Cambia 'dashboard' si tienes otra URL de destino
            except Exception as e:
                    # Manejar error si el nombre ya existe (unique=True)
                    messages.error(request, f"Error al guardar la categoría: {e}")
        else:
            # Si el formulario no es válido, se mostrará con errores
            messages.error(request, "Por favor corrige los errores en el formulario.")
            
    else: # Método GET
        form = CategoriaForm()

    context = {'form': form}
    # Asegúrate de tener una carpeta 'categorias' dentro de 'templates'
    return render(request, 'habitaciones/registrarcategoria.html', context)
#endregion

#region ------ HUESPEDES ------ #

def RegistrarHuesped(request):
    """
    Vista para crear un nuevo perfil de huésped.
    """
    if request.method == 'POST':
        form = HuespedForm(request.POST)
        if form.is_valid():
            try:
                # Verificar unicidad de identificación manualmente (si no es unique=True en el modelo)
                identificacion = form.cleaned_data['identificacion']
                if Registro_Huespedes.objects.filter(identificacion=identificacion).exists():
                    messages.error(request, f"El número de identificación '{identificacion}' ya existe en la base de datos.")
                else:
                    huesped = form.save()
                    messages.success(request, f"Huésped '{huesped.nombre} {huesped.apellido}' registrado con éxito.")
                    # Redirige a la futura lista de huéspedes
                    # Si aún no existe, redirige al dashboard
                    return redirect('dashboard') # Cambia 'dashboard' por 'listar_huespedes' cuando la crees
            
            except Exception as e:
                 # Captura otros errores (como fallos de DB)
                 messages.error(request, f"Error al guardar: {e}")
        else:
            # Si el formulario no es válido, se mostrará con errores
            messages.error(request, "Por favor corrige los errores en el formulario.")
            
    else: # Método GET
        form = HuespedForm()

    context = {
        'form': form
    }
    # Asegúrate de crear este template en la siguiente ruta
    return render(request, 'huespedes/registrarhuesped.html', context)


def ListarHuespedes(request):
    # Obtiene TODOS los huéspedes
    huespedes_queryset = Registro_Huespedes.objects.all().order_by('apellido', 'nombre')
    
    # *** Punto de Depuración ***
    print(f"Número de huéspedes encontrados: {huespedes_queryset.count()}") # Añade esto
    
    context = {
        'huespedes': huespedes_queryset # La clave es 'huespedes'
    }
    return render(request, 'huespedes/listarhuespedes.html', context)


def EditarHuesped(request, huesped_id): 
    """
    Vista para editar un perfil de huésped existente.
    """
    # 1. Obtener la instancia del huésped que queremos editar
    huesped = get_object_or_404(Registro_Huespedes, pk=huesped_id)

    if request.method == 'POST':
        # 2. Si es POST, rellenar el formulario con los datos enviados Y la instancia
        form = HuespedForm(request.POST, instance=huesped)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Huésped '{huesped.nombre} {huesped.apellido}' actualizado con éxito.")
                return redirect('listarhuespedes') # Redirigir a la lista
            except Exception as e:
                 messages.error(request, f"Error al actualizar: {e}")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
            
    else: # Método GET
        # 3. Si es GET, rellenar el formulario solo con la instancia
        form = HuespedForm(instance=huesped)

    context = {
        'form': form,
        'huesped': huesped # Pasamos el huésped por si queremos mostrar el nombre en el título
    }
    # 4. Reutilizar el template de registro
    return render(request, 'huespedes/editarhuespedes.html', context)


def EliminarHuesped(request, huesped_id):
    """
    Vista para eliminar un huésped vía AJAX (solo POST).
    """
    # Usamos 'if' para verificar el método
    if request.method == 'POST': 
        try:
            huesped = get_object_or_404(Registro_Huespedes, pk=huesped_id)
            
            # Opcional: Comprobar si tiene reservas activas si quieres prevenirlo
            # if huesped.reservas_como_principal.filter(check_out__gte=timezone.now()).exists():
            #    return JsonResponse({'status': 'error', 'message': 'Huésped tiene reservas activas.'}, status=400)
            
            huesped_nombre = f"{huesped.nombre} {huesped.apellido}" # Guardar nombre para mensaje
            huesped.delete()
            
            # Devolver respuesta JSON de éxito
            return JsonResponse({'status': 'ok', 'message': f"Huésped '{huesped_nombre}' eliminado con éxito."})

        except Exception as e:
            # Devolver respuesta JSON de error
            return JsonResponse({'status': 'error', 'message': f'Error al eliminar: {str(e)}'}, status=500)
    else:
            # Si no es POST, devolver error
        return HttpResponseBadRequest("Método no permitido. Solo POST.")


def GetHuespedDetallesAJAX(request, huesped_id):
    """
    Vista AJAX para obtener los detalles de un huésped
    y autocompletar el formulario de reserva.
    """
    # Solo respondemos a peticiones GET
    if request.method == 'GET':
        try:
            # 1. Buscar el huésped por su ID
            huesped = get_object_or_404(Registro_Huespedes, pk=huesped_id)
            
            # 2. Preparar los datos que el formulario necesita
            # (Usamos .get('campo', '') para evitar errores si un campo es None)
            data = {
                'status': 'ok',
                'apellido': huesped.apellido,
                'nombre': huesped.nombre,
                'identificacion': huesped.identificacion,
                'email': huesped.email,
                'domicilio': huesped.procedencia, # Asumimos procedencia como domicilio
                'telefono_domicilio': huesped.telefono,
                # Puedes añadir más campos si quieres autocompletar más
                # 'ciudad': huesped.ciudad, # (Necesitarías añadir 'ciudad' al modelo Huesped)
            }
            
            # 3. Devolver los datos como JSON
            return JsonResponse(data)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
#endregion

#region ------ FACTURA ------ # 
def GenerarFactura(request, reserva_id):
    """
    Vista AJAX para calcular el costo de la estadía y generar la factura.
    (MODIFICADA para el nuevo modelo de precios)
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Método no permitido. Solo POST.")

    try:
        # 1. Obtener la Reserva
        # Usamos select_related para optimizar la consulta de las habitaciones y sus tipos (categorías)
        reserva = get_object_or_404(
            Reservas.objects.prefetch_related('habitaciones_asignadas__tipo'), 
            pk=reserva_id
        )

        # 2. Verificar precondiciones (sin cambios)
        if hasattr(reserva, 'factura'):
            return JsonResponse({'status': 'error', 'message': f'La Reserva #{reserva_id} ya tiene una Factura (ID: {reserva.factura.id}) emitida.'}, status=400)
        if not reserva.habitaciones_asignadas.exists():
            return JsonResponse({'status': 'error', 'message': 'No se puede facturar: la reserva no tiene habitaciones asignadas.'}, status=400)
        if not reserva.huesped_principal:
             return JsonResponse({'status': 'error', 'message': 'No se puede facturar: la reserva debe tener un Huésped Titular asignado.'}, status=400)

        # 3. Lógica de Cálculo (MODIFICADA)
        
        # 3.1. Calcular Noches (sin cambios)
        check_in_date = reserva.check_in.date()
        check_out_date = reserva.check_out.date()
        total_noches = (check_out_date - check_in_date).days
        if total_noches == 0:
            total_noches = 1 

        # 3.2. Calcular Subtotal Alojamiento (¡LÓGICA ACTUALIZADA!)
        subtotal_alojamiento = 0
        for h in reserva.habitaciones_asignadas.all():
            # Suma el precio base de la CATEGORÍA + el adicional de la HABITACIÓN
            precio_noche_hab = h.tipo.precio_base + h.adicional_precio
            subtotal_alojamiento += precio_noche_hab
        
        # Multiplicar el total de las habitaciones por el número de noches
        subtotal_alojamiento *= total_noches

        # 3.3. Calcular Impuestos (Usando Integers, como en tu modelo Factura)
        IMPUESTO_PORCENTAJE = 0.19 # 19%
        valor_impuestos = int(subtotal_alojamiento * IMPUESTO_PORCENTAJE)
        
        # 3.4. Calcular Total Final
        total_facturado = subtotal_alojamiento + valor_impuestos

        # 4. Crear la Factura
        factura = Factura.objects.create(
            reserva=reserva,
            huesped=reserva.huesped_principal,
            total_noches=total_noches,
            subtotal_alojamiento=subtotal_alojamiento, # Guardamos el Int
            impuestos=valor_impuestos, # Guardamos el Int (Asegúrate que tu modelo Factura tenga este campo)
            total_facturado=total_facturado, # Guardamos el Int
            estado='Pendiente'
        )

        # 5. Respuesta de éxito
        return JsonResponse({
            'status': 'ok',
            'message': f'Factura #{factura.id} generada con éxito.',
            'factura_id': factura.id,
            'total': str(factura.total_facturado) # Devolver como string para el JS
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error al generar factura: {str(e)}'}, status=500)
#endregion