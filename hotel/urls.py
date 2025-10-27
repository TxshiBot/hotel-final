"""
URL configuration for hotel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

# ---- DASBOARD ---- #
from hotel.views import Dashboard
from hotel.views import Dashboard

# ---- HABITACIONES ---- #
from hotel.views import ListarHabitaciones
from hotel.views import RegistroHabitaciones


# ---- RESERVAS ---- # 
from hotel.views import Reservar
from hotel.views import ListarReservas

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', Dashboard, name='dashboard'),
    path('listahabitaciones', ListarHabitaciones, name='habitaciones'),
    path('registrohabitaciones', RegistroHabitaciones, name='registrohabitaciones'),
    path('reservar', Reservar, name='reservar'),
    path('listarreservas', ListarReservas, name='reservas'),
]
