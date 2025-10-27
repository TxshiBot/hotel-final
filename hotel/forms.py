from django import forms 


# ---- MODELS ---- #
from hotel.models import Reservas


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
            'empleados', 'telefono', 'solicitud', 'observaciones',
            
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
            'compania_email',
        )
        
        # Adicionalmente, los campos marcados como obligatorios en tu formulario original
        # (pero que son null=True en el modelo) DEBERÍAN ser opcionales:
        # 'solicitud' y 'observaciones' no tienen null=True/blank=True en tu modelo,
        # por lo que el formulario los marcará como 'required=True' por defecto.
        
        for campo in opcionales:
            if campo in self.fields:
                self.fields[campo].required = False