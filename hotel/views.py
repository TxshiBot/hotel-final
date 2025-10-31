from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.db.models import Q, Count, F, ProtectedError
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import json 
import uuid
import os


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

# ---- PRODUCTOS ---- # 
from hotel.forms import ProductoForm
from hotel.models import Producto
from hotel.models import Consumo

# ---- FACTURA ---- #
from hotel.models import Factura
# ----------------- #


def Dashboard(request):
    
    today = timezone.now().date()

    
    # Cuántas habitaciones están listas para vender
    disponibles_count = Habitaciones.objects.filter(estado='Disponible').count()
    
    # Cuántas están ocupadas
    ocupadas_count = Habitaciones.objects.filter(estado='Ocupada').count()
    
    # Cuántas necesitan limpieza (después de un Check-out)
    limpieza_count = Habitaciones.objects.filter(estado='Limpieza').count()

    
    # Huéspedes que llegan hoy (Reservas que empiezan hoy Y que aún no han hecho Check-in)
    llegadas_hoy_count = Reservas.objects.filter(
        check_in__date=today,
        estado_estancia='Pendiente' # Aún no han llegado
    ).count()
    
    # Huéspedes que se van hoy (Reservas que están 'Activas' Y terminan hoy)
    salidas_hoy_count = Reservas.objects.filter(
        check_out__date=today,
        estado_estancia='Activa' 
    ).count()

    context = {
        'disponibles_count': disponibles_count,
        'ocupadas_count': ocupadas_count,
        'limpieza_count': limpieza_count,
        'llegadas_hoy_count': llegadas_hoy_count,
        'salidas_hoy_count': salidas_hoy_count,
    }
    return render(request, 'dashboard.html', context)

