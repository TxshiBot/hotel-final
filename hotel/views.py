from django.shortcuts import render, redirect
from django.db import connection

def Dashboard(request):
    return render(request, 'dashboard.html')


def ListarHabitaciones(request):
    return render(request, 'habitaciones/listarhabitaciones.html')


def RegistroHabitaciones(request):
    return render(request, 'habitaciones/registrarhabitaciones.html')

<<<<<<< HEAD
=======

def Reservar(request):
    return render(request, 'reservas/reservar.html')


def ListarReservas(request):
    return render(request, 'reservas/reservas.html')
>>>>>>> d599ba8118b2fec660ec941854101719f047aba1
