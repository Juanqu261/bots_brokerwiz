from enum import Enum


class MQTTTopics(str, Enum):
    """Topics MQTT disponibles"""
    
    QUEUE = "bots/queue"


class Aseguradora(str, Enum):
    """Listado de aseguradoras soportadas"""
    
    HDI = "hdi"
    RUNT = "runt"
    AXA = "axa"
    SURA = "sura"
    SOLIDARIA = "solidaria"
    EQUIDAD = "equidad"
    MUNDIAL = "mundial"
    ALLIANZ = "allianz"
    BOLIVAR = "bolivar"
    SBS = "sbs"
    
    @classmethod
    def list(cls):
        """Retornar lista de aseguradoras"""
        return [a.value for a in cls]


class JobStatus(str, Enum):
    """Estados posibles de un job"""
    
    QUEUED = "queued"          # En cola esperando ser procesado
    PROCESSING = "processing"  # Siendo procesado por un worker
    COMPLETED = "completed"    # Completado exitosamente
    FAILED = "failed"          # Falló y no se reintentará
    CANCELLED = "cancelled"    # Cancelado manualmente


class LogLevel(str, Enum):
    """Niveles de logging"""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Entornos soportados"""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogFormat(str, Enum):
    """Formatos de logging"""
    
    JSON = "json"
    PLAIN = "plain"


# Mapping de bots

BOT_MAPPING = {
    Aseguradora.HDI: "workers.bots.hdi_bot.HDIBot",
    Aseguradora.RUNT: "workers.bots.runt_bot.RUNTBot",
    Aseguradora.AXA: "workers.bots.axa_bot.AXABot",
    Aseguradora.SURA: "workers.bots.sura_bot.SURABot",
    Aseguradora.SOLIDARIA: "workers.bots.solidaria_bot.SolidariaBot",
    Aseguradora.EQUIDAD: "workers.bots.equidad_bot.EquidadBot",
    Aseguradora.MUNDIAL: "workers.bots.mundial_bot.MundialBot",
    Aseguradora.ALLIANZ: "workers.bots.allianz_bot.AllianzBot",
    Aseguradora.BOLIVAR: "workers.bots.bolivar_bot.BolivarBot",
    Aseguradora.SBS: "workers.bots.sbs_bot.SBSBot",
}

# Codigos de error

class ErrorCode(str, Enum):
    """Codigos de error estandarizados"""
    
    INVALID_ASEGURADORA = "INVALID_ASEGURADORA"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    INVALID_API_KEY = "INVALID_API_KEY"
    BOT_TIMEOUT = "BOT_TIMEOUT"
    BOT_FAILED = "BOT_FAILED"
    PDF_UPLOAD_FAILED = "PDF_UPLOAD_FAILED"
    MQTT_CONNECTION_FAILED = "MQTT_CONNECTION_FAILED"
    SELENIUM_TIMEOUT = "SELENIUM_TIMEOUT"
    SELENIUM_ELEMENT_NOT_FOUND = "SELENIUM_ELEMENT_NOT_FOUND"
    SELENIUM_NAVIGATION_FAILED = "SELENIUM_NAVIGATION_FAILED"
    LOGIN_FAILED = "LOGIN_FAILED"
    QUOTE_EXTRACTION_FAILED = "QUOTE_EXTRACTION_FAILED"
    PDF_GENERATION_FAILED = "PDF_GENERATION_FAILED"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Mensajes de error

ERROR_MESSAGES = {
    ErrorCode.INVALID_ASEGURADORA: "La aseguradora especificada no es válida",
    ErrorCode.JOB_NOT_FOUND: "El job no fue encontrado",
    ErrorCode.INVALID_API_KEY: "API Key inválido",
    ErrorCode.BOT_TIMEOUT: "El bot excedió el tiempo máximo de ejecución",
    ErrorCode.BOT_FAILED: "El bot falló durante la ejecución",
    ErrorCode.PDF_UPLOAD_FAILED: "Falló al enviar el PDF a app-web",
    ErrorCode.MQTT_CONNECTION_FAILED: "No se pudo conectar al broker MQTT",
    ErrorCode.SELENIUM_TIMEOUT: "Timeout en carga de página Selenium",
    ErrorCode.SELENIUM_ELEMENT_NOT_FOUND: "Elemento no encontrado en la página",
    ErrorCode.SELENIUM_NAVIGATION_FAILED: "Fallo en navegación a URL",
    ErrorCode.LOGIN_FAILED: "Credenciales inválidas o cambio en UI",
    ErrorCode.QUOTE_EXTRACTION_FAILED: "No se pudo extraer la cotización",
    ErrorCode.PDF_GENERATION_FAILED: "Error generando PDF",
    ErrorCode.NETWORK_ERROR: "Error de conexión de red",
    ErrorCode.UNKNOWN_ERROR: "Error desconocido",
}
