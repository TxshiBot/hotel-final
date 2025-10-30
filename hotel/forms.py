from django import forms 
from django.utils import timezone
from django.core.exceptions import ValidationError


# ---- MODELS ---- #
from hotel.models import Reservas
from hotel.models import Categorias
from hotel.models import Habitaciones
from hotel.models import Registro_Huespedes

class ReservarForm(forms.ModelForm):

    hospedaje_deseado = forms.ChoiceField(
        choices=[], 
        required=False, 
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        # ... (tu lógica __init__ existente se mantiene igual) ...
        super().__init__(*args, **kwargs)
        
        opcionales = (
            'telefono_oficina', 'hospedaje_deseado', 'cotizado', 'solicitado',
            'num_hues', 'num_habt',
            'nombre_compania', 'compania_domicilio', 'compania_ciudad', 
            'compania_email', 'solicitud', 'observaciones',
            'huesped_principal'
        )
        for campo in opcionales:
            if campo in self.fields:
                self.fields[campo].required = False
        
        if 'huesped_principal' in self.fields:
            self.fields['huesped_principal'].label_from_instance = lambda obj: f"{obj.nombre} {obj.apellido} ({obj.identificacion})"
            self.fields['huesped_principal'].queryset = Registro_Huespedes.objects.order_by('apellido', 'nombre')
            
        try:
            categoria_choices = [("", "Seleccionar tipo...")]
            categorias = Categorias.objects.all().order_by('tipo_hab')
            for cat in categorias:
                categoria_choices.append((cat.tipo_hab, cat.tipo_hab)) 
            self.fields['hospedaje_deseado'].choices = categoria_choices
        except Exception as e:
            self.fields['hospedaje_deseado'].choices = [("", f"Error al cargar categorías: {e}")]
    

    class Meta:
        model = Reservas
        fields = (
            'huesped_principal', 
            'apellido', 'nombre', 'identificacion', 'email', 'domicilio',
            'ciudad', 'departamento', 'telefono_domicilio',
            'check_in', 'check_out', 
            'companion', 'formadepago', # <-- Campo
            'empleados', 'telefono',
            'telefono_oficina', 'hospedaje_deseado', 
            'cotizado', 'solicitado',
            'num_hues', 'num_habt',
            'nombre_compania', 'compania_domicilio', 'compania_ciudad', 
            'compania_email', 
            'solicitud', 'observaciones' 
        )

        widgets = {
            'huesped_principal': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'}
            ),
            'check_out': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'}
            ),
            
            # --- ¡AQUÍ ESTÁ LA CORRECCIÓN DE ESTILO! ---
            'formadepago': forms.Select(attrs={'class': 'form-select'}),
        }
        
        labels = {
            'huesped_principal': 'Buscar Huésped Registrado (Opcional)',
        }

    def clean(self):
        # ... (tu método clean() se mantiene igual) ...
        cleaned_data = super().clean()
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")
        
        if check_in and check_out:
            if check_out <= check_in:
                self.add_error('check_out', "La fecha de salida debe ser posterior a la fecha de llegada.")
            
            if check_in.date() < timezone.now().date():
                self.add_error('check_in', "No se pueden registrar reservas para fechas pasadas.")
                
        return cleaned_data


# En forms.py

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categorias
        fields = [
            'tipo_hab', 
            'precio_base', # <-- Campo
            'descripcion', 
            'camas_matrimoniales', 
            'camas_individuales', 
            'especiales'
        ]
        widgets = {
            'tipo_hab': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Ej: Suite Presidencial'
            }),
            
            # --- ¡WIDGET ACTUALIZADO CON STEP! ---
            'precio_base': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: 150000',
                'min': '0',
                'step': '1000' # <-- ¡REQUERIMIENTO CUMPLIDO!
            }),
            # --- FIN DE LA ACTUALIZACIÓN ---
            
            'descripcion': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 3, 
                'placeholder': 'Descripción breve...'
            }),
            'camas_matrimoniales': forms.NumberInput(attrs={
                'class': 'form-input', 'min': 0
            }),
            'camas_individuales': forms.NumberInput(attrs={
                'class': 'form-input', 'min': 0
            }),
            'especiales': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 3, 
                'placeholder': 'Ej: Balcón, Jacuzzi...'
            }),
        }
        labels = {
            'tipo_hab': 'Nombre de la Categoría',
            'precio_base': 'Precio Base (COP)', # <-- REQUERIMIENTO CUMPLIDO
            'camas_matrimoniales': 'Camas Matrimoniales',
            'camas_individuales': 'Camas Individuales',
            'especiales': 'Características Especiales',
        }


