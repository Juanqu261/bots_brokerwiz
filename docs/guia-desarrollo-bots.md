# Guía de Desarrollo de Bots - BrokerWiz

Esta guía proporciona instrucciones completas para desarrollar nuevos bots de cotización compatibles con el sistema BrokerWiz.

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura de Bots](#arquitectura-de-bots)
3. [Estructura de un Bot](#estructura-de-un-bot)
5. [API de BaseBot](#api-de-basebot)
6. [Helpers de Selenium](#helpers-de-selenium)
7. [Handlers Especializados](#handlers-especializados)
8. [Gestión de Sesiones y Cookies](#gestión-de-sesiones-y-cookies)
9. [Manejo de Errores](#manejo-de-errores)
10. [Testing y Debugging](#testing-y-debugging)
11. [Registro del Bot](#registro-del-bot)
12. [Mejores Prácticas](#mejores-prácticas)
13. [Troubleshooting](#troubleshooting)

---

## Introducción

Los bots de BrokerWiz son automatizaciones Selenium que realizan cotizaciones en portales de aseguradoras. Cada bot:

- Hereda de `BaseBot` que proporciona toda la infraestructura necesaria
- Implementa un método `run()` con la lógica específica de la aseguradora
- Se ejecuta de forma asíncrona en workers MQTT
- Maneja sesiones, cookies, errores y reportes automáticamente

### Flujo General

```
MQTT Queue → Worker → Bot Instance → run() → PDF Upload → Success/Retry/DLQ
```

---

## Arquitectura de Bots

### Componentes Principales

```
BaseBot (Orquestador)
├── SeleniumDriverManager (self.selenium)
│   ├── SeleniumHelpers (wait_for, click, type_text, etc.)
│   ├── HumanInteraction (self.human)
│   └── CookiesManager
├── AppWebClient (self.api)
│   ├── upload_pdf()
│   └── report_error()
└── BotExecutionLogger (self.logger)
```


### Jerarquía de Clases

```python
BaseBot
  ├── Propiedades
  │   ├── bot_id: str
  │   ├── job_id: str
  │   ├── payload: dict
  │   ├── selenium: SeleniumDriverManager
  │   ├── api: AppWebClient
  │   ├── logger: Logger
  │   ├── driver: WebDriver (atajo)
  │   └── solicitud_id: str (del payload)
  │
  ├── Métodos Lifecycle
  │   ├── setup() → Inicializar WebDriver
  │   ├── teardown() → Cerrar WebDriver
  │   └── run() → IMPLEMENTAR EN SUBCLASE
  │
  └── Métodos Utilidad
      ├── upload_result(pdf_path) → Subir PDF a API
      └── report_error(code, msg) → Reportar error a API
```

---

## Estructura de un Bot

### Archivo Mínimo

```python
# workers/bots/mi_aseguradora_bot.py

from workers.bots import BaseBot
from selenium.webdriver.common.by import By

class MiAseguradoraBot(BaseBot):
    """Bot de cotización para Mi Aseguradora."""
    
    URL_LOGIN = "https://portal.miaseguradora.com/login"
    COOKIE_DOMAIN = "miaseguradora.com"
    
    def __init__(self, job_id: str, payload: dict):
        super().__init__(bot_id="mi_aseguradora", job_id=job_id, payload=payload)
    
    async def run(self) -> bool:
        """Ejecutar flujo de cotización."""
        try:
            # 1. Navegar
            await self.selenium.get(self.URL_LOGIN)
            
            # 2. Login
            await self._login()
            
            # 3. Cotizar
            await self._fill_quotation()
            
            # 4. Descargar PDF
            pdf_path = await self._download_pdf()
            
            # 5. Subir a API
            return await self.upload_result(pdf_path)
            
        except Exception as e:
            await self.report_error("BOT_ERROR", str(e))
            return False
    
    async def _login(self):
        """Implementar login."""
        pass
    
    async def _fill_quotation(self):
        """Implementar formulario."""
        pass
    
    async def _download_pdf(self):
        """Implementar descarga."""
        pass
```

---

## API de BaseBot

### Propiedades Disponibles

```python
# Identificadores
self.bot_id          # str: ID del bot (ej: "sura")
self.job_id          # str: ID único del job
self.solicitud_id    # str: ID de solicitud (del payload)

# Datos
self.payload         # dict: Datos de cotización desde MQTT

# Componentes
self.selenium        # SeleniumDriverManager: Driver con helpers
self.api             # AppWebClient: Cliente HTTP para API
self.logger          # Logger: Logger configurado
self.driver          # WebDriver: Acceso directo al driver
```

### Métodos Principales

#### `async def setup()`
Inicializa el WebDriver. Llamado automáticamente por el context manager.

```python
# Uso manual (no recomendado)
await bot.setup()
try:
    # ... lógica del bot
finally:
    await bot.teardown()

# Uso recomendado (context manager)
async with bot:
    # setup() se llama automáticamente
    await bot.run()
    # teardown() se llama automáticamente
```

#### `async def teardown()`
Cierra el WebDriver y limpia recursos. Llamado automáticamente por el context manager.

#### `async def run() -> bool`
**DEBE SER IMPLEMENTADO** en cada bot. Contiene la lógica principal de cotización.

```python
async def run(self) -> bool:
    """
    Returns:
        True si cotización exitosa
        False si hubo errores
    """
    pass
```

---

## Helpers de Selenium

El objeto `self.selenium` proporciona todos los métodos necesarios para interactuar con el navegador.

### Navegación

```python
# Navegar a URL
await self.selenium.get("https://portal.com")

# Recargar página
await self.selenium.refresh()

# Navegar atrás/adelante
await self.selenium.back()
await self.selenium.forward()

# Obtener URL actual
url = self.selenium.current_url

# Esperar carga completa
await self.selenium.wait_page_load()
```

### Búsqueda y Espera de Elementos

```python
# Esperar elemento (múltiples condiciones)
element = await self.selenium.wait_for(
    By.CSS_SELECTOR,
    "#mi-elemento",
    timeout=15,
    condition="clickable"  # "presence" | "visible" | "clickable" | "invisible"
)

# Esperar múltiples elementos
elements = await self.selenium.wait_for_all(
    By.CLASS_NAME,
    "item-lista",
    timeout=10
)

# Buscar elemento (sin espera)
element = await self.selenium.find_element(By.ID, "boton")
elements = await self.selenium.find_elements(By.TAG_NAME, "a")
```

### Interacción con Elementos

```python
# Click con scroll automático
await self.selenium.click(element, scroll=True, use_js=False)

# Enviar texto
await self.selenium.type_text(
    element,
    "mi texto",
    clear=True,
    delay=0.05  # delay entre caracteres
)

# Selects (dropdowns)
await self.selenium.select_by_text(select_element, "Opción 1")
await self.selenium.select_by_value(select_element, "valor1")

# Obtener información
text = await self.selenium.get_text(element)
value = await self.selenium.get_attribute(element, "value")
visible = await self.selenium.is_displayed(element)
```


### Interacción Humana (self.selenium.human)

Simula comportamiento humano para evitar detección:

```python
# Pausa aleatoria
await self.selenium.human.pause(1, 3)  # Entre 1 y 3 segundos

# Click con pausas antes/después
await self.selenium.human.click(
    "#boton",
    timeout=30,
    pause_before=(1.2, 2.8),  # Pausa antes del click
    pause_after=(0.5, 1.5)     # Pausa después del click
)

# Input carácter por carácter
await self.selenium.human.input(
    "#campo",
    "texto a escribir",
    timeout=30,
    char_delay=(0.05, 0.15),  # Delay entre caracteres
    clear=True
)
```

### Descargas

```python
# Esperar descarga de PDF
pdf_path = await self.selenium.wait_for_download(
    timeout=60,
    extension=".pdf",
    initial_count=None  # O pasar conteo inicial de archivos
)

if pdf_path:
    print(f"Descargado: {pdf_path}")
```

### Screenshots

```python
# Screenshot de página completa
path = await self.selenium.screenshot("nombre_captura")
# Guarda en: logs/bots/{bot_id}/{job_id}/screenshots/HHMMSS_nombre_captura.png

# Screenshot de elemento específico
img_bytes = await self.selenium.take_screenshot(element)
```

### Cookies

```python
# Guardar cookies actuales
await self.selenium.save_cookies()
# Guarda en: temp/profiles/{bot_id}/cookies.json

# Cargar cookies (debe estar en el dominio primero!)
await self.selenium.get("https://portal.com")
loaded = await self.selenium.load_cookies("portal.com")

if loaded:
    await self.selenium.refresh()
    # Verificar si sesión es válida
```

### Ventanas y Tabs

```python
# Obtener handles
current = await self.selenium.get_current_window()
all_handles = await self.selenium.get_window_handles()

# Cambiar de ventana
await self.selenium.switch_to_window(handle)
```

### Iframes

```python
# Cambiar a iframe
iframe = await self.selenium.wait_for(By.ID, "mi-iframe")
await self.selenium.switch_to_frame(iframe)

# Volver al contexto principal
await self.selenium.switch_to_default()
```

### JavaScript

```python
# Ejecutar JavaScript
result = await self.selenium.execute_js(
    "return document.title;"
)

# Scroll a elemento
await self.selenium.execute_js(
    "arguments[0].scrollIntoView();",
    element
)
```

---

## Handlers Especializados

### CaptchaHandler

Resolución de captchas usando API 2Captcha:

```python
from workers.selenium import CaptchaHandler

# Inicializar
self.captcha_handler = CaptchaHandler(self.selenium)

# Resolver captcha completo (capturar → enviar → esperar → llenar)
captcha_text = await self.captcha_handler.resolve_captcha(
    api_key=os.getenv("API_KEY_2CAPTCHA"),
    captcha_selector="#captcha-image",
    input_selector="#captcha-input",
    language="en"
)

# O paso por paso:
# 1. Capturar imagen
image_b64 = await self.captcha_handler.capture_captcha_image("#captcha-img")

# 2. Enviar a 2Captcha
task = await self.captcha_handler.send_to_2captcha(api_key, image_b64)

# 3. Esperar resolución con validación y reintentos
captcha_text = await self.captcha_handler.wait_for_resolution(
    api_key=api_key,
    task_id=task["taskId"],
    max_attempts=20,
    retry_delay=10,
    max_retries=10,
    captcha_input_selector="#captcha-input",
    login_button_selector="#btn-login",
    refresh_button_selector="#btn-refresh-captcha",
    captcha_image_selector="#captcha-img"
)
```

### ModalHandler

Manejo de alertas, modales y loaders:

```python
from workers.selenium import ModalHandler

self.modal_handler = ModalHandler(self.selenium)

# Alertas JavaScript
if await self.modal_handler.wait_for_alert(timeout=5):
    text = await self.modal_handler.get_alert_text()
    await self.modal_handler.accept_alert()
    # O: await self.modal_handler.dismiss_alert()

# Cerrar modal
await self.modal_handler.close_modal("#btn-close-modal", timeout=10)

# Esperar que aparezca/desaparezca modal
await self.modal_handler.wait_for_modal_appear("#modal", timeout=10)
await self.modal_handler.wait_for_modal_disappear("#modal", timeout=10)

# Esperar que desaparezca loader
await self.modal_handler.wait_for_loader_disappear(".spinner", timeout=30)
```

### WindowHandler

Manejo de ventanas y tabs:

```python
from workers.selenium import WindowHandler

self.window_handler = WindowHandler(self.selenium)

# Esperar nueva ventana y cambiar a ella
await self.window_handler.wait_for_new_window(timeout=10)
await self.window_handler.switch_to_new_window()

# Cambiar por título o URL
await self.window_handler.switch_to_window_by_title("Cotización")
await self.window_handler.switch_to_window_by_url("/cotizador")

# Cerrar ventanas
await self.window_handler.close_current_window()
closed = await self.window_handler.close_all_windows_except_main()

# Obtener número de ventanas
count = await self.window_handler.get_window_count()
```


---

## Gestión de Sesiones y Cookies

### Cómo Funcionan las Cookies

Las cookies se guardan **por aseguradora** (no por worker) en:
```
temp/profiles/{aseguradora}/cookies.json
```

Esto significa que **todos los workers comparten las mismas cookies** para una aseguradora, permitiendo reutilizar sesiones entre ejecuciones.

### Flujo Recomendado

```python
async def run(self) -> bool:
    try:
        # 1. Navegar al dominio (requerido para cargar cookies)
        await self.selenium.get(self.URL_LOGIN)
        await self.selenium.human.pause(2, 4)
        
        # 2. Intentar cargar cookies
        cookies_loaded = await self.selenium.load_cookies(self.COOKIE_DOMAIN)
        
        if cookies_loaded:
            # 3. Refrescar para aplicar cookies
            await self.selenium.refresh()
            await self.selenium.wait_page_load()
            
            # 4. Verificar si sesión es válida
            try:
                await self.selenium.wait_for(
                    By.CSS_SELECTOR,
                    "#dashboard",  # Elemento que solo aparece logueado
                    timeout=5
                )
                self.logger.info("Sesión restaurada, saltando login")
                # Ir directo a cotización
                return await self._complete_quotation()
            except:
                self.logger.debug("Sesión expirada, requiere login")
        
        # 5. Login completo si no hay sesión válida
        if not await self._login():
            return False
        
        # 6. Guardar cookies para futuras ejecuciones
        await self.selenium.save_cookies()
        self.logger.info("Cookies guardadas")
        
        # 7. Continuar con cotización
        return await self._complete_quotation()
        
    except Exception as e:
        await self.report_error("BOT_ERROR", str(e))
        return False
```

### Métodos de Cookies

```python
# Guardar cookies actuales
await self.selenium.save_cookies()

# Cargar cookies (debe estar en el dominio primero!)
loaded = await self.selenium.load_cookies("midominio.com")

# Limpiar archivo de cookies
self.selenium.clear_cookies()

# Eliminar cookies del navegador
await self.selenium.delete_all_cookies()
```

---

## Manejo de Errores

### Códigos de Error Recomendados

```python
# Autenticación
"AUTH_001"  # Credenciales inválidas
"AUTH_002"  # Estado de login desconocido
"AUTH_ERROR"  # Error genérico de autenticación

# Captcha
"CAPTCHA_001"  # No se pudo resolver después de reintentos
"CAPTCHA_002"  # Error creando tarea
"CAPTCHA_003"  # No se pudo capturar imagen
"CAPTCHA_ERROR"  # Error genérico de captcha

# Cotización
"QUOTE_001"  # Tabla de cotización no apareció
"QUOTE_ERROR"  # Error en flujo de cotización
"QUOTE_FLOW_ERROR"  # Error en flujo específico

# PDF
"PDF_001"  # No se pudo descargar PDF
"PDF_DOWNLOAD_FAILED"  # Fallo en descarga

# Configuración
"CONFIG_001"  # Variable de entorno faltante

# Bot
"BOT_EXCEPTION"  # Excepción no manejada
"BOT_ERROR"  # Error genérico del bot
```


### Reportar Errores

```python
# Error simple
await self.report_error("LOGIN_FAILED", "Usuario o contraseña incorrectos")

# Error con severidad
await self.report_error(
    error_code="CAPTCHA_ERROR",
    message="No se pudo resolver captcha después de 10 intentos",
    severity="CRITICAL",
    take_screenshot=True
)

# Severidades disponibles:
# - "WARNING": Advertencia, no crítico
# - "ERROR": Error estándar (default)
# - "CRITICAL": Error crítico que requiere atención
```

### Sistema de Retry Automático

El sistema maneja automáticamente 3 niveles de retry:

1. **Tier 1 - Immediate Retry**: Para errores transitorios (timeouts, stale elements)
2. **Tier 2 - Delayed Retry**: Para errores recuperables con exponential backoff
3. **Tier 3 - DLQ**: Para errores permanentes o después de max_retries

**No necesitas implementar retry en tu bot**, el worker lo maneja automáticamente.

### Clasificación Automática de Errores

El sistema clasifica automáticamente las excepciones:

- **TRANSIENT**: `TimeoutException`, `StaleElementReferenceException` → Retry inmediato
- **RETRIABLE**: `ElementClickInterceptedException`, `NoSuchElementException` → Retry con delay
- **PERMANENT**: `BotNotImplementedError`, errores de autenticación → DLQ

---

## Testing y Debugging

### Script de Testing Manual

Usar `tests/run_bot.py` para probar bots localmente:

```bash
# Ejecutar bot específico
python tests/run_bot.py sbs

# Con payload personalizado
python tests/run_bot.py sbs --payload '{"in_strPlaca": "ABC123"}'

```

### Ejemplo de Script de Test

```python
# tests/run_bot.py
import asyncio
from workers.bots.sura_bot import SURABot

async def test_sura():
    payload = {
        "in_strIDSolicitudAseguradora": "TEST-001",
        "in_strUsuarioAsesor": "usuario@test.com",
        "in_strContrasenaAsesor": "password",
        "in_strPlaca": "ABC123",
        "in_strNumDoc": "1234567890",
        "in_strCelular": "3001234567",
        "in_strEmail": "test@test.com"
    }
    
    bot = SURABot(job_id="test-sura-001", payload=payload)
    
    async with bot:
        success = await bot.run()
        print(f"Resultado: {'✅ Éxito' if success else '❌ Fallo'}")

if __name__ == "__main__":
    asyncio.run(test_sura())
```

### Debugging con Chrome Visible

El bot se ejecuta en modo headless en producción, pero en desarrollo/test se ejecuta con Chrome visible:

```python
# config/settings.py
ENVIRONMENT = "development"  # Chrome visible para debugging
# ENVIRONMENT = "production"  # Chrome headless
```

### Logs

Los logs se organizan por ejecución:

```
logs/bots/{aseguradora}/{job_id}/
├── bot.log              # Logs de esta ejecución
└── screenshots/         # Screenshots de esta ejecución
    ├── HHMMSS_error_LOGIN_001.png
    └── HHMMSS_error_PDF_001.png
```


---

## Registro del Bot

### Paso 1: Agregar al Registry

Editar `workers/mqtt_worker.py`:

```python
from workers.bots.sura_bot import SURABot

BOT_REGISTRY: dict[str, Type[BaseBot]] = {
    "hdi": HDIBot,
    "sbs": SBSBot,
    "sura": SURABot,  # ← Agregar aquí
    # ... otros bots
}
```

### Paso 2: Agregar Enum de Aseguradora

Editar `app/models/job.py`:

```python
class Aseguradora(str, Enum):
    """Aseguradoras soportadas."""
    HDI = "hdi"
    SURA = "sura"  # ← Agregar aquí
    SBS = "sbs"
    # ... otras
```

### Paso 3: Verificar Registro

```bash
# Iniciar worker y verificar que el bot aparece en la lista
python -m workers.mqtt_worker --id worker-1

# Output esperado:
# Worker [worker-1] iniciado
#   Aseguradoras: TODAS
#   Bots disponibles: ['hdi', 'sbs', 'sura']
```

### Paso 4: Probar Integración

```bash
# Enviar tarea de prueba
curl -X POST http://localhost:8000/api/sura/cotizar \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "in_strIDSolicitudAseguradora": "TEST-001",
    "in_strPlaca": "ABC123",
    "in_strNumDoc": "1234567890"
  }'

# Verificar logs del worker
tail -f logs/worker.log
```

---

## Mejores Prácticas

### 1. Estructura del Código

```python
class MiBot(BaseBot):
    # Constantes al inicio
    URL_LOGIN = "..."
    COOKIE_DOMAIN = "..."
    
    def __init__(self, job_id, payload):
        super().__init__(bot_id="mi_bot", job_id=job_id, payload=payload)
        # Inicializar handlers si se necesitan
    
    async def run(self) -> bool:
        """Método principal - flujo de alto nivel."""
        try:
            # Flujo principal claro y legible
            await self._login()
            await self._fill_form()
            pdf = await self._download_pdf()
            return await self.upload_result(pdf)
        except Exception as e:
            await self.report_error("BOT_ERROR", str(e))
            return False
    
    # Métodos privados para cada paso
    async def _login(self):
        """Login específico."""
        pass
    
    async def _fill_form(self):
        """Llenar formulario."""
        pass
    
    async def _download_pdf(self):
        """Descargar PDF."""
        pass
```

### 2. Usar Human Interaction

```python
# ❌ Malo - Detectable como bot
await self.selenium.click(element)
await self.selenium.type_text(element, "texto")

# ✅ Bueno - Simula humano
await self.selenium.human.click("#selector")
await self.selenium.human.input("#selector", "texto")
await self.selenium.human.pause(1, 3)
```


### 3. Manejo de Sesiones

```python
# ✅ Siempre intentar restaurar sesión primero
async def run(self) -> bool:
    await self.selenium.get(self.URL_LOGIN)
    
    # Intentar cookies
    if await self.selenium.load_cookies(self.COOKIE_DOMAIN):
        await self.selenium.refresh()
        # Verificar si sesión válida
        try:
            await self.selenium.wait_for(By.ID, "dashboard", timeout=5)
            # Sesión válida, saltar login
            return await self._complete_quotation()
        except:
            pass  # Sesión expirada, continuar con login
    
    # Login completo
    await self._login()
    await self.selenium.save_cookies()  # Guardar para próxima vez
    return await self._complete_quotation()
```

### 4. Esperas Inteligentes

```python
# ❌ Malo - Esperas fijas
await asyncio.sleep(5)

# ✅ Bueno - Esperar condiciones específicas
await self.selenium.wait_for(By.ID, "resultado", timeout=30)
await self.selenium.wait_page_load()
await self.modal_handler.wait_for_loader_disappear(".spinner")
```

### 5. Logging Descriptivo

```python
# ✅ Logs claros en cada paso importante
self.logger.info("Iniciando login...")
self.logger.debug(f"Llenando usuario: {usuario}")
self.logger.info("Login exitoso")
self.logger.warning("Sesión expirada, requiere nuevo login")
self.logger.error(f"Error en cotización: {e}")
```

### 6. Manejo de Descargas

```python
# ✅ Siempre contar PDFs antes de descargar
initial_count = len(list(self.selenium.TEMP_PDF_DIR.glob("*.pdf")))
self.logger.debug(f"PDFs antes de descargar: {initial_count}")

await self.selenium.human.click("#btn-descargar")

pdf_path = await self.selenium.wait_for_download(
    timeout=60,
    extension=".pdf",
    initial_count=initial_count  # ← Importante!
)
```

### 7. Validación de Datos

```python
# ✅ Validar datos del payload
placa = self.payload.get("in_strPlaca")
if not placa:
    await self.report_error("VALIDATION_001", "Placa no proporcionada")
    return False

# ✅ Normalizar datos
placa = placa.strip().upper()
```

### 8. Manejo de Elementos Dinámicos

```python
# ✅ Para elementos con postback (ASP.NET, etc.)
async def _click_checkbox(self, selector: str):
    """Click seguro en checkbox con postback."""
    loop = asyncio.get_running_loop()
    
    def _click():
        wait = WebDriverWait(self.driver, 30)
        checkbox = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        checkbox.click()
        
        # Esperar que el elemento se vuelva stale (postback)
        try:
            wait.until(EC.staleness_of(checkbox))
        except TimeoutException:
            pass
    
    await loop.run_in_executor(None, _click)
```

---

## Troubleshooting

### Problema: El bot no aparece en el worker

**Solución:**
1. Verificar que el bot está registrado en `BOT_REGISTRY` en `workers/mqtt_worker.py`
2. Verificar que la aseguradora está en el enum `Aseguradora` en `app/models/job.py`
3. Reiniciar el worker

### Problema: Cookies no se cargan

**Causas comunes:**
1. No navegaste al dominio antes de cargar cookies
2. El dominio no coincide con las cookies guardadas
3. Las cookies expiraron

**Solución:**
```python
# ✅ Orden correcto
await self.selenium.get(self.URL_LOGIN)  # Primero navegar
cookies_loaded = await self.selenium.load_cookies(self.COOKIE_DOMAIN)  # Luego cargar
if cookies_loaded:
    await self.selenium.refresh()  # Refrescar para aplicar
```

### Problema: PDF no se descarga

**Causas comunes:**
1. No se pasó `initial_count` a `wait_for_download()`
2. El PDF se descarga muy rápido y ya existía antes
3. Timeout muy corto

**Solución:**
```python
# ✅ Contar antes de descargar
initial_count = len(list(self.selenium.TEMP_PDF_DIR.glob("*.pdf")))
await self.selenium.human.click("#btn-descargar")
pdf_path = await self.selenium.wait_for_download(
    timeout=90,  # Timeout generoso
    extension=".pdf",
    initial_count=initial_count
)
```

### Problema: ElementClickInterceptedException

**Causa:** Otro elemento está sobre el elemento que quieres clickear.

**Solución:**
```python
# Opción 1: Usar JavaScript click
await self.selenium.click(element, use_js=True)

# Opción 2: Esperar que el elemento interceptor desaparezca
await self.modal_handler.wait_for_loader_disappear(".overlay")
await self.selenium.click(element)

# Opción 3: Usar human click (hace scroll automático)
await self.selenium.human.click("#selector")
```

### Problema: StaleElementReferenceException

**Causa:** El elemento cambió en el DOM (común en páginas con postback).

**Solución:**
```python
# Opción 1: Re-buscar el elemento
try:
    element.click()
except StaleElementReferenceException:
    element = await self.selenium.wait_for(By.ID, "elemento")
    element.click()

# Opción 2: Usar selector directamente con human
await self.selenium.human.click("#elemento")  # Re-busca automáticamente
```

### Problema: Captcha no se resuelve

**Causas comunes:**
1. API_KEY_2CAPTCHA no configurada
2. Captcha con longitud incorrecta
3. Botón de login no disponible después de llenar

**Solución:**
El `CaptchaHandler` ya incluye validación y reintentos automáticos. Verificar:
```python
# ✅ Usar wait_for_resolution con todos los parámetros
captcha_text = await self.captcha_handler.wait_for_resolution(
    api_key=api_key,
    task_id=task_id,
    max_attempts=20,
    retry_delay=10,
    max_retries=10,
    captcha_input_selector="#captcha-input",
    login_button_selector="#btn-login",
    refresh_button_selector="#btn-refresh",
    captcha_image_selector="#captcha-img"
)
```
---

### Acceso a Campos

```python
# Acceso directo
placa = self.payload.get("in_strPlaca", "")
usuario = self.payload.get("in_strUsuarioAsesor", "")

# ID de solicitud (atajo)
solicitud_id = self.solicitud_id  # Equivale a payload["in_strIDSolicitudAseguradora"]
```

---

## Recursos Adicionales

### Archivos de Referencia

- `workers/bots/base_bot.py` - Clase base con toda la infraestructura
- `workers/bots/sbs_bot.py` - Ejemplo completo de bot funcional
- `workers/selenium/helpers.py` - Todos los helpers de Selenium
- `workers/selenium/human_interaction.py` - Simulación de comportamiento humano
- `workers/selenium/captcha_handler.py` - Resolución de captchas
- `workers/mqtt_worker.py` - Worker y registro de bots

### Documentación Externa

- [Selenium Python Docs](https://selenium-python.readthedocs.io/)
- [2Captcha API](https://2captcha.com/api-docs)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)

---

## Checklist de Desarrollo

- [ ] Crear archivo del bot en `workers/bots/`
- [ ] Heredar de `BaseBot`
- [ ] Definir constantes (URLs, COOKIE_DOMAIN)
- [ ] Implementar `__init__()` con super()
- [ ] Implementar método `run()` con try/except
- [ ] Implementar `_login()` con manejo de sesiones
- [ ] Implementar formulario de cotización
- [ ] Implementar descarga de PDF con conteo inicial
- [ ] Agregar códigos de error descriptivos
- [ ] Registrar bot en `BOT_REGISTRY`
- [ ] Agregar aseguradora al enum `Aseguradora`
- [ ] Crear script de test en `tests/`
- [ ] Probar localmente con Chrome visible
- [ ] Probar con cookies/sesiones
- [ ] Probar en modo headless
- [ ] Verificar logs y screenshots
- [ ] Documentar campos específicos del payload

---

**¡Listo!** Con esta guía tienes todo lo necesario para desarrollar bots de cotización compatibles con BrokerWiz. Si tienes dudas, revisa el código de `SBSBot` como referencia completa.
