from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
import json 

# ---- MODELS ---- #
from hotel.models import Reservas
from hotel.models import Categorias
from hotel.models import Habitaciones

# ---- FORMS ---- # 
from hotel.forms import ReservarForm
from hotel.forms import CategoriaForm
from hotel.forms import HabitacionForm

def Dashboard(request):
    return render(request, 'dashboard.html')


def ListarHabitaciones(request):
    habitaciones_list = Habitaciones.objects.select_related('tipo', 'reserva').order_by('numero')
    todas_categorias = Categorias.objects.all().order_by('tipo_hab') # Obtener todas las categorías

    # --- Lógica de Búsqueda (Mantenemos la lógica anterior por ahora) ---
    query = request.GET.get('q', '').strip()
    selected_categoria_id = request.GET.get('categoria_id', '').strip() # NUEVO: Leer filtro categoría
    status_filter = request.GET.get('status', 'all').strip().lower() # Usar minúsculas para comparar con data-filter

    if query:
        try:
            query_num = int(query)
            q_filter = Q(reserva__id=query_num) | Q(numero__icontains=query)
        except ValueError:
            q_filter = (
                Q(tipo__tipo_hab__icontains=query) |
                Q(estado__icontains=query) |
                Q(reserva__nombre__icontains=query)|
                Q(reserva__apellido__icontains=query)
            )
        habitaciones_list = habitaciones_list.filter(q_filter).distinct()

    # --- NUEVO: Filtrado por Categoría ---
    if selected_categoria_id.isdigit(): # Asegurarse que sea un número
        habitaciones_list = habitaciones_list.filter(tipo_id=int(selected_categoria_id))

    # --- Lógica de Filtrado por Estado ---
    valid_statuses = [choice[0].lower() for choice in Habitaciones.ESTADO_CHOICES] # Comparar en minúsculas
    if status_filter != 'all' and status_filter in valid_statuses:
        habitaciones_list = habitaciones_list.filter(estado__iexact=status_filter)
        active_filter = status_filter # Guardar filtro activo (minúsculas)
    else:
        active_filter = 'all'

    # --- Obtener Reservas Asignables (SIN CAMBIOS) ---
    reservas_asignables = Reservas.objects.filter(habitaciones__isnull=True).order_by('-id')
    habitacion_form = HabitacionForm() # Para choices de estado

    context = {
        'habitaciones': habitaciones_list,
        'reservas_asignables': reservas_asignables,
        'habitacion_form': habitacion_form,
        'todas_categorias': todas_categorias, # NUEVO: Pasar categorías al template
        'selected_categoria_id': selected_categoria_id, # NUEVO: Pasar ID seleccionado
        'active_filter': active_filter, # Filtro de estado activo
        'search_query': query,
    }
    return render(request, 'habitaciones/listarhabitaciones.html', context)


# --- VISTA AJAX PARA ACTUALIZAR ESTADO/RESERVA (SIMPLIFICADA) ---
def ActualizarHabitacionAJAX(request):
    if request.method == 'POST': # Verificación simple con if
        try:
            # Leer datos JSON del cuerpo de la petición
            data = json.loads(request.body)
            habitacion_id = data.get('habitacion_id')
            nuevo_estado = data.get('estado')
            reserva_id = data.get('reserva_id') # Puede ser un ID numérico o ""/"None"

            # Validar datos básicos
            if not habitacion_id or not nuevo_estado:
                return JsonResponse({'status': 'error', 'message': 'Faltan datos requeridos (ID o estado).'}, status=400)

            habitacion = get_object_or_404(Habitaciones, pk=habitacion_id)

            # Validar y actualizar estado
            valid_statuses = [choice[0] for choice in Habitaciones.ESTADO_CHOICES]
            if nuevo_estado in valid_statuses:
                habitacion.estado = nuevo_estado
            else:
                 return JsonResponse({'status': 'error', 'message': 'Estado no válido.'}, status=400)

            # Actualizar/Asignar/Desasignar reserva
            if reserva_id: # Si se envió un ID de reserva
                try:
                    # Intenta obtener la reserva seleccionada
                    reserva_asignada = Reservas.objects.get(pk=int(reserva_id))
                    habitacion.reserva = reserva_asignada
                    # Considera cambiar estado a 'Ocupada' automáticamente si asignas reserva?
                    # if nuevo_estado == 'Disponible': # Solo si estaba disponible
                    #    habitacion.estado = 'Ocupada'
                except (Reservas.DoesNotExist, ValueError):
                    return JsonResponse({'status': 'error', 'message': 'Reserva seleccionada no encontrada o ID inválido.'}, status=404)
            else: # Si reserva_id está vacío o nulo, se desasigna
                habitacion.reserva = None
                # Considera cambiar estado a 'Disponible' o 'Limpieza' si se desasigna?
                # if habitacion.estado == 'Ocupada':
                #    habitacion.estado = 'Limpieza' # O 'Disponible'

            habitacion.save()

            # Preparamos la respuesta
            response_data = {
                'status': 'ok',
                'nuevo_estado': habitacion.get_estado_display(), # Usamos get_..._display() para el label
                'reserva_asignada': {
                    'id': habitacion.reserva.id,
                    'nombre_huesped': f"{habitacion.reserva.nombre} {habitacion.reserva.apellido}"
                } if habitacion.reserva else None
            }
            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Formato de datos inválido.'}, status=400)
        except Exception as e:
            # Captura genérica para otros posibles errores
            return JsonResponse({'status': 'error', 'message': f'Error interno: {str(e)}'}, status=500)
    else:
        # Si no es POST, devolver error
        return HttpResponseBadRequest("Método no permitido. Solo POST.")


# --- VISTA AJAX PARA DETALLES DE RESERVA (CONTEO) ---
def GetReservaDetallesAJAX(request, reserva_id):
    if request.method == 'GET': # Esta vista sí usa GET
        try:
            reserva = get_object_or_404(Reservas.objects.prefetch_related('habitaciones_set'), pk=reserva_id) # Optimizamos un poco

            num_necesarias = reserva.num_habt if reserva.num_habt is not None else 1 # Asume 1 si num_habt es None
            # Contamos las habitaciones REALMENTE asignadas a esta reserva
            num_asignadas = reserva.habitaciones_set.count()

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


def Reservar(request):
    
    if request.method == 'POST':
        form = ReservarForm(request.POST)
        
        if form.is_valid():
            # ** Bloque de éxito **
            print("XXXXXXXXXXXXX - VÁLIDO. Guardando reserva...")
            reservar = form.save()
            # La redirección debe ser con 'return' para finalizar la vista
            return redirect('reservas')
        
        else:
            # ** Bloque de fallo de validación **
            # ** ESTE ES EL PASO CLAVE QUE YA HICISTE: Muestra el error en tu terminal **
            print("Formulario NO VÁLIDO. Errores detallados:")
            print(form.errors) 
            # El código sigue su curso hasta el final, retornando el formulario con errores
            
    else:
        # ** Bloque de petición GET (primera carga de la página) **
        form = ReservarForm()
    
    # Renderiza el template. Si el método fue POST y form.is_valid() fue False,
    # el template recibe 'form' con todos los mensajes de error de Django.
    # Si fue GET, el template recibe 'form' vacío.
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