#region ------ HABITACIONES ------ #
def ListarHabitaciones(request):
    habitaciones_list = Habitaciones.objects.select_related('tipo').order_by('numero')
    todas_categorias = Categorias.objects.all().order_by('tipo_hab')

    # --- Lógica de Filtros --- #
    query = request.GET.get('q', '').strip()
    selected_categoria_id = request.GET.get('categoria_id', '').strip()
    status_filter = request.GET.get('status', 'all').strip().lower()

    if query:
        habitaciones_list = habitaciones_list.filter(
            Q(numero__icontains=query) |
            Q(tipo__tipo_hab__icontains=query) |
            Q(estado__icontains=query)
        )
    if selected_categoria_id.isdigit():
        habitaciones_list = habitaciones_list.filter(tipo_id=int(selected_categoria_id))
    valid_statuses = [choice[0].lower() for choice in Habitaciones.ESTADO_CHOICES]
    if status_filter != 'all' and status_filter in valid_statuses:
        habitaciones_list = habitaciones_list.filter(estado__iexact=status_filter)
        active_filter = status_filter
    else:
        active_filter = 'all'
    # --- ------------ --- #

    
    # --- ¡NUEVA LÓGICA PARA ENCONTRAR RESERVA ACTIVA! ---
    now = timezone.now()
    
    # 1. Buscamos todas las reservas activas o futuras
    #    Usamos prefetch_related para cargar eficientemente las habitaciones asignadas
    future_reservas = Reservas.objects.filter(
        check_out__gt=now, 
        confirmado='Confirmado'
    ).prefetch_related('habitaciones_asignadas')

    # 2. Creamos un mapa: { id_habitacion: objeto_reserva }
    active_reserva_map = {}
    for res in future_reservas:
        for hab in res.habitaciones_asignadas.all():
            # Como no permitimos solapamientos, la primera que encontremos es la activa.
            if hab.id not in active_reserva_map:
                 active_reserva_map[hab.id] = res

    # 3. Adjuntamos la reserva encontrada a cada objeto 'habitacion'
    for hab in habitaciones_list:
        hab.active_reserva = active_reserva_map.get(hab.id, None)
    # --- FIN DE LA NUEVA LÓGICA ---


    # --- Lógica de Reservas Asignables (Sin cambios) ---
    reservas_asignables = Reservas.objects.annotate(
        num_asignadas=Count('habitaciones_asignadas')
    ).filter(
        Q(num_habt__gt=F('num_asignadas')) |
        Q(num_habt__isnull=True, num_asignadas=0)
    ).filter(
        confirmado='Confirmado',
        check_out__gt=timezone.now()
    ).distinct().order_by('-id')
    
    habitacion_form = HabitacionForm()

    context = {
        'habitaciones': habitaciones_list, # ¡Ahora cada habitacion tiene un .active_reserva!
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
            
            # --- VALIDACIÓN Y ASIGNACIÓN (Tu lógica existente) ---
            if reserva_id_str: 
                try:
                    reserva_a_asignar = Reservas.objects.prefetch_related('habitaciones_asignadas').get(pk=int(reserva_id_str))
                except (Reservas.DoesNotExist, ValueError):
                    return JsonResponse({'status': 'error', 'message': 'Reserva seleccionada no encontrada.'}, status=404)
            
                # ... (Toda tu lógica de VALIDACIÓN 1: LÍMITE y VALIDACIÓN 2: CONFLICTO DE FECHAS va aquí) ...
                limite = reserva_a_asignar.num_habt if reserva_a_asignar.num_habt is not None and reserva_a_asignar.num_habt > 0 else 1
                asignadas_actualmente = reserva_a_asignar.habitaciones_asignadas.count()
                esta_ya_asignada = habitacion in reserva_a_asignar.habitaciones_asignadas.all()
                if not esta_ya_asignada and asignadas_actualmente >= limite:
                    return JsonResponse({'status': 'error', 'message': f"Límite alcanzado..."}, status=400)
                
                nueva_llegada = reserva_a_asignar.check_in
                nueva_salida = reserva_a_asignar.check_out
                reservas_en_conflicto = habitacion.reservas_asignadas.filter(
                    check_in__lt=nueva_salida, 
                    check_out__gt=nueva_llegada
                ).exclude(pk=reserva_a_asignar.id)
                if reservas_en_conflicto.exists():
                    conflicto = reservas_en_conflicto.first()
                    return JsonResponse({'status': 'error', 'message': f"Conflicto de fechas..."}, status=400)
                # --- FIN VALIDACIONES ---
                
                reserva_a_asignar.habitaciones_asignadas.add(habitacion)
                habitacion.estado = 'Ocupada'
            
            # --- LÓGICA DE DESASIGNACIÓN/CAMBIO DE ESTADO ---
            else: 
                habitacion.estado = nuevo_estado
                if habitacion.estado == 'Disponible' or habitacion.estado == 'Limpieza':
                    reservas_a_quitar = habitacion.reservas_asignadas.filter(check_out__gt=timezone.now())
                    for res in reservas_a_quitar:
                        res.habitaciones_asignadas.remove(habitacion)
            
            habitacion.save()

            # --- ¡AQUÍ ESTÁ LA CORRECCIÓN DE LA RESPUESTA! ---
            response_data = {
                'status': 'ok',
                'nuevo_estado': habitacion.get_estado_display(),
                'reserva_asignada': None # Default
            }
            
            if reserva_a_asignar:
                # Si asignamos una reserva, incluimos todos los datos necesarios
                response_data['reserva_asignada'] = {
                    'id': reserva_a_asignar.id,
                    'nombre_huesped': f"{reserva_a_asignar.nombre} {reserva_a_asignar.apellido}",
                    # ¡Añadimos las fechas que faltaban!
                    'check_in_simple': reserva_a_asignar.check_in.strftime('%d/%m/%y'),
                    'check_out_simple': reserva_a_asignar.check_out.strftime('%d/%m/%y')
                }
            
            return JsonResponse(response_data)
            # --- FIN DE LA CORRECCIÓN ---

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


def EliminarReserva(request, reserva_id):
    """
    Vista AJAX para eliminar una reserva.
    Esto desasigna las habitaciones pero NO las elimina.
    """
    if request.method == 'POST':
        try:
            reserva = get_object_or_404(Reservas, pk=reserva_id)
            
            # --- LÓGICA CLAVE DE NEGOCIO ---
            # 1. Desvincular todas las habitaciones asignadas (ManyToManyField.clear())
            # Esto vacía la tabla intermedia M2M, dejando las habitaciones intactas.
            reserva.habitaciones_asignadas.clear() 
            
            # 2. (Opcional) Si tienes una Factura y quieres eliminarla también:
            if hasattr(reserva, 'factura'):
                # Usamos try-except por si la FK tiene PROTECT (como la definimos)
                try:
                    reserva.factura.delete()
                except Exception as e:
                    print(f"No se pudo eliminar la factura (quizás por PROTECT): {e}")

            # 3. Eliminar la reserva
            reserva_info = f"#{reserva.id} - {reserva.nombre} {reserva.apellido}"
            reserva.delete()
            
            return JsonResponse({'status': 'ok', 'message': f'Reserva {reserva_info} eliminada con éxito.'})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return HttpResponseBadRequest("Método no permitido. Solo POST.")


@transaction.atomic
def RealizarCheckIn(request, reserva_id):
    """
    Marca una reserva como 'Activa' (Checked-in) y ocupa las habitaciones.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
    
    try:
        reserva = get_object_or_404(Reservas.objects.prefetch_related('habitaciones_asignadas'), pk=reserva_id)
        
        # --- Reglas de Negocio ---
        if reserva.estado_estancia == 'Activa':
            return JsonResponse({'status': 'error', 'message': 'El huésped ya ha realizado el Check-in.'}, status=400)
        if reserva.confirmado != 'Confirmado':
            return JsonResponse({'status': 'error', 'message': 'La reserva debe estar "Confirmada" para hacer Check-in.'}, status=400)
        if not reserva.habitaciones_asignadas.exists():
            return JsonResponse({'status': 'error', 'message': 'No se puede hacer Check-in: la reserva no tiene habitaciones asignadas.'}, status=400)
        
        # --- Ejecutar Acciones ---
        reserva.estado_estancia = 'Activa'
        reserva.save()
        
        # Cambiar todas las habitaciones a 'Ocupada'
        for hab in reserva.habitaciones_asignadas.all():
            hab.estado = 'Ocupada'
            hab.save()
            
        return JsonResponse({'status': 'ok', 'message': 'Check-in realizado con éxito. Las habitaciones están ahora "Ocupadas".', 'nuevo_estado_estancia': 'Activa'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@transaction.atomic
def RealizarCheckOut(request, reserva_id):
    """
    Marca una reserva como 'Completada' (Checked-out) y libera las habitaciones a 'Limpieza'.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        reserva = get_object_or_404(Reservas.objects.select_related('factura').prefetch_related('habitaciones_asignadas'), pk=reserva_id)
        
        # --- Reglas de Negocio ---
        if reserva.estado_estancia == 'Completada':
            return JsonResponse({'status': 'error', 'message': 'El huésped ya ha realizado el Check-out.'}, status=400)
        if reserva.estado_estancia == 'Pendiente':
            return JsonResponse({'status': 'error', 'message': 'No se puede hacer Check-out sin haber hecho Check-in primero.'}, status=400)
        
        # --- ¡LA REGLA MÁS IMPORTANTE! ---
        if not hasattr(reserva, 'factura') or reserva.factura.estado != 'Pagada':
            return JsonResponse({'status': 'error', 'message': '¡Check-out bloqueado! La factura de la reserva no ha sido marcada como "Pagada".'}, status=400)
            
        # --- Ejecutar Acciones ---
        reserva.estado_estancia = 'Completada'
        reserva.save()
        
        # Cambiar todas las habitaciones a 'Limpieza'
        for hab in reserva.habitaciones_asignadas.all():
            hab.estado = 'Limpieza'
            hab.save()
            
        return JsonResponse({'status': 'ok', 'message': 'Check-out realizado con éxito. Las habitaciones están ahora en "Limpieza".', 'nuevo_estado_estancia': 'Completada'})

    except Exception as e:
        # --- ¡ESTA ES LA LÍNEA QUE FALTABA! ---
        return JsonResponse({'status': 'error', 'message': f'Error inesperado: {str(e)}'}, status=500)
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


def GetHuespedReservasAJAX(request, huesped_id):
    """
    Vista AJAX para obtener el historial de reservas de un huésped,
    buscando si es Titular O Acompañante. (VERSIÓN CORREGIDA)
    """
    if request.method == 'GET':
        try:
            huesped = get_object_or_404(Registro_Huespedes, pk=huesped_id)
            
            # 1. Obtener los IDs de las reservas donde es Titular
            reservas_p_ids = set(huesped.reservas_como_principal.values_list('id', flat=True))
            
            # 2. Obtener los IDs de las reservas donde es Acompañante
            reservas_a_ids = set(huesped.reservas_como_acompanante.values_list('id', flat=True))
            
            # 3. Combinar todos los IDs únicos
            all_ids = reservas_p_ids.union(reservas_a_ids)
            
            if not all_ids:
                return JsonResponse({'status': 'ok', 'reservas': []}) # No tiene reservas

            # 4. Obtener todos los objetos Reserva de una sola vez
            todas_reservas = Reservas.objects.filter(id__in=all_ids).order_by('-check_in')
            
            data_reservas = []
            for res in todas_reservas:
                # 5. Determinar el rol para cada reserva
                rol = "Titular" if res.id in reservas_p_ids else "Acompañante"
                
                # 6. Determinar el estado más relevante
                estado_label = res.get_estado_estancia_display() # Ej: "Activa"
                estado_class = res.estado_estancia.lower()      # Ej: "activa"
                
                # Si la estancia aún está 'Pendiente', es más útil saber si está 'Confirmada'
                if res.estado_estancia == 'Pendiente':
                    estado_label = res.confirmado
                    estado_class = res.confirmado.lower()

                data_reservas.append({
                    'id': res.id,
                    'check_in': res.check_in.strftime('%d/%m/%Y'),
                    'check_out': res.check_out.strftime('%d/%m/%Y'),
                    'estado_label': estado_label, # "Activa", "Completada", "Confirmado"
                    'estado_class': estado_class, # "activa", "completada", "confirmado"
                    'rol': rol # "Titular" o "Acompañante"
                })

            return JsonResponse({'status': 'ok', 'reservas': data_reservas})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
#endregion

#region ------ FACTURA ------ # 
@transaction.atomic # Es buena idea mantener esto por si acaso
def GenerarFactura(request, reserva_id):
    """
    Vista AJAX para calcular el costo TOTAL (Alojamiento + Consumos) 
    y generar la factura final.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Método no permitido. Solo POST.")

    try:
        # 1. Obtener la Reserva (Optimizada para traer todo lo necesario)
        reserva = get_object_or_404(
            Reservas.objects.prefetch_related(
                'habitaciones_asignadas__tipo', # Para calcular alojamiento
                'consumos'                     # Para calcular consumos
            ), 
            pk=reserva_id
        )

        # 2. Verificar precondiciones (Sin cambios)
        if hasattr(reserva, 'factura'):
            return JsonResponse({'status': 'error', 'message': f'La Reserva #{reserva_id} ya tiene una Factura (ID: {reserva.factura.id}) emitida.'}, status=400)
        if not reserva.habitaciones_asignadas.exists():
            return JsonResponse({'status': 'error', 'message': 'No se puede facturar: la reserva no tiene habitaciones asignadas.'}, status=400)
        if not reserva.huesped_principal:
             return JsonResponse({'status': 'error', 'message': 'No se puede facturar: la reserva debe tener un Huésped Titular asignado.'}, status=400)

        # 3. Lógica de Cálculo (¡ACTUALIZADA!)
        
        # 3.1. Calcular Noches (Sin cambios)
        total_noches = (reserva.check_out.date() - reserva.check_in.date()).days
        if total_noches == 0:
            total_noches = 1 

        # 3.2. Calcular Subtotal Alojamiento (Sin cambios)
        subtotal_alojamiento = 0
        for h in reserva.habitaciones_asignadas.all():
            precio_noche_hab = h.tipo.precio_base + h.adicional_precio
            subtotal_alojamiento += precio_noche_hab
        subtotal_alojamiento *= total_noches

        # 3.3. Calcular Subtotal Consumos (¡NUEVA LÓGICA!)
        # Sumamos solo los consumos que NO fueron pagados inmediatamente
        consumos_pendientes = reserva.consumos.filter(pagado_inmediatamente=False)
        
        subtotal_consumos = 0
        for c in consumos_pendientes:
            subtotal_consumos += c.precio_en_el_momento * c.cantidad

        # (Método alternativo más rápido si prefieres usar la DB):
        # subtotal_consumos = consumos_pendientes.aggregate(
        #     total=Sum(F('precio_en_el_momento') * F('cantidad'), output_field=models.IntegerField())
        # )['total'] or 0

        # 3.4. Calcular Totales
        subtotal_general = subtotal_alojamiento + subtotal_consumos
        IMPUESTO_PORCENTAJE = 0.19 # Asumimos 19%
        valor_impuestos = int(subtotal_general * IMPUESTO_PORCENTAJE)
        total_facturado = subtotal_general + valor_impuestos

        # 4. Crear la Factura (¡ACTUALIZADA!)
        factura = Factura.objects.create(
            reserva=reserva,
            huesped=reserva.huesped_principal,
            total_noches=total_noches,
            subtotal_alojamiento=subtotal_alojamiento,
            subtotal_consumos=subtotal_consumos, # <-- Campo nuevo
            impuestos=valor_impuestos, 
            total_facturado=total_facturado,
            estado='Pendiente'
        )

        # 5. Respuesta de éxito (Sin cambios)
        return JsonResponse({
            'status': 'ok',
            'message': f'Factura #{factura.id} generada con éxito.',
            'factura_id': factura.id,
            'total': str(factura.total_facturado)
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error al generar factura: {str(e)}'}, status=500)


def VerFactura(request, factura_id):
    """
    Muestra la factura final (alojamiento + consumos) en un formato imprimible.
    (Lógica de cálculo movida aquí para arreglar el bug 'mul')
    """
    try:
        factura = get_object_or_404(
            Factura.objects.select_related(
                'reserva', 
                'reserva__huesped_principal'
            ),
            pk=factura_id
        )
        
        # --- LÓGICA DE CÁLCULO MEJORADA ---
        
        # 1. Habitaciones: Calcular el subtotal POR HABITACIÓN
        habitaciones_con_calculos = []
        habs_asignadas = factura.reserva.habitaciones_asignadas.select_related('tipo').all()
        for hab in habs_asignadas:
            precio_noche = hab.tipo.precio_base + hab.adicional_precio
            subtotal_hab = precio_noche * factura.total_noches
            habitaciones_con_calculos.append({
                'numero': hab.numero,
                'tipo_hab': hab.tipo.tipo_hab,
                'precio_noche': precio_noche,
                'subtotal': subtotal_hab
            })

        # 2. Consumos: Calcular el subtotal POR CONSUMO
        consumos_con_calculos = []
        todos_los_consumos = factura.reserva.consumos.select_related('producto').order_by('fecha_consumo')
        for c in todos_los_consumos:
            subtotal_consumo = c.precio_en_el_momento * c.cantidad
            consumos_con_calculos.append({
                'nombre': c.producto.nombre,
                'cantidad': c.cantidad,
                'precio_unitario': c.precio_en_el_momento,
                'subtotal': subtotal_consumo,
                'pagado': c.pagado_inmediatamente,
                'fecha': c.fecha_consumo
            })
        
        # 3. Totales (ya los tenemos en la factura)
        subtotal_general = factura.subtotal_alojamiento + factura.subtotal_consumos
        
        context = {
            'factura': factura,
            'habitaciones_data': habitaciones_con_calculos, # <-- Pasamos la data calculada
            'consumos_data': consumos_con_calculos,     # <-- Pasamos la data calculada
            'subtotal_general': subtotal_general,
        }
        
        return render(request, 'facturas/verfactura.html', context)
        
    except Exception as e:
        # Aquí es donde se estaba generando tu error
        messages.error(request, f"Error al cargar la factura: {str(e)}")
        return redirect('reservas') # Redirige a la lista


@transaction.atomic
def MarcarFacturaPagada(request, factura_id):
    """
    Vista AJAX para cambiar el estado de una factura a 'Pagada'.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        factura = get_object_or_404(Factura, pk=factura_id)
        
        if factura.estado == 'Pagada':
             return JsonResponse({'status': 'error', 'message': 'Esta factura ya fue marcada como pagada.'}, status=400)

        factura.estado = 'Pagada'
        factura.save()
        
        return JsonResponse({
            'status': 'ok', 
            'message': 'Factura actualizada a Pagada.',
            'nuevo_estado': factura.get_estado_display() # Devuelve "Pagada"
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error inesperado: {str(e)}'}, status=500)
#endregion

#region ------ MINIBAR ------ #
def ListarProductos(request):
    productos = Producto.objects.filter(esta_activo=True).order_by('nombre')
    active_reservas = Reservas.objects.filter(
        confirmado='Confirmado',
        check_out__gt=timezone.now()
    ).order_by('-id')
    context = {
        'productos': productos,
        'active_reservas': active_reservas
    }
    return render(request, 'productos/listarproductos.html', context)

def RegistrarProducto(request):
    # ... (Tu vista RegistrarProducto se mantiene exactamente igual) ...
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        foto_archivo = request.FILES.get('foto', None)
        if form.is_valid() and foto_archivo:
            producto = form.save(commit=False)
            location_path = 'hotel/public/img/minibar' 
            imagen_storage = FileSystemStorage(location=location_path)
            nombre_limpio = foto_archivo.name.strip()
            nombre_foto_final = str(uuid.uuid4()) + "_" + nombre_limpio
            imagen_storage.save(nombre_foto_final, foto_archivo)
            producto.foto = nombre_foto_final
            producto.save()
            messages.success(request, f"Producto '{producto.nombre}' guardado.")
            return redirect('listarproductos')
        else:
            messages.error(request, "Error en el formulario. Revisa los campos.")
            if not foto_archivo:
                messages.error(request, "Debes subir una imagen.")
    else: 
        form = ProductoForm()
    context = {'form': form}
    return render(request, 'productos/registrarproducto.html', context)

@transaction.atomic 
def RegistrarConsumoAJAX(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        producto_id = int(data.get('producto_id'))
        reserva_id = int(data.get('reserva_id'))
        cantidad = int(data.get('cantidad', 1))
        pagado_ya = bool(data.get('pagado_inmediatamente', False))
        
        producto = Producto.objects.select_for_update().get(pk=producto_id)
        if not producto.esta_activo:
            return JsonResponse({'status': 'error', 'message': 'Este producto ya no está disponible para la venta.'}, status=400)
        
        if cantidad <= 0:
            return JsonResponse({'status': 'error', 'message': 'La cantidad debe ser mayor a cero.'}, status=400)

        producto = Producto.objects.select_for_update().get(pk=producto_id)
        reserva = Reservas.objects.get(pk=reserva_id)

        if producto.stock_disponible < cantidad:
            return JsonResponse({
                'status': 'error', 
                'message': f'Stock insuficiente. Solo quedan {producto.stock_disponible} unidades de {producto.nombre}.'
            }, status=400)
        
        producto.stock_disponible = F('stock_disponible') - cantidad
        producto.save()
        
        # --- ¡LÓGICA ACTUALIZADA! ---
        # 1. Creamos el consumo
        nuevo_consumo = Consumo.objects.create(
            reserva=reserva,
            producto=producto,
            cantidad=cantidad,
            precio_en_el_momento=producto.precio,
            pagado_inmediatamente=pagado_ya
        )
        
        # 2. Refrescamos el stock
        producto.refresh_from_db()
        
        # 3. Preparamos la respuesta
        response_data = {
            'status': 'ok',
            'message': 'Consumo registrado con éxito.',
            'nuevo_stock': producto.stock_disponible,
            'recibo_id': None # Por defecto no hay recibo
        }
        
        # 4. Si se pagó ya, adjuntamos el ID del recibo
        if pagado_ya:
            response_data['recibo_id'] = nuevo_consumo.id
        
        return JsonResponse(response_data)
        # --- FIN DE LA LÓGICA ACTUALIZADA ---

    except Producto.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'El producto no existe.'}, status=404)
    except Reservas.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'La reserva no existe.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error inesperado: {str(e)}'}, status=500)


