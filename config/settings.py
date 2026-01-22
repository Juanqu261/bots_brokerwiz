from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class GeneralSettings(BaseSettings):
    """Configuracion general"""
    
    ENVIRONMENT: str = Field(
        default="development",
        description="Entorno: development, staging, production"
    )
    DEBUG: bool = Field(
        default=True,
        description="Modo debug (verbose logging, stack traces)"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Nivel de logging: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class APISettings(BaseSettings):
    """Configuracion del servidor FastAPI"""
    
    API_HOST: str = Field(
        default="0.0.0.0",
        description="Host del servidor API"
    )
    API_PORT: int = Field(
        default=8000,
        description="Puerto del servidor API"
    )
    API_KEY: str = Field(
        default="dev-key-change-in-prod",
        description="API Key para autenticacion Bearer token"
    )
    API_REQUEST_TIMEOUT: int = Field(
        default=120,
        description="Timeout en segundos para requests"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class MQTTSettings(BaseSettings):
    """Configuracion de MQTT Broker (Mosquitto) - Productivo con TLS, LWT, Reconexion"""
    
    MQTT_HOST: str = Field(
        default="localhost",
        description="Host del broker MQTT"
    )
    MQTT_PORT: int = Field(
        default=1883,
        description="Puerto del broker MQTT (1883=plain, 8883=TLS)"
    )
    MQTT_USERNAME: Optional[str] = Field(
        default=None,
        description="Usuario MQTT (opcional)"
    )
    MQTT_PASSWORD: Optional[str] = Field(
        default=None,
        description="Contraseña MQTT (opcional)"
    )
    MQTT_CLIENT_ID: str = Field(
        default="broker-wiz-api",
        description="ID unico del cliente MQTT"
    )
    MQTT_QOS: int = Field(
        default=1,
        description="Quality of Service (0=at most once, 1=at least once, 2=exactly once)"
    )
    MQTT_TOPIC_PREFIX: str = Field(
        default="bots",
        description="Prefijo de topics MQTT"
    )
    MQTT_CLEAN_SESSION: bool = Field(
        default=True,
        description="Limpiar sesion al conectar"
    )
    MQTT_KEEPALIVE: int = Field(
        default=60,
        description="Keepalive en segundos"
    )
    
    # TLS
    MQTT_USE_TLS: bool = Field(
        default=False,
        description="Habilitar TLS/SSL para conexion segura"
    )
    MQTT_TLS_VERSION: Optional[str] = Field(
        default="tlsv1_2",
        description="Version de TLS: tlsv1_2, tlsv1_3"
    )
    MQTT_CA_CERTS: Optional[str] = Field(
        default=None,
        description="Ruta a archivo CA certificates para validar servidor"
    )
    MQTT_CERTFILE: Optional[str] = Field(
        default=None,
        description="Ruta a certificado cliente (para autenticacion mutua)"
    )
    MQTT_KEYFILE: Optional[str] = Field(
        default=None,
        description="Ruta a clave privada cliente (para autenticacion mutua)"
    )
    MQTT_TLS_INSECURE: bool = Field(
        default=False,
        description="NO verificar certificado del servidor (solo dev, NO en prod)"
    )
    
    # LWT
    MQTT_ENABLE_LWT: bool = Field(
        default=True,
        description="Habilitar Last Will para publicar estado offline"
    )
    MQTT_LWT_TOPIC: Optional[str] = Field(
        default=None,
        description="Topic para LWT (si None, sera: {TOPIC_PREFIX}/clients/status)"
    )
    
    # Reconexion
    MQTT_AUTO_RECONNECT: bool = Field(
        default=True,
        description="Reconexion automatica ante caidas"
    )
    MQTT_RECONNECT_MIN_DELAY: int = Field(
        default=1,
        description="Delay minimo en segundos para reconexion"
    )
    MQTT_RECONNECT_MAX_DELAY: int = Field(
        default=32,
        description="Delay maximo en segundos para reconexion (backoff exponencial)"
    )
    
    @property
    def MQTT_QUEUE_TOPIC_TEMPLATE(self) -> str:
        """Template para cola de jobs por aseguradora: bots/queue/{aseguradora}"""
        return f"{self.MQTT_TOPIC_PREFIX}/queue"
    
    @property
    def MQTT_STATUS_TOPIC(self) -> str:
        """Topic para estado de clientes (LWT)"""
        return self.MQTT_LWT_TOPIC or f"{self.MQTT_TOPIC_PREFIX}/clients/status"
    
    @property
    def MQTT_QUEUE_WILDCARD_SINGLE(self) -> str:
        """Wildcard de un nivel: bots/queue/+ (consume de cualquier aseguradora)"""
        return f"{self.MQTT_TOPIC_PREFIX}/queue/+"
    
    @property
    def MQTT_QUEUE_WILDCARD_MULTI(self) -> str:
        """Wildcard multilinivel: bots/queue/# (consume todo bajo queue)"""
        return f"{self.MQTT_TOPIC_PREFIX}/queue/#"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class WorkersSettings(BaseSettings):
    """Configuracion de Workers (MQTT-based)"""
    
    NUM_WORKERS: int = Field(
        default=3,
        description="Numero de workers a iniciar"
    )
    WORKER_TIMEOUT: int = Field(
        default=300,
        description="Timeout en segundos para cada job"
    )
    WORKER_POLL_INTERVAL: int = Field(
        default=1,
        description="Intervalo en segundos para polling de MQTT"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class AppWebIntegrationSettings(BaseSettings):
    """Configuracion de integracion con app-web"""
    
    APP_WEB_BASE_URL: str = Field(
        default="http://localhost:3000",
        description="URL base de la aplicacion web"
    )
    APP_WEB_API_KEY: str = Field(
        default="",
        description="API Key para autenticarse con app-web (Bearer token)"
    )
    APP_WEB_UPLOAD_TIMEOUT: int = Field(
        default=30,
        description="Timeout en segundos para upload de PDFs a app-web"
    )
    
    @validator("APP_WEB_BASE_URL")
    def validate_base_url(cls, v):
        """Remover trailing slash de la URL"""
        if v.endswith("/"):
            return v.rstrip("/")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class PDFUploadSettings(BaseSettings):
    """Configuracion de retry para uploads de PDF"""
    
    PDF_UPLOAD_MAX_RETRIES: int = Field(
        default=3,
        description="Maximo numero de reintentos en upload de PDF"
    )
    PDF_UPLOAD_INITIAL_WAIT: int = Field(
        default=2,
        description="Espera inicial en segundos (se multiplica exponencialmente)"
    )
    PDF_UPLOAD_BACKOFF_FACTOR: int = Field(
        default=2,
        description="Factor multiplicador para backoff exponencial"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class SeleniumSettings(BaseSettings):
    """Configuracion de Selenium WebDriver"""
    
    SELENIUM_HEADLESS: bool = Field(
        default=True,
        description="Ejecutar navegador en modo headless"
    )
    SELENIUM_WINDOW_SIZE: str = Field(
        default="1920,1080",
        description="Tamaño de ventana del navegador (WIDTHxHEIGHT)"
    )
    SELENIUM_TIMEOUT: int = Field(
        default=15,
        description="Timeout implicito en segundos para encontrar elementos"
    )
    SELENIUM_USER_AGENT: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User Agent para las requests del navegador"
    )
    
    @property
    def SELENIUM_CHROME_ARGS(self) -> List[str]:
        """Argumentos para Chrome/Chromium"""
        args = [
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions",
            "--disable-plugins",
        ]
        if self.SELENIUM_HEADLESS:
            args.append("--headless=new")
        width, height = self.SELENIUM_WINDOW_SIZE.split(",")
        args.append(f"--window-size={width},{height}")
        return args
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class StorageSettings(BaseSettings):
    """Configuracion de almacenamiento (screenshots, archivos temporales)"""
    
    STORAGE_PATH: str = Field(
        default="./storage",
        description="Ruta base para almacenamiento"
    )
    STORAGE_SCREENSHOTS: bool = Field(
        default=True,
        description="Guardar screenshots para debugging"
    )
    STORAGE_MAX_AGE_DAYS: int = Field(
        default=7,
        description="Dias antes de limpiar archivos viejos"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True

class LoggingSettings(BaseSettings):
    """Configuracion de logging"""
    
    LOG_FORMAT: str = Field(
        default="json",
        description="Formato de logs: json, plain"
    )
    LOG_FILE: str = Field(
        default="logs/broker_wiz.log",
        description="Archivo de log principal"
    )
    LOG_FILE_MAX_MB: int = Field(
        default=100,
        description="Tamaño maximo en MB antes de rotar logs"
    )
    LOG_FILE_BACKUP_COUNT: int = Field(
        default=10,
        description="Numero de backups de logs a mantener"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class SecuritySettings(BaseSettings):
    """Configuracion de seguridad y CORS"""
    
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Origenes permitidos para CORS (comma-separated)"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Permitir credenciales en CORS"
    )
    CORS_ALLOW_METHODS: str = Field(
        default="GET,POST,PUT,DELETE",
        description="Metodos HTTP permitidos (comma-separated)"
    )
    CORS_ALLOW_HEADERS: str = Field(
        default="*",
        description="Headers permitidos (comma-separated o *)"
    )
    
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """Convertir string a lista"""
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]
    
    @property
    def CORS_ALLOW_METHODS_LIST(self) -> List[str]:
        """Convertir string a lista"""
        return [m.strip() for m in self.CORS_ALLOW_METHODS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class FeatureFlagsSettings(BaseSettings):
    """Flags para habilitar/deshabilitar features"""
    
    FEATURE_WEBHOOK_NOTIFICATIONS: bool = Field(
        default=False,
        description="Habilitar notificaciones por webhook"
    )
    FEATURE_PERSISTENT_JOBS: bool = Field(
        default=False,
        description="Persistencia de jobs en base de datos"
    )
    FEATURE_ADMIN_UI: bool = Field(
        default=True,
        description="Habilitar dashboard admin"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class Settings(BaseSettings):
    """
    Clase principal que agrupa todas las configuraciones
    Uso: from config.settings import settings
         settings.API_PORT, settings.REDIS_HOST, etc
    """
    
    # Subconfigurations
    general: GeneralSettings = GeneralSettings()
    api: APISettings = APISettings()
    mqtt: MQTTSettings = MQTTSettings()
    workers: WorkersSettings = WorkersSettings()
    app_web: AppWebIntegrationSettings = AppWebIntegrationSettings()
    pdf_upload: PDFUploadSettings = PDFUploadSettings()
    selenium: SeleniumSettings = SeleniumSettings()
    storage: StorageSettings = StorageSettings()
    logging: LoggingSettings = LoggingSettings()
    security: SecuritySettings = SecuritySettings()
    feature_flags: FeatureFlagsSettings = FeatureFlagsSettings()
    
    # Shortcuts para acceso directo
    @property
    def ENVIRONMENT(self) -> str:
        return self.general.ENVIRONMENT
    
    @property
    def DEBUG(self) -> bool:
        return self.general.DEBUG
    
    @property
    def LOG_LEVEL(self) -> str:
        return self.general.LOG_LEVEL
    
    @property
    def API_PORT(self) -> int:
        return self.api.API_PORT
    
    @property
    def API_HOST(self) -> str:
        return self.api.API_HOST
    
    @property
    def API_KEY(self) -> str:
        return self.api.API_KEY
    
    @property
    def MQTT_HOST(self) -> str:
        return self.mqtt.MQTT_HOST
    
    @property
    def MQTT_PORT(self) -> int:
        return self.mqtt.MQTT_PORT
    
    @property
    def MQTT_QUEUE_TOPIC(self) -> str:
        return self.mqtt.MQTT_QUEUE_TOPIC
    
    @property
    def NUM_WORKERS(self) -> int:
        return self.workers.NUM_WORKERS
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
@lru_cache()
def get_settings() -> Settings:
    """
    Obtener instancia singleton de Settings
    Uso: from config.settings import get_settings
         settings = get_settings()
    """
    return Settings()


# Instancia global (para imports directos)
settings = get_settings()


"""
# Opcion 1: Acceso directo
from config.settings import settings

host = settings.API_HOST
port = settings.API_PORT
redis_url = settings.REDIS_URL

# Opcion 2: Acceso a subgrupos
from config.settings import settings

redis_host = settings.redis.REDIS_HOST
chrome_args = settings.selenium.SELENIUM_CHROME_ARGS

# Opcion 3: Via funcion
from config.settings import get_settings

settings = get_settings()
"""
