from flask import Flask, render_template, request, redirect, url_for, flash
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from datetime import datetime
import subprocess
import os
import json

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

app = Flask(__name__)
app.secret_key = "secreto"

# ---------------------------------------------------------------------
# Configuración de la base de datos para autenticación
# ---------------------------------------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ---------------------------------------------------------------------
# Modelo de usuario para autenticación, con campo "role"
# ---------------------------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='user')  # Campo para el rol: "admin" o "user"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------
# Configuración de Google Sheets API
# ---------------------------------------------------------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if os.getenv("GOOGLE_CREDENTIALS"):
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    credentials_dict = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
else:
    credentials_path = "credenciales.json"
    if os.path.exists(credentials_path):
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    else:
        raise Exception("No se encontró el archivo de credenciales.")

client = gspread.authorize(creds)
sheet = client.open("Hermanos_MCC").sheet1


# ---------------------------------------------------------------------
# Rutas de autenticación
# ---------------------------------------------------------------------
@app.route('/admin/users', methods=['GET'])
@login_required
def admin_users():
    # Verifica si el usuario actual es admin
    if current_user.role != "admin":
        flash("No tienes permisos para acceder a esta página.", "danger")
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

# ---------------------------------------------------------------------
# Ruta para eliminar usuarios
# ---------------------------------------------------------------------
@app.route('/admin/delete_user/<int:id>', methods=['GET'])
@login_required
def delete_user(id):
    if current_user.role != "admin":
        flash("No tienes permisos para realizar esta acción.", "danger")
        return redirect(url_for('index'))

    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"Usuario {user.username} eliminado correctamente.", "success")
    else:
        flash("Usuario no encontrado.", "danger")
    return redirect(url_for('admin_users'))

# ---------------------------------------------------------------------
# Ruta para crear nuevos usuarios
# ---------------------------------------------------------------------
@app.route('/admin/create_user', methods=['POST'])
@login_required
def create_user():
    if current_user.role != "admin":
        flash("No tienes permisos para realizar esta acción.", "danger")
        return redirect(url_for('index'))

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash("El nombre de usuario y la contraseña son obligatorios.", "danger")
        return redirect(url_for('admin_users'))

    # Verifica si el usuario ya existe
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("El nombre de usuario ya está en uso.", "danger")
        return redirect(url_for('admin_users'))

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_password, role='user')
    db.session.add(new_user)
    db.session.commit()
    flash(f"Usuario {username} creado correctamente.", "success")
    return redirect(url_for('admin_users'))

# ---------------------------------------------------------------------
# Ruta para cambiar el rol de un usuario (admin <-> user)
# ---------------------------------------------------------------------
@app.route('/admin/set_role/<int:user_id>/<role>', methods=['GET'])
@login_required
def set_role(user_id, role):
    # Solo el usuario 'admin' puede cambiar roles
    if current_user.role != "admin":
        flash("No tienes permisos para realizar esta acción.", "danger")
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if not user:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('admin_users'))

    # Verifica que el rol sea válido
    if role not in ['admin', 'user']:
        flash("Rol no válido.", "danger")
        return redirect(url_for('admin_users'))

    # Actualiza el rol del usuario
    user.role = role
    db.session.commit()

    flash(f"Rol del usuario {user.username} cambiado a {role}.", "success")
    return redirect(url_for('admin_users'))

# ---------------------------------------------------------------------
# Ruta para crear un usuario administrador (por ejemplo, el superadmin)
# ---------------------------------------------------------------------
@app.route('/create_admin', methods=['GET'])
def create_admin():
    # Cambia estos datos según sea necesario
    username = "admin@example.com"
    password = "adminpassword"

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_password, role='admin')
    db.session.add(new_user)
    db.session.commit()
    return "Usuario administrador creado con éxito. ¡Asegúrate de guardar la contraseña!"

# ---------------------------------------------------------------------
# Ruta de login
# ---------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')

