from django import forms 


# ---- MODELS ---- #
from hotel.models import Reservas
from hotel.models import Categorias
from hotel.models import Habitaciones

class ReservarForm(forms.ModelForm):
    
# Contenido de la clase Meta en forms.py
    class Meta:
        model = Reservas
        fields = (
            # Campos obligatorios (ajustados a los nombres EXACTOS del modelo)
            'apellido', 'nombre', 'identificacion', 'email', 'domicilio',
            'ciudad', 'departamento', 'telefono_domicilio',
            'check_in', 'check_out', 'companion', 'formadepago',
            # Nota: Los campos 'num_hues' y 'num_habt' son NULLABLE en el modelo, 
            # pero están en tu lista de "obligatorios". Los movemos al final por ser NULLABLE.
            'empleados', 'telefono',
            
            # Campos Opcionales/NULLABLE (ajustados a los nombres EXACTOS del modelo)
            'telefono_oficina', 'hospedaje_deseado', 'cotizado', 'solicitado',
            'num_hues', 'num_habt',
            'nombre_compania', 'compania_domicilio', 'compania_ciudad', 
            'compania_email', 
            # NOTA: Los campos 'cliente_paga', 'cobrar_compania', 'pago_efectivo', 'pago_tc', 'pago_td'
            #       y 'departamento_compania' NO EXISTEN en tu modelo, por lo que NO se incluyen.
        )

    # Contenido del método __init__ en forms.py
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Campos opcionales (ajustados a los nombres EXACTOS del modelo)
        opcionales = (
            'telefono_oficina', 'hospedaje_deseado', 'cotizado', 'solicitado',
            'num_hues', 'num_habt',
            'nombre_compania', 'compania_domicilio', 'compania_ciudad', 
            'compania_email', 'solicitud', 'observaciones'
        )
        
        # Adicionalmente, los campos marcados como obligatorios en tu formulario original
        # (pero que son null=True en el modelo) DEBERÍAN ser opcionales:
        # 'solicitud' y 'observaciones' no tienen null=True/blank=True en tu modelo,
        # por lo que el formulario los marcará como 'required=True' por defecto.
        
        for campo in opcionales:
            if campo in self.fields:
                self.fields[campo].required = False


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categorias
        fields = [
            'tipo_hab', 
            'descripcion', 
            'camas_matrimoniales', 
            'camas_individuales', 
            'especiales'
        ]
        widgets = {
            'tipo_hab': forms.TextInput(attrs={
                'class': 'form-input', # <-- AÑADIR CLASE
                'placeholder': 'Ej: Suite Presidencial'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-textarea', # <-- AÑADIR CLASE
                'rows': 3, 
                'placeholder': 'Descripción breve...'
            }),
            'camas_matrimoniales': forms.NumberInput(attrs={
                'class': 'form-input', # <-- AÑADIR CLASE (o form-number si tienes estilo específico)
                'min': 0
            }),
            'camas_individuales': forms.NumberInput(attrs={
                'class': 'form-input', # <-- AÑADIR CLASE
                'min': 0
            }),
            'especiales': forms.Textarea(attrs={
                'class': 'form-textarea', # <-- AÑADIR CLASE
                'rows': 3, 
                'placeholder': 'Ej: Balcón, Jacuzzi...'
            }),
        }
        labels = {
            'tipo_hab': 'Nombre de la Categoría',
            'camas_matrimoniales': 'Camas Matrimoniales',
            'camas_individuales': 'Camas Individuales',
            'especiales': 'Características Especiales',
        }


class HabitacionForm(forms.ModelForm):
    class Meta:
        model = Habitaciones
        fields = ['numero', 'tipo', 'precio', 'estado'] 
        widgets = {
            'numero': forms.TextInput(attrs={
                'placeholder': 'Ej: 101', 
                'maxlength': '3', 
                'pattern': '[0-9]{1,3}', 
                'title': 'Ingrese un número de habitación de hasta 3 dígitos.'
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}), 
            'precio': forms.NumberInput(attrs={
                'placeholder': 'Ej: 150000', 
                'min': '0',
                'step': '1000' 
            }),
            'estado': forms.RadioSelect(attrs={'class': 'd-none'}), 
        }
        labels = {
            'numero': 'Número de Habitación',
            'tipo': 'Categoría',
            'precio': 'Precio por Noche (COP)',
            'estado': 'Estado Inicial',
        }
        field_classes = {
            'tipo': forms.ModelChoiceField, 
        }