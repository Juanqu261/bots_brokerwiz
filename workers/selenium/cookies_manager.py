"""
Guarda solo las cookies (no caché, historial ni extensiones) para mantener
sesiones activas entre ejecuciones de bots.

Estructura:
    profiles/
    ├── hdi/cookies.json
    ├── sura/cookies.json
    └── ...
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


class CookiesManager:
    """Gestiona cookies de sesión en archivos JSON livianos."""
    
    # Directorio base para perfiles
    PROFILES_DIR = Path("profiles")
    
    def __init__(self, bot_id: str):
        """
        Inicializar manager de cookies.
        
        Args:
            bot_id: Identificador del bot (ej: "hdi", "sura")
        """
        self.bot_id = bot_id
        self.cookies_file = self.PROFILES_DIR / bot_id / "cookies.json"
    
    async def save(self, driver: "WebDriver") -> None:
        """
        Guardar cookies actuales del driver a archivo JSON.
        
        Args:
            driver: WebDriver con sesión activa
        """
        try:
            cookies = await asyncio.to_thread(driver.get_cookies)
            
            # Crear directorio si no existe
            self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar cookies en formato JSON legible
            self.cookies_file.write_text(
                json.dumps(cookies, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            logger.debug(f"[{self.bot_id}] Guardadas {len(cookies)} cookies en {self.cookies_file}")
            
        except Exception as e:
            logger.warning(f"[{self.bot_id}] Error guardando cookies: {e}")
    
    async def load(self, driver: "WebDriver", domain: str) -> bool:
        """
        Cargar cookies desde JSON para un dominio específico.
        
        IMPORTANTE: El driver debe haber navegado primero al dominio
        antes de cargar cookies (requisito de Selenium).
        
        Args:
            driver: WebDriver activo (ya debe estar en el dominio)
            domain: Dominio base para filtrar cookies (ej: "hdi.com.co")
        
        Returns:
            True si se cargaron cookies, False si no existían o hubo error
        """
        if not self.cookies_file.exists():
            logger.debug(f"[{self.bot_id}] No hay cookies guardadas en {self.cookies_file}")
            return False
        
        try:
            cookies = json.loads(self.cookies_file.read_text(encoding="utf-8"))
            loaded_count = 0
            
            for cookie in cookies:
                # Filtrar cookies por dominio
                cookie_domain = cookie.get("domain", "")
                if domain not in cookie_domain and cookie_domain not in domain:
                    continue
                
                try:
                    # Eliminar campos que pueden causar problemas
                    cookie_clean = {k: v for k, v in cookie.items() 
                                   if k not in ("sameSite",)}  # sameSite puede fallar en algunos drivers
                    
                    await asyncio.to_thread(driver.add_cookie, cookie_clean)
                    loaded_count += 1
                    
                except Exception as e:
                    # Cookie inválida, expirada o incompatible - continuar con las demás
                    logger.debug(f"[{self.bot_id}] Cookie ignorada ({cookie.get('name')}): {e}")
            
            logger.info(f"[{self.bot_id}] Cargadas {loaded_count} cookies para dominio {domain}")
            return loaded_count > 0
            
        except json.JSONDecodeError as e:
            logger.warning(f"[{self.bot_id}] Error parseando cookies JSON: {e}")
            return False
        except Exception as e:
            logger.warning(f"[{self.bot_id}] Error cargando cookies: {e}")
            return False
    
    def clear(self) -> None:
        """Eliminar archivo de cookies guardadas."""
        if self.cookies_file.exists():
            self.cookies_file.unlink()
            logger.info(f"[{self.bot_id}] Cookies eliminadas: {self.cookies_file}")
    
    def exists(self) -> bool:
        """Verificar si hay cookies guardadas."""
        return self.cookies_file.exists()
    
    @classmethod
    def clear_all(cls) -> int:
        """
        Eliminar todas las cookies de todos los bots.
        
        Returns:
            Número de archivos eliminados
        """
        count = 0
        if cls.PROFILES_DIR.exists():
            for cookies_file in cls.PROFILES_DIR.glob("*/cookies.json"):
                cookies_file.unlink()
                count += 1
        logger.info(f"Eliminadas cookies de {count} bots")
        return count
