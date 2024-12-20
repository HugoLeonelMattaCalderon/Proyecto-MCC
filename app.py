from flask import Flask, render_template, request, redirect, url_for, flash
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from datetime import datetime
import subprocess
import os
import json

app = Flask(__name__)  # Crear la aplicación Flask
app.secret_key = "secreto"  # Clave para manejar mensajes temporales (flash)

# Configuración de Google Sheets API
# 1. Define los permisos necesarios para acceder a las hojas de cálculo de Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 2. Carga las credenciales desde una variable de entorno (configuración segura en Render)
credentials_json = os.getenv("GOOGLE_CREDENTIALS")
if credentials_json:  # Si las credenciales existen...
    credentials_dict = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
else:
    raise Exception("No se encontró la variable de entorno GOOGLE_CREDENTIALS")  # Error si no hay credenciales

# 3. Conecta con Google Sheets
client = gspread.authorize(creds)
sheet = client.open("Hermanos_MCC").sheet1  # Abre una hoja de cálculo llamada "Hermanos_MCC"

# Ruta principal
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":  # Si el usuario envió el formulario para guardar asistencias
        asistencias = request.form.getlist("asistio")  # Lista de IDs de hermanos que asistieron
        fecha_actual = datetime.now().strftime("%Y-%m-%d")  # Fecha actual

        # Verifica si la fecha actual ya está en la hoja. Si no, la agrega como nueva columna
        encabezados = sheet.row_values(1)
        if fecha_actual not in encabezados:
            sheet.update_cell(1, len(encabezados) + 1, fecha_actual)

        # Marca la asistencia como "Sí" o "No" en la hoja para cada hermano
        data = sheet.get_all_records()
        for i, row in enumerate(data, start=2):
            valor = "Sí" if str(row["ID"]) in asistencias else "No"
            sheet.update_cell(i, len(encabezados), valor)

        flash("Asistencias guardadas correctamente.")  # Mensaje de confirmación
        return redirect(url_for("index"))  # Recarga la página principal

    data = sheet.get_all_records()  # Obtiene todos los datos de la hoja para mostrar
    return render_template("index.html", hermanos=data)  # Renderiza el HTML con los datos

# Ruta: Enviar mensajes a los inasistentes
@app.route("/enviar_mensajes_asistencia", methods=["POST"])
def enviar_mensajes_asistencia():
    # Encuentra la fecha más reciente de asistencia
    encabezados = sheet.row_values(1)
    fecha_mas_reciente = max([h for h in encabezados if h.startswith("202")], key=lambda d: datetime.strptime(d, "%Y-%m-%d"))
    
    # Filtra los hermanos que no asistieron
    data = sheet.get_all_records()
    hermanos_a_enviar = [h for h in data if h[fecha_mas_reciente].strip().lower() == "no"]

    # Crea un archivo temporal con los mensajes que se enviarán
    with open("mensajes_seleccionados.txt", "w") as file:
        for h in hermanos_a_enviar:
            telefono = h["TELEFONO"]
            mensaje = h.get("MENSAJE", "Mensaje no disponible")
            file.write(f"{telefono}|{mensaje}\n")

    # Ejecuta un script externo (enviar_mensaje.py) para enviar los mensajes
    try:
        subprocess.Popen(["python", "enviar_mensaje.py"], shell=True)
        flash("Mensajes enviados a los hermanos que no asistieron.")
    except Exception as e:
        flash(f"Error al enviar mensajes: {e}")

    return redirect(url_for("index"))

# Ruta: Enviar mensajes personalizados
@app.route("/enviar_mensajes_personalizados", methods=["POST"])
def enviar_mensajes_personalizados():
    seleccionados = request.form.getlist("seleccionados")
    mensaje_personalizado = request.form.get("mensaje_personalizado")

    if not seleccionados:
        flash("No seleccionaste a ningún hermano.")
        return redirect(url_for("index"))

    if not mensaje_personalizado:
        flash("El mensaje personalizado no puede estar vacío.")
        return redirect(url_for("index"))

    data = sheet.get_all_records()
    hermanos_a_enviar = [h for h in data if str(h["ID"]) in seleccionados]

    # Guardar los datos en un archivo temporal
    with open("mensajes_seleccionados.txt", "w") as file:
        for h in hermanos_a_enviar:
            telefono = h["TELEFONO"]
            file.write(f"{telefono}|{mensaje_personalizado}\n")
        print("Contenido del archivo 'mensajes_seleccionados.txt':")
        with open("mensajes_seleccionados.txt", "r") as debug_file:
            print(debug_file.read())

    try:
        subprocess.Popen(["python", "enviar_mensaje.py"], shell=True)
        flash("Mensajes personalizados enviados correctamente.")
    except Exception as e:
        flash(f"Error al enviar mensajes personalizados: {e}")

    return redirect(url_for("index"))

# Rutas para agregar, editar, actualizar, eliminar hermanos
@app.route("/agregar", methods=["POST"])
def agregar():
    nombre = request.form["nombre"]
    telefono = request.form["telefono"]
    mensaje = request.form["mensaje"]
    nuevo_id = len(sheet.get_all_values())

    nueva_fila = [nuevo_id, nombre, telefono, mensaje, 0]
    encabezados = sheet.row_values(1)
    while len(nueva_fila) < len(encabezados):
        nueva_fila.append("")
    sheet.append_row(nueva_fila)
    flash("Hermano agregado correctamente.")
    return redirect(url_for("index"))

@app.route("/editar/<id>", methods=["GET", "POST"])
def editar(id):
    data = sheet.get_all_records()
    hermano = next((h for h in data if str(h["ID"]) == id), None)

    if not hermano:
        flash("Hermano no encontrado.")
        return redirect(url_for("index"))

    return render_template("editar.html", hermano=hermano)

@app.route("/actualizar/<id>", methods=["POST"])
def actualizar(id):
    nombre = request.form["nombre"]
    telefono = request.form["telefono"]
    mensaje = request.form["mensaje"]

    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        if str(row["ID"]) == id:
            sheet.update_cell(i, 2, nombre)
            sheet.update_cell(i, 3, telefono)
            sheet.update_cell(i, 4, mensaje)
            flash("Hermano actualizado correctamente.")
            return redirect(url_for("index"))

    flash("No se pudo actualizar el hermano.")
    return redirect(url_for("index"))

@app.route("/eliminar/<id>", methods=["GET"])
def eliminar(id):
    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        if str(row["ID"]) == id:
            sheet.delete_rows(i)
            flash(f"Hermano con ID {id} eliminado correctamente.")
            return redirect(url_for("index"))

    flash(f"No se encontró el hermano con ID {id}.")
    return redirect(url_for("index"))

# Nueva Ruta: Probar Selenium
@app.route("/test_selenium")
def test_selenium():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import chromedriver_autoinstaller

    # Instalar automáticamente el driver de Chrome
    chromedriver_autoinstaller.install()

    # Configuración de Selenium
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    try:
        # Inicia el navegador
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        return f"Selenium funcionó correctamente. Título de la página: {title}"
    except Exception as e:
        return f"Error al probar Selenium: {e}"


if __name__ == "__main__":
    app.run(debug=True)