class HabitacionForm(forms.ModelForm):
    class Meta:
        model = Habitaciones
        fields = ['numero', 'tipo', 'adicional_precio', 'estado'] # <-- CAMBIADO
        widgets = {
            'numero': forms.TextInput(attrs={
                'placeholder': 'Ej: 101', 'maxlength': '3', 
                'pattern': '[0-9]{1,3}', 'title': 'Ingrese un número de habitación de hasta 3 dígitos.'
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}), 
            # --- WIDGET CAMBIADO ---
            'adicional_precio': forms.NumberInput(attrs={
                'placeholder': 'Ej: 50000 (por vista)', 
                'min': '0',
                'step': '1000' 
            }),
            'estado': forms.RadioSelect(attrs={'class': 'd-none'}), 
        }
        labels = {
            'numero': 'Número de Habitación',
            'tipo': 'Categoría',
            'adicional_precio': 'Adicional al Precio Base (COP)', # <-- CAMBIADO
            'estado': 'Estado Inicial',
        }
        field_classes = {
            'tipo': forms.ModelChoiceField, 
        }


class HuespedForm(forms.ModelForm):
    # Definir choices para tipo_documento y razon (opcional pero recomendado)
    TIPO_DOCUMENTO_CHOICES = [
        ('', 'Seleccionar...'), # Opción vacía
        ('CC', 'Cédula de Ciudadanía'),
        ('PPT', 'Cédula de Extranjería'),
        ('PA', 'Pasaporte'),
        ('TI', 'Tarjeta de Identidad'),
        ('NIT', 'NIT (Empresa)'),
        ('Otro', 'Otro'),
    ]
    RAZON_VIAJE_CHOICES = [
         ('', 'Seleccionar...'),
        ('Turismo', 'Turismo'),
        ('Negocios', 'Negocios'),
        ('Evento', 'Evento/Conferencia'),
        ('Familiar', 'Visita Familiar'),
        ('Otro', 'Otro'),
    ]

    # Sobrescribir campos para usar choices o widgets específicos
    tipo_documento = forms.ChoiceField(choices=TIPO_DOCUMENTO_CHOICES, required=True, widget=forms.Select(attrs={'class': 'form-select'}))
    razon = forms.ChoiceField(choices=RAZON_VIAJE_CHOICES, required=True, label="Razón del Viaje", widget=forms.Select(attrs={'class': 'form-select'}))
    # Usar widget de fecha para fecha_nacimiento
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}), required=False)
    # Cambiar 'contacto' por campos específicos (más robusto)
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono de Contacto", widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 3001234567'}))
    email = forms.EmailField(max_length=254, required=False, label="Email de Contacto", widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'correo@ejemplo.com'}))


    class Meta:
        model = Registro_Huespedes
        # Lista de campos a incluir en el formulario
        fields = [
            'nombre', 'apellido', 'tipo_documento', 'identificacion',
            'procedencia', 'razon',
            'telefono', 'email', # Usar los campos separados en lugar de 'contacto'
            'fecha_nacimiento', 'nacionalidad', 'genero',
            'preferencias',
        ]
        # Excluir campos automáticos
        exclude = ['fecha_registro', 'ultima_actualizacion', 'contacto'] # Excluimos 'contacto' original

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nombres completos'}),
            'apellido': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Apellidos completos'}),
            # 'tipo_documento': forms.Select(attrs={'class': 'form-select'}), # Redefinido arriba con choices
            'identificacion': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Número de documento'}), # Mantenido como NumberInput por ahora
            'procedencia': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ciudad y/o País'}),
            # 'razon': forms.Select(attrs={'class': 'form-select'}), # Redefinido arriba con choices
            'nacionalidad': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Colombiana'}),
            'genero': forms.Select(attrs={'class': 'form-select'}), # Django usa los choices del modelo
            'preferencias': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Alergias, piso preferido, etc.'}),
        }
        labels = {
            'tipo_hab': 'Nombre de la Categoría',
            'tipo_documento': 'Tipo de Documento',
            'identificacion': 'Número de Documento',
            'procedencia': 'Lugar de Procedencia',
            'razon': 'Razón del Viaje',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'nacionalidad': 'Nacionalidad',
            'genero': 'Género',
            'preferencias': 'Preferencias / Notas',
        }

    # Limpieza/Validación adicional (opcional)
    def clean_identificacion(self):
        identificacion = self.cleaned_data.get('identificacion')
        # Aquí podrías añadir validaciones, como asegurar que sea numérico si se mantiene IntegerField
        # O verificar unicidad si no lo pusiste en el modelo
        return identificacion

    # Lógica para manejar 'contacto' si decides NO separarlo (menos recomendado)
    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     # Combinar teléfono y email en el campo 'contacto' si fuera necesario
    #     # instance.contacto = f"Tel: {self.cleaned_data.get('telefono', '')} / Email: {self.cleaned_data.get('email', '')}"
    #     if commit:
    #         instance.save()
    #     return instance