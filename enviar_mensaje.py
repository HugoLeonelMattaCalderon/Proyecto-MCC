from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time

# Configuración de Selenium para WhatsApp Web
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")

driver = webdriver.Chrome(options=options)
driver.get("https://web.whatsapp.com/")
print("Escanea el código QR para iniciar sesión en WhatsApp Web...")

# Esperar a que WhatsApp Web esté completamente cargado
try:
    wait = WebDriverWait(driver, 60)
    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true' and @data-tab='3']")))
    print("WhatsApp Web sincronizado correctamente. Continuando...")
except Exception as e:
    print(f"Error al sincronizar WhatsApp Web: {e}")
    driver.quit()
    exit()

# Verificar si el archivo de mensajes existe
if not os.path.exists("mensajes_seleccionados.txt"):
    print("El archivo 'mensajes_seleccionados.txt' no existe. Verifica que el sistema lo haya generado correctamente.")
    driver.quit()
    exit()

# Leer los datos seleccionados desde el archivo temporal
print("Leyendo destinatarios y mensajes...")
with open("mensajes_seleccionados.txt", "r") as file:
    for line in file:
        try:
            telefono, mensaje = line.strip().split("|")
            if not telefono.startswith("+"):
                telefono = f"502{telefono}"  # Agregar código de país si no está presente
            print(f"Enviando mensaje a {telefono}...")

            # Navegar a la URL de WhatsApp Web con el mensaje prellenado
            driver.get(f"https://web.whatsapp.com/send?phone={telefono}&text={mensaje}")

            # Esperar a que el cuadro de mensaje esté disponible
            message_box = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true' and @aria-placeholder='Escribe un mensaje']"))
            )
            time.sleep(1)  # Pausa breve para evitar errores
            message_box.send_keys(Keys.ENTER)
            time.sleep(2)  # Esperar a que el mensaje se envíe

            print(f"Mensaje enviado a {telefono}")
        except Exception as e:
            print(f"No se pudo enviar mensaje a {telefono}: {e}")
            continue

print("Todos los mensajes han sido enviados.")
input("Presiona Enter para cerrar el navegador...")
driver.quit()
