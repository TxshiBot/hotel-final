from django.shortcuts import render, redirect
from django.db import connection

# ---- FORMS ---- # 
from hotel.forms import ReservarForm


def Dashboard(request):
    return render(request, 'dashboard.html')


def ListarHabitaciones(request):
    return render(request, 'habitaciones/listarhabitaciones.html')


def RegistroHabitaciones(request):
    return render(request, 'habitaciones/registrarhabitaciones.html')


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
    return render(request, 'reservas/reservas.html')
