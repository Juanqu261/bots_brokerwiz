"""
Subpaquete Selenium - Utilidades para automatización con WebDriver.

Este paquete proporciona clases para gestionar el ciclo de vida del WebDriver,
persistencia de cookies, helpers para operaciones comunes, y handlers especializados
para captchas, modales y ventanas.

Uso:
    from workers.selenium import (
        SeleniumDriverManager,
        CookiesManager,
        SeleniumHelpers,
        CaptchaHandler,
        ModalHandler,
        WindowHandler
    )
"""

from workers.selenium.driver_manager import SeleniumDriverManager
from workers.selenium.cookies_manager import CookiesManager
from workers.selenium.helpers import SeleniumHelpers
from workers.selenium.captcha_handler import CaptchaHandler
from workers.selenium.modal_handler import ModalHandler
from workers.selenium.window_handler import WindowHandler

__all__ = [
    "SeleniumDriverManager",
    "CookiesManager", 
    "SeleniumHelpers",
    "CaptchaHandler",
    "ModalHandler",
    "WindowHandler",
]
