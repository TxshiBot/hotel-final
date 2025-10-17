from django.shortcuts import render, redirect
from django.db import connection

def Dashboard(request):
    return render(request, 'dashboard.html')


def ListarHabitaciones(request):
<<<<<<< Updated upstream
    return render(request, 'habitaciones/listarhabitaciones.html')


def RegistroHabitaciones(request):
    return render(request, 'habitaciones/registrarhabitaciones.html')
=======
    return render(request, 'habitaciones/listarhabitaciones.html')
>>>>>>> Stashed changes
