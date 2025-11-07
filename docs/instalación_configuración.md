Pasos para la instalación y ejecución del programa:



1. Clonar el repositorio remoto



git clone https://github.com/TxshiBot/spirit-of-fire.git



* Acceder a la carpeta:

cd spirit-of-fire.git





2\. Crear entorno virtual



python -m venv env



env\\Scripts\\activate





3\. Instalar dependencias



pip install -r requirements.txt





4\. Configurar settings.py para manejo de base de datos 



En el archivo "settings.py" modificar "DATABASES" con los datos establecidos en la base de datos, ejemplo:



DATABASES = {

&nbsp;   'default': {

&nbsp;       'ENGINE': 'django.db.backends.mysql',

&nbsp;       'NAME': 'nombre\_bd',

&nbsp;       'USER': 'usuario',

&nbsp;       'PASSWORD': 'contraseña',

&nbsp;       'HOST': 'localhost',

&nbsp;       'PORT': '3306',

&nbsp;   }

&nbsp;}





4\. Migrar y ejecutar el servidor



python manage.py makemigrations



python manage.py migrate



python manage.py runserver







