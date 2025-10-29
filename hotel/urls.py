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
from hotel.views import RegistrarHabitaciones
from hotel.views import RegistroCategorias
from hotel.views import ActualizarHabitacionAJAX
from hotel.views import GetReservaDetallesAJAX

# ---- RESERVAS ---- # 
from hotel.views import Reservar
from hotel.views import ListarReservas
from hotel.views import ConfirmarReserva
from hotel.views import EditarReserva

# ---- HUESPEDES ---- # 
from hotel.views import RegistrarHuesped
from hotel.views import ListarHuespedes
from hotel.views import EliminarHuesped
from hotel.views import EditarHuesped
from hotel.views import GetHuespedDetallesAJAX

# ---- FACTURA ---- #
from hotel.views import GenerarFactura


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', Dashboard, name='dashboard'),
    path('listahabitaciones', ListarHabitaciones, name='habitaciones'),
    path('registrohabitaciones', RegistrarHabitaciones, name='registrohabitaciones'),
    path('reservar', Reservar, name='reservar'),
    path('listarreservas', ListarReservas, name='reservas'),
    path('reservas/confirmar/<int:reserva_id>/', ConfirmarReserva, name='confirmarreserva'),
    path('registrocategorias', RegistroCategorias, name='registrocategorias'),
    path('actualizarajax', ActualizarHabitacionAJAX, name='actualizarhabitacionajax'),
    path('reservas/detallesajax/<int:reserva_id>/', GetReservaDetallesAJAX, name='reservadetallesajax'),
    path('registrohuespedes', RegistrarHuesped, name='registrarhuesped'),
    path('listarhuespedes', ListarHuespedes, name='listarhuespedes'),
    path('huespedes/eliminar/<int:huesped_id>/', EliminarHuesped, name='eliminarhuesped'),
    path('huespedes/editar/<int:huesped_id>/', EditarHuesped, name='editarhuesped'),
    path('huespedes/detallesajax/<int:huesped_id>/', GetHuespedDetallesAJAX, name='huespeddetallesajax'),
    path('facturas/generar/<int:reserva_id>/', GenerarFactura, name='generarfactura'),
    path('reservas/editar/<int:reserva_id>/', EditarReserva, name='editarreserva'),
]