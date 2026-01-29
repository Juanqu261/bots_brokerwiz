"""
Subpaquete Selenium - Utilidades para automatización con WebDriver.

Este paquete proporciona clases para gestionar el ciclo de vida del WebDriver,
persistencia de cookies, helpers para operaciones comunes, handlers especializados
para captchas/modales/ventanas, e interacción humana simulada.

Uso:
    from workers.selenium import (
        SeleniumDriverManager,
        CookiesManager,
        SeleniumHelpers,
        HumanInteraction,
        CaptchaHandler,
        ModalHandler,
        WindowHandler
    )
"""

from workers.selenium.driver_manager import SeleniumDriverManager
from workers.selenium.cookies_manager import CookiesManager
from workers.selenium.helpers import SeleniumHelpers
from workers.selenium.human_interaction import HumanInteraction
from workers.selenium.captcha_handler import CaptchaHandler
from workers.selenium.modal_handler import ModalHandler
from workers.selenium.window_handler import WindowHandler

__all__ = [
    "SeleniumDriverManager",
    "CookiesManager", 
    "SeleniumHelpers",
    "HumanInteraction",
    "CaptchaHandler",
    "ModalHandler",
    "WindowHandler",
]
