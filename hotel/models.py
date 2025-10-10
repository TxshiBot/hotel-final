from django.db import models


class Hab_Categorias(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    descripcion = models.CharField(max_length=255, null=False)
    vistas = models.CharField(max_length=50, null=False)

    class Meta:
        db_table = 'hab_categorias'


class Registro_Huespedes(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    apellido = models.CharField(max_length=100, null=False)
    tipo_documento = models.CharField(max_length=100, null=False)
    identificacion = models.IntegerField(null=False)
    procedencia = models.CharField(max_length=200, null=False)
    razon = models.CharField(max_length=255, null=False)
    contacto = models.CharField(max_length=255, null=False)
    codigo_usuario = models.CharField(max_length=10, null=False)

    class Meta:
        db_table = 'registro_huespedes'


class Habitaciones(models.Model):
    ESTADO_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    ]

    id = models.AutoField(primary_key=True)
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, null=False)
    precio = models.IntegerField(null=False)
    piso = models.IntegerField(null=False, default=1)
    categoria_id = models.ForeignKey(Hab_Categorias, on_delete=models.CASCADE)

    class Meta:
        db_table = 'habitaciones'


class Reservas(models.Model):
    id = models.AutoField(primary_key=True)
    check_in = models.DateTimeField(null=False)
    check_out = models.DateTimeField(null=False)
    companion = models.IntegerField(null=False)
    observaciones = models.TextField(null=False)
    cliente_id = models.ForeignKey(Registro_Huespedes, on_delete=models.CASCADE)
    habitacion_id = models.ForeignKey(Habitaciones, on_delete=models.CASCADE)

    class Meta:
        db_table = 'reserva'