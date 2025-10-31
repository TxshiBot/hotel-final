from django.db import models
from django.utils import timezone

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
    tipo_hab = models.CharField(max_length=100, null=False, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    precio_base = models.IntegerField(null=False, default=100000) 
    
    camas_matrimoniales = models.PositiveIntegerField(default=0)
    camas_individuales = models.PositiveIntegerField(default=0)
    especiales = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'categorias'
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.tipo_hab


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
    
    adicional_precio = models.IntegerField(
        null=False, 
        default=0, 
        help_text="Valor extra por vistas, balcón, etc. (se suma al precio base de la categoría)"
    )

    class Meta:
        db_table = 'habitaciones'

    def __str__(self):
        return f"Hab. {self.numero} ({self.tipo.tipo_hab})"


class Reservas(models.Model):
    
    FORMA_PAGO_CHOICES = [
        ('Efectivo', 'Efectivo'),
        ('Tarjeta de Credito', 'Tarjeta de Crédito'),
        ('Transferencia', 'Transferencia Bancaria'),
        ('cobrar_compania', 'Cobrar a Compañía'),
        ('Otro', 'Otro'),
    ]
    
    ESTANCIA_CHOICES = [
        ('Pendiente', 'Pendiente (No ha llegado)'),
        ('Activa', 'Activa (Checked-in)'),
        ('Completada', 'Completada (Checked-out)'),
    ]
    
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
    
    formadepago = models.CharField(
        null=False, 
        max_length=50,
        choices=FORMA_PAGO_CHOICES,
        default='Efectivo'
    )
    
    check_in = models.DateTimeField(null=False, max_length=50)
    check_out = models.DateTimeField(null=False, max_length=50)
    
    num_habt = models.IntegerField(null=True, blank=True) 

    # OPCIONAL: COMPAÑÍA
    nombre_compania = models.CharField(null=True, max_length=50, blank=True)
    compania_domicilio = models.CharField(null=True, max_length=50, blank=True)
    compania_ciudad = models.CharField(null=True, max_length=50, blank=True)
    compania_email = models.CharField(null=True, max_length=50, blank=True)
    
    # HUESPEDES
    hospedaje_deseado = models.CharField(null=True, max_length=50, blank=True)
    solicitado = models.IntegerField(null=True, blank=True) 
    
    # DATOS EMPLEADO
    empleados = models.CharField(null=False, max_length=50)
    telefono = models.CharField(null=False, max_length=10, blank=True)
    
    # EXTRA
    solicitud = models.CharField(null=True, max_length=50, blank=True)
    observaciones = models.CharField(null=True, max_length=50, blank=True)
    confirmado = models.CharField(null=True, max_length=50, default='Pendiente', blank=True)

    # --- CAMPO HUESPED PRINCIPAL --- #
    huesped_principal = models.ForeignKey(
        Registro_Huespedes,
        on_delete=models.SET_NULL,
        null=True, 
        blank=True, 
        related_name='reservas_como_principal' # El que paga
    )

    acompanantes = models.ManyToManyField(
        Registro_Huespedes,
        blank=True,
        related_name='reservas_como_acompanante' 
    )

    habitaciones_asignadas = models.ManyToManyField(
        Habitaciones,
        blank=True,
        related_name='reservas_asignadas'
    )

    estado_estancia = models.CharField(
        max_length=20, 
        choices=ESTANCIA_CHOICES, 
        default='Pendiente'
    )

    class Meta:
        db_table = 'reserva'

    def __str__(self):
        return f"Reserva #{self.id} ({self.nombre} {self.apellido})"


class Factura(models.Model):
    id = models.AutoField(primary_key=True)
    
    reserva = models.OneToOneField(
        Reservas, 
        on_delete=models.PROTECT, 
        related_name='factura'
    )
    huesped = models.ForeignKey(
        Registro_Huespedes, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='facturas'
    )
    
    # --- Datos de la Factura y Cálculos --- #
    fecha_emision = models.DateTimeField(default=timezone.now)
    total_noches = models.IntegerField(default=0)
    
    # 1. Alojamiento #
    subtotal_alojamiento = models.IntegerField(null=False) 
    
    # 2. Consumos #
    subtotal_consumos = models.IntegerField(null=False, default=0)
    
    # 3. Totales #
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
        verbose_name_plural = "Facturas"

    def __str__(self):
        return f"Factura #{self.id} (Reserva #{self.reserva.id})"


class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    precio = models.IntegerField(null=False) 
    stock_disponible = models.PositiveIntegerField(default=0)
    esta_activo = models.BooleanField(default=True)
    
    foto = models.CharField(max_length=255, blank=True, null=True) 
    
    class Meta:
        db_table = 'productos'
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} (${self.precio})"


class Consumo(models.Model):
    id = models.AutoField(primary_key=True)
    reserva = models.ForeignKey(Reservas, on_delete=models.CASCADE, related_name='consumos')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    
    precio_en_el_momento = models.IntegerField() 
    
    fecha_consumo = models.DateTimeField(auto_now_add=True)
    
    pagado_inmediatamente = models.BooleanField(default=False)

    class Meta:
        db_table = 'consumos'
        verbose_name_plural = "Consumos"

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} para Reserva #{self.reserva.id}"