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
    nombre = models.CharField(null=False, max_length=50)
    apellido = models.CharField(null=False, max_length=50)
    ciudad = models.CharField(null=False, max_length=50)
    telefono_domicilio = models.IntegerField(null=False)
    email = models.CharField(null=False, max_length=50)
    domicilio = models.CharField(null=False, max_length=255)
    departamento = models.CharField(null=False, max_length=50)
    telefono_oficina = models.CharField(null=False, max_length=50)
    formadepago = models.CharField(null=False, max_length=50)
    check_in = models.DateTimeField(null=False, max_length=50)
    check_out = models.DateTimeField(null=False, max_length=50)
    companion = models.IntegerField(null=False)
    
    # OPCIONAL: COMPAÑÍA #
    nombre_compania = models.CharField(null=True, max_length=50)
    compania_domicilio = models.CharField(null=True, max_length=50)
    compania_ciudad = models.CharField(null=True, max_length=50)
    compania_email = models.CharField(null=True, max_length=50)
    
    # HUESPEDES #
    hospedaje_deseado = models.CharField(null=True, max_length=50)
    cotizado = models.IntegerField(null=True)
    solicitado = models.IntegerField(null=True)
    num_hues= models.IntegerField(null=True)
    num_habt = models.IntegerField(null=True)
    
    # DATOS EMPLEADO # 
    empleados = models.CharField(null=False, max_length=50)
    telefono = models.IntegerField(null=False)
    
    # EXTRA # 
    solicitud = models.CharField(null=False, max_length=50)
    observaciones = models.CharField(null=False, max_length=50)

    class Meta:
        db_table = 'reserva'