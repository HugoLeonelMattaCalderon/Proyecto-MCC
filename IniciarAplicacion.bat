@echo off
REM Cambiar al directorio del proyecto
cd /d C:\Users\Usuario\Desktop\Proyecto MCC

REM Activar el entorno virtual
call venv\Scripts\activate

REM Ejecutar la aplicación
start /b python app.py

REM Esperar un momento para que el servidor inicie
timeout 5 >nul

REM Abrir el navegador en la URL de la aplicación
start http://127.0.0.1:5000

REM Mantener la ventana abierta en caso de errores
pause