def VerReciboConsumo(request, consumo_id):
    """
    Muestra una "mini-factura" o recibo imprimible para un consumo
    que fue pagado inmediatamente.
    """
    # Usamos select_related para traer la info de la reserva y el producto
    consumo = get_object_or_404(
        Consumo.objects.select_related('reserva', 'producto', 'reserva__huesped_principal'),
        pk=consumo_id
    )
    
    # Solo permitir ver recibos que fueron marcados como pagados
    if not consumo.pagado_inmediatamente:
        return HttpResponseBadRequest("Este consumo no es un recibo de pago inmediato.")

    # --- Cálculos ---
    # Asumimos que los precios en tu DB (precio_en_el_momento) ya incluyen IVA
    # Si no, tendríamos que calcularlo:
    subtotal = consumo.cantidad * consumo.precio_en_el_momento
    iva = int(subtotal * 0.19) # Asumimos 19%
    total = subtotal + iva
    
    context = {
        'consumo': consumo,
        'subtotal': subtotal,
        'iva': iva,
        'total': total
    }
    # Renderizamos un template que NO incluye el header/sidebar
    return render(request, 'productos/reciboconsumo.html', context)


def EditarProducto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    foto_antigua = producto.foto # Guardamos el nombre de la foto vieja

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        foto_archivo_nuevo = request.FILES.get('foto', None) # Archivo nuevo (opcional)
        
        if form.is_valid():
            producto_editado = form.save(commit=False)
            
            # --- Lógica de tu sistema de archivos ---
            if foto_archivo_nuevo:
                # 1. Se subió una foto nueva. Hay que borrar la vieja y guardar la nueva.
                location_path = 'hotel/public/img/minibar'
                imagen_storage = FileSystemStorage(location=location_path)
                
                # Borrar la foto antigua si existe
                if foto_antigua:
                    try:
                        # Componemos la ruta completa para el storage
                        ruta_foto_antigua = os.path.join(location_path, foto_antigua)
                        if imagen_storage.exists(ruta_foto_antigua):
                            imagen_storage.delete(ruta_foto_antigua)
                    except Exception as e:
                        print(f"Advertencia: No se pudo eliminar la foto antigua: {e}")

                # Guardar la foto nueva
                nombre_limpio = foto_archivo_nuevo.name.strip()
                nombre_foto_final = str(uuid.uuid4()) + "_" + nombre_limpio
                imagen_storage.save(nombre_foto_final, foto_archivo_nuevo)
                producto_editado.foto = nombre_foto_final # Guardar nombre nuevo
            else:
                # 2. No se subió foto nueva. Mantenemos la foto antigua.
                producto_editado.foto = foto_antigua
            
            producto_editado.save()
            messages.success(request, f"Producto '{producto_editado.nombre}' actualizado.")
            return redirect('listarproductos')
        else:
            messages.error(request, "Error en el formulario. Revisa los campos.")
            
    else: # GET
        form = ProductoForm(instance=producto)

    context = {
        'form': form,
        'producto': producto # Para mostrar la imagen actual
    }
    return render(request, 'productos/editarproducto.html', context)


def EliminarProducto(request, producto_id):
    """
    Elimina un producto de la BD y su foto del sistema de archivos.
    """
    if request.method == 'POST':
        try:
            producto = get_object_or_404(Producto, pk=producto_id)
            foto_nombre = producto.foto
            producto_nombre = producto.nombre

            # 1. Eliminar la foto de /hotel/public/img/minibar/
            if foto_nombre:
                location_path = 'hotel/public/img/minibar'
                imagen_storage = FileSystemStorage(location=location_path)
                
                # Componemos la ruta completa que el FileSystemStorage entiende
                ruta_foto = os.path.join(location_path, foto_nombre)

                if imagen_storage.exists(ruta_foto):
                    imagen_storage.delete(ruta_foto)
            
            # 2. Eliminar el producto de la Base de Datos
            producto.delete()
            
            return JsonResponse({'status': 'ok', 'message': f"Producto '{producto_nombre}' eliminado."})
        
        except ProtectedError:
             # Esto pasará si un 'Consumo' está usando este producto
             return JsonResponse({'status': 'error', 'message': 'No se puede eliminar. Este producto ya está en un consumo registrado.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return HttpResponseBadRequest("Método no permitido.")
#endregion