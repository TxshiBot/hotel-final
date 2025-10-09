from django.db import models


class Hab_Categorias(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255)
    vistas = models.CharField(max_length=50)

    class Meta:
        db_table = 'hab_categorias'


class Registro_Huespedes(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    tipo_documento = models.CharField(max_length=100)
    identificacion = models.IntegerField()
    procedencia = models.CharField(max_length=200)
    razon = models.CharField(max_length=255)
    contacto = models.CharField(max_length=255)
    codigo_usuario = models.CharField(max_length=10)

    class Meta:
        db_table = 'registro_huespedes'


class Habitaciones(models.Model):
    ESTADO_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    ]

    id = models.AutoField(primary_key=True)
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES)
    precio = models.IntegerField()
    categoria_id = models.ForeignKey(Hab_Categorias, on_delete=models.CASCADE)

    class Meta:
        db_table = 'habitaciones'


class Reservas(models.Model):
    id = models.AutoField(primary_key=True)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    companion = models.IntegerField()
    observaciones = models.TextField()
    cliente_id = models.ForeignKey(Registro_Huespedes, on_delete=models.CASCADE)
    habitacion_id = models.ForeignKey(Habitaciones, on_delete=models.CASCADE)

    class Meta:
        db_table = 'reserva'