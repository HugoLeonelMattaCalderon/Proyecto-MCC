from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
try:
    driver.get("https://www.google.com")
    print("Página cargada con título:", driver.title)
except Exception as e:
    print("Error al cargar la página:", e)
finally:
    driver.quit()
