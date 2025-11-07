ESTRUCTURA DEL PROYECTO:



hotel/

├── .idea/

├── docs/

├── hotel/

│   ├── \_\_pycache\_\_/

│   ├── migrations/

│   ├── public/

│   ├── templates/

│   ├── \_\_init\_\_.py

│   ├── asgi.py

│   ├── forms.py

│   ├── models.py

│   ├── settings.py

│   ├── urls.py

│   ├── views.py

│   └── wsgi.py

├── .gitignore

├── manage.py

├── README.md

└── requirements.txt





DESCRIPCION:



models.py:



Modelo. 



Define la estructura de la base de datos (tablas, campos y relaciones). Es la capa de datos.





views.py



Controlador / Vista.



Contiene la lógica de negocio de la aplicación. Recibe la solicitud del usuario, interactúa con el Modelo y selecciona la Plantilla a renderizar.





urls.py:



Vista / Template 



Contiene los archivos HTML que definen la interfaz de usuario. Recibe datos de la Vista (views.py) y los presenta al usuario.





forms.py:



Manejo de Entradas.



Define la estructura de los formularios web para la captura y validación de datos del usuario antes de ser procesados por la Vista.





settings.py:



Configuración.



Almacena la configuración global del proyecto (conexión a la base de datos, middlewares, aplicaciones instaladas, etc.).





manage.py:



Utilidad.



Herramienta de línea de comandos para tareas administrativas (ejecutar el servidor, migraciones, crear superusuarios, etc.).





requirements.txt:



Requerimientos.



Requerimientos, contiene módulos de Python para que el programa funcione.

