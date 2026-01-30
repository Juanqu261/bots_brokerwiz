"""
Guarda solo las cookies (no caché, historial ni extensiones) para mantener
sesiones activas entre ejecuciones de bots.

Estructura:
    temp/
    ├── profiles/
    │   ├── hdi/cookies.json
    │   ├── sbs/cookies.json
    │   └── ...
    └── pdfs/

Sincronización:
    - Lectura: NO bloqueante (múltiples bots pueden leer simultáneamente)
    - Escritura: BLOQUEANTE (solo un bot escribe a la vez)
    - Lock: Archivo .lock en el mismo directorio
"""

import json
import time
import logging
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


class CookiesManager:
    """
    Gestiona cookies de sesión en archivos JSON livianos con sincronización.
    
    Sincronización:
    - Lectura: NO bloqueante (múltiples bots pueden leer simultáneamente)
    - Escritura: BLOQUEANTE con timeout (solo un bot escribe a la vez)
    - Usa archivo .lock para coordinar escrituras
    """
    
    # Directorio base para perfiles (dentro de temp/)
    PROFILES_DIR = Path("temp/profiles")
    
    # Timeout para adquirir lock de escritura (segundos)
    LOCK_TIMEOUT = 30
    
    # Tiempo de espera entre intentos de lock (segundos)
    LOCK_RETRY_DELAY = 0.1
    
    def __init__(self, bot_id: str):
        """
        Inicializar manager de cookies.
        
        Args:
            bot_id: Identificador del bot (ej: "hdi", "sbs")
                   Todos los jobs del mismo bot comparten el mismo perfil/cookies
        """
        self.bot_id = bot_id
        self.cookies_file = self.PROFILES_DIR / bot_id / "cookies.json"
        self.lock_file = self.PROFILES_DIR / bot_id / "cookies.lock"
    
    async def save(self, driver: "WebDriver") -> None:
        """
        Guardar cookies actuales del driver a archivo JSON.
        
        BLOQUEANTE: Adquiere lock exclusivo antes de escribir.
        Solo se debe llamar después de un login exitoso.
        
        Args:
            driver: WebDriver con sesión activa
        """
        try:
            cookies = await asyncio.to_thread(driver.get_cookies)
            
            # Crear directorio si no existe
            self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Adquirir lock exclusivo para escritura
            await self._acquire_write_lock()
            
            try:
                # Guardar cookies en formato JSON legible
                self.cookies_file.write_text(
                    json.dumps(cookies, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                
                logger.info(f"[{self.bot_id}] Guardadas {len(cookies)} cookies en {self.cookies_file}")
                
            finally:
                # Liberar lock
                await self._release_write_lock()
            
        except Exception as e:
            logger.warning(f"[{self.bot_id}] Error guardando cookies: {e}")
    
    async def load(self, driver: "WebDriver", domain: str) -> bool:
        """
        Cargar cookies desde JSON para un dominio específico.
        
        NO BLOQUEANTE: Lectura concurrente permitida.
        
        IMPORTANTE: El driver debe haber navegado primero al dominio
        antes de cargar cookies (requisito de Selenium).
        
        Args:
            driver: WebDriver activo (ya debe estar en el dominio)
            domain: Dominio base para filtrar cookies (ej: "tu.sbseguros.co")
        
        Returns:
            True si se cargaron cookies, False si no existían o hubo error
        """
        if not self.cookies_file.exists():
            logger.debug(f"[{self.bot_id}] No hay cookies guardadas en {self.cookies_file}")
            return False
        
        try:
            # Lectura NO bloqueante - múltiples bots pueden leer simultáneamente
            cookies = json.loads(self.cookies_file.read_text(encoding="utf-8"))
            loaded_count = 0
            
            for cookie in cookies:
                # Filtrado mejorado: más flexible con dominios
                if not self._cookie_matches_domain(cookie, domain):
                    continue
                
                try:
                    # Eliminar campos que pueden causar problemas
                    cookie_clean = {k: v for k, v in cookie.items() 
                                   if k not in ("sameSite",)}
                    
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
    
    def _cookie_matches_domain(self, cookie: dict, target_domain: str) -> bool:
        """
        Verificar si una cookie es válida para el dominio objetivo.
        
        Maneja:
        - Dominios exactos: "tu.sbseguros.co" == "tu.sbseguros.co"
        - Dominios con punto: ".sbseguros.co" válido para "tu.sbseguros.co"
        - Subdominios: "sbseguros.co" válido para "tu.sbseguros.co"
        
        Args:
            cookie: Cookie dict con campo "domain"
            target_domain: Dominio objetivo (ej: "tu.sbseguros.co")
        
        Returns:
            True si la cookie es válida para el dominio
        """
        cookie_domain = cookie.get("domain", "").lower()
        target_domain = target_domain.lower()
        
        if not cookie_domain:
            return False
        
        # Caso 1: Coincidencia exacta
        if cookie_domain == target_domain:
            return True
        
        # Caso 2: Cookie con dominio que comienza con punto (ej: ".sbseguros.co")
        # Es válida para cualquier subdominio (ej: "tu.sbseguros.co")
        if cookie_domain.startswith("."):
            # Remover el punto y verificar si target termina con ese dominio
            domain_without_dot = cookie_domain[1:]
            if target_domain.endswith(domain_without_dot):
                return True
            if target_domain == domain_without_dot:
                return True
        
        # Caso 3: Target termina con cookie_domain (ej: target="tu.sbseguros.co", cookie="sbseguros.co")
        if target_domain.endswith("." + cookie_domain):
            return True
        
        # Caso 4: Son el mismo dominio base
        if target_domain == cookie_domain:
            return True
        
        return False
    
    async def _acquire_write_lock(self) -> None:
        """
        Adquirir lock exclusivo para escritura.
        
        BLOQUEANTE: Espera hasta obtener el lock o timeout.
        Usa polling con retry delay.
        """
        start_time = time.time()
        
        while True:
            try:
                # Intentar crear archivo lock (falla si ya existe)
                self.lock_file.touch(exist_ok=False)
                logger.debug(f"[{self.bot_id}] Lock de escritura adquirido")
                return
                
            except FileExistsError:
                # Lock ya existe, esperar
                elapsed = time.time() - start_time
                
                if elapsed > self.LOCK_TIMEOUT:
                    logger.warning(
                        f"[{self.bot_id}] Timeout esperando lock de escritura "
                        f"({self.LOCK_TIMEOUT}s). Procediendo de todas formas."
                    )
                    return
                
                # Esperar antes de reintentar
                await asyncio.sleep(self.LOCK_RETRY_DELAY)
    
    async def _release_write_lock(self) -> None:
        """Liberar lock exclusivo de escritura."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                logger.debug(f"[{self.bot_id}] Lock de escritura liberado")
        except Exception as e:
            logger.warning(f"[{self.bot_id}] Error liberando lock: {e}")
    
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
