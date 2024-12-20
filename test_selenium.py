from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Ruta del ChromeDriver descargado
driver_path = r"C:\Selenium\chromedriver.exe"  # Asegúrate de que esta ruta sea correcta

# Ruta del perfil de usuario de Chrome
profile_path = r"C:\Users\Usuario\AppData\Local\Google\Chrome\User Data"

# Configuración de ChromeOptions
options = Options()
options.add_argument(f"--user-data-dir={profile_path}")  # Ruta al perfil de usuario
options.add_argument("--profile-directory=Default")      # Usa el perfil predeterminado
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")

# Configura el servicio de ChromeDriver
service = Service(driver_path)

# Inicializa el navegador con ChromeDriver
driver = webdriver.Chrome(service=service, options=options)

# Abre WhatsApp Web
driver.get("https://web.whatsapp.com/")
print("WhatsApp Web abierto.")