# ---------------------------------------------------------------------
# Ruta de logout
# ---------------------------------------------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------------------------------------------------------------------
# Ruta principal protegida
# ---------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        asistencias = request.form.getlist("asistio")
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        encabezados = sheet.row_values(1)
        if fecha_actual not in encabezados:
            sheet.update_cell(1, len(encabezados) + 1, fecha_actual)

        data = sheet.get_all_records()
        for i, row in enumerate(data, start=2):
            valor = "Sí" if str(row["ID"]) in asistencias else "No"
            sheet.update_cell(i, len(encabezados), valor)

        flash("Asistencias guardadas correctamente.")
        return redirect(url_for("index"))

    data = sheet.get_all_records()
    # Garantizar que cada hermano tenga un ID
    for i, row in enumerate(data):
        row["ID"] = i + 1
    return render_template("index.html", hermanos=data)

# ---------------------------------------------------------------------
# Ruta para enviar mensajes a inasistentes
# ---------------------------------------------------------------------
@app.route("/enviar_mensajes_asistencia", methods=["POST"])
@login_required
def enviar_mensajes_asistencia():
    encabezados = sheet.row_values(1)
    fecha_mas_reciente = max(
        [h for h in encabezados if h.startswith("202")],
        key=lambda d: datetime.strptime(d, "%Y-%m-%d")
    )
    data = sheet.get_all_records()
    hermanos_a_enviar = [
        h for h in data if h[fecha_mas_reciente].strip().lower() == "no"
    ]

    with open("mensajes_seleccionados.txt", "w") as file:
        for h in hermanos_a_enviar:
            telefono = h["TELEFONO"]
            mensaje = h.get("MENSAJE", "Mensaje no disponible")
            file.write(f"{telefono}|{mensaje}\n")

    try:
        subprocess.Popen(["python", "enviar_mensaje.py"], shell=True)
        flash("Mensajes enviados a los hermanos que no asistieron.")
    except Exception as e:
        flash(f"Error al enviar mensajes: {e}")

    return redirect(url_for("index"))

# ---------------------------------------------------------------------
# Ruta para enviar mensajes personalizados
# ---------------------------------------------------------------------
@app.route("/enviar_mensajes_personalizados", methods=["POST"])
@login_required
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

    with open("mensajes_seleccionados.txt", "w") as file:
        for h in hermanos_a_enviar:
            telefono = h["TELEFONO"]
            file.write(f"{telefono}|{mensaje_personalizado}\n")

    try:
        subprocess.Popen(["python", "enviar_mensaje.py"], shell=True)
        flash("Mensajes personalizados enviados correctamente.")
    except Exception as e:
        flash(f"Error al enviar mensajes personalizados: {e}")

    return redirect(url_for("index"))

# ---------------------------------------------------------------------
# Ruta para editar un hermano
# ---------------------------------------------------------------------
@app.route("/editar/<id>", methods=["GET", "POST"])
@login_required
def editar(id):
    data = sheet.get_all_records()
    hermano = next((h for h in data if str(h["ID"]) == id), None)

    if not hermano:
        flash("Hermano no encontrado.")
        return redirect(url_for("index"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        mensaje = request.form["mensaje"]

        for i, row in enumerate(data, start=2):
            if str(row["ID"]) == id:
                sheet.update_cell(i, 2, nombre)
                sheet.update_cell(i, 3, telefono)
                sheet.update_cell(i, 4, mensaje)
                flash("Hermano actualizado correctamente.")
                return redirect(url_for("index"))

    return render_template("editar.html", hermano=hermano)

# ---------------------------------------------------------------------
# Ruta para eliminar un hermano (en la hoja de cálculo)
# ---------------------------------------------------------------------
@app.route("/eliminar/<id>", methods=["GET"])
@login_required
def eliminar(id):
    data = sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        if str(row["ID"]) == id:
            sheet.delete_rows(i)
            flash(f"Hermano con ID {id} eliminado correctamente.")
            return redirect(url_for("index"))

    flash(f"No se encontró el hermano con ID {id}.")
    return redirect(url_for("index"))

# ---------------------------------------------------------------------
# Ruta para agregar un hermano (en la hoja de cálculo)
# ---------------------------------------------------------------------
@app.route("/agregar", methods=["POST"])
@login_required
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

# ---------------------------------------------------------------------
# Crear base de datos de usuarios al iniciar
# ---------------------------------------------------------------------
with app.app_context():
    db.create_all()

@app.route('/list_users', methods=['GET'])
def list_users():
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append(f"ID: {user.id}, Username: {user.username}, Role: {user.role}")
    return "<br>".join(user_list)


# ---------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

