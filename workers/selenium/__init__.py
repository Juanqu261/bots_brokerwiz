"""
Subpaquete Selenium - Utilidades para automatización con WebDriver.

Este paquete proporciona clases para gestionar el ciclo de vida del WebDriver,
persistencia de cookies y helpers para operaciones comunes de Selenium.

Uso:
    from workers.selenium import SeleniumDriverManager, CookiesManager, SeleniumHelpers
"""

from workers.selenium.driver_manager import SeleniumDriverManager
from workers.selenium.cookies_manager import CookiesManager
from workers.selenium.helpers import SeleniumHelpers

__all__ = [
    "SeleniumDriverManager",
    "CookiesManager", 
    "SeleniumHelpers",
]
