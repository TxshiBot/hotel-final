from django.db import models

class Registro_Huespedes(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    apellido = models.CharField(max_length=100, null=False)
    tipo_documento = models.CharField(max_length=100, null=False)
    identificacion = models.CharField(max_length=10, null=False)
    procedencia = models.CharField(max_length=200, null=False)
    razon = models.CharField(max_length=255, null=False)
    telefono = models.CharField(max_length=10, null=True)
    email = models.CharField(max_length=30, null=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    nacionalidad = models.CharField(max_length=100, blank=True, null=True)
    genero = models.CharField(max_length=20, choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')], blank=True, null=True)
    preferencias = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'registro_huespedes'

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Categorias(models.Model):
    id = models.AutoField(primary_key=True)
    tipo_hab = models.CharField(max_length=100, null=False, unique=True) # Este es el nombre que queremos mostrar
    descripcion = models.TextField(blank=True, null=True)
    camas_matrimoniales = models.PositiveIntegerField(default=0)
    camas_individuales = models.PositiveIntegerField(default=0)
    especiales = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'categorias'
        verbose_name_plural = "Categorias" # Opcional, para el admin

    def __str__(self):
        return self.tipo_hab # Devuelve el valor del campo 'tipo_hab' como representación


class Habitaciones(models.Model):
    id = models.AutoField(primary_key=True)
    ESTADO_CHOICES = [
        ('Disponible', 'Disponible'),
        ('Ocupada', 'Ocupada'),
        ('Limpieza', 'Limpieza'),
        ('Mantenimiento', 'Mantenimiento'),
    ]
    numero = models.CharField(max_length=10, null=False, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Disponible')
    tipo = models.ForeignKey(Categorias, on_delete=models.CASCADE, null=False, blank=True)
    precio = models.IntegerField(null=False)

    class Meta:
        db_table = 'habitaciones'

    def __str__(self):
        return f"Hab. {self.numero} ({self.tipo.tipo_hab})"


class Reservas(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(null=False, max_length=50)
    apellido = models.CharField(null=False, max_length=50)
    ciudad = models.CharField(null=False, max_length=50)
    identificacion = models.IntegerField(blank=True, null=False, default=0)
    telefono_domicilio = models.CharField(null=False, max_length=10, blank=True)
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
    telefono = models.CharField(null=False, max_length=10, blank=True)
    
    # EXTRA # 
    solicitud = models.CharField(null=True, max_length=50)
    observaciones = models.CharField(null=True, max_length=50)
    confirmado = models.CharField(null=True, max_length=50, default='Pendiente')


    # REGISTRO HUESPEDES # 
    huesped_principal = models.ForeignKey(
        Registro_Huespedes,
        on_delete=models.SET_NULL, # Importante: Si se borra el huésped, no borres sus reservas
        null=True, 
        blank=True, 
        related_name='reservas_como_principal' # Para acceder desde el huésped
    )

    # MANY TO MANY - MUCHOS A MUCHOS # 
    habitaciones_asignadas = models.ManyToManyField(
        Habitaciones,
        blank=True, # Una reserva puede existir sin habitaciones asignadas
        related_name='reservas_asignadas' # Para acceder a las reservas desde una habitación
    )

    class Meta:
        db_table = 'reserva'

    def __str__(self):
        return f"Reserva #{self.id} ({self.nombre} {self.apellido})"


class Factura(models.Model):
    id = models.AutoField(primary_key=True)
    
    # --- La conexión clave ---
    reserva = models.OneToOneField(
        Reservas, 
        on_delete=models.PROTECT, # No borrar factura si se borra la reserva
        related_name='factura'
    )
    huesped = models.ForeignKey(
        Registro_Huespedes, 
        on_delete=models.SET_NULL, # A quién se le facturó
        null=True,
        related_name='facturas'
    )
    
    # --- Datos de la Factura ---
    fecha_emision = models.DateTimeField(auto_now_add=True)
    total_noches = models.IntegerField(null=False)
    subtotal_alojamiento = models.IntegerField(null=False) # Usamos IntegerField como en 'precio'
    impuestos = models.IntegerField(null=False, default=0)
    total_facturado = models.IntegerField(null=False)
    
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente de Pago'),
        ('Pagada', 'Pagada'),
        ('Anulada', 'Anulada'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')

    class Meta:
        db_table = 'facturas'

    def __str__(self):
        return f"Factura #{self.id} (Reserva #{self.reserva.id})"