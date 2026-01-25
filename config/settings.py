from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from functools import lru_cache
from pathlib import Path

# Ruta al archivo .env (relativa a la raíz del proyecto)
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


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
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


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
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


class MQTTSettings(BaseSettings):
    """Configuracion de MQTT Broker (Mosquitto) - Simplficada sin TLS"""
    
    MQTT_HOST: str = Field(
        default="localhost",
        description="Host del broker MQTT"
    )
    MQTT_PORT: int = Field(
        default=1883,
        description="Puerto del broker MQTT"
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
    
    
    @property
    def get_aseguradora_topic(self) -> str:
        """Obtener template para cola de jobs por aseguradora: bots/queue/{aseguradora}"""
        return f"{self.MQTT_TOPIC_PREFIX}/queue"
    
    @property
    def get_wildcard_topic(self) -> str:
        """Wildcard para escuchar todas las aseguradoras: bots/queue/+"""
        return f"{self.MQTT_TOPIC_PREFIX}/queue/+"
    
    @property
    def MQTT_LWT_TOPIC(self) -> str:
        """Topic para Last Will and Testament"""
        return f"{self.MQTT_TOPIC_PREFIX}/clients/status"
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


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
    MAX_CONCURRENT_BOTS: int = Field(
        default=3,
        description="Maximo de bots Selenium ejecutandose simultaneamente"
    )
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


class AppWebSettings(BaseSettings):
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
    
    @field_validator("APP_WEB_BASE_URL")
    def validate_base_url(cls, v):
        """Remover trailing slash de la URL"""
        if v.endswith("/"):
            return v.rstrip("/")
        return v
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


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
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


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
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


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
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


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
    app_web: AppWebSettings = AppWebSettings()
    selenium: SeleniumSettings = SeleniumSettings()
    security: SecuritySettings = SecuritySettings()
    
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
    def NUM_WORKERS(self) -> int:
        return self.workers.NUM_WORKERS
    
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


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

# Opcion 2: Acceso a subgrupos
from config.settings import settings
api_host = settings.api.API_HOST}

# Opcion 3: Via funcion
from config.settings import get_settings

settings = get_settings()
"""